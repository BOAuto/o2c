"""Temporal activities for O2C central order ingestion."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from imap_tools import AND, MailBox, MailBoxUnencrypted
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from temporalio import activity

from app.core.config import settings
from app.core.crypto import decrypt_secret
from app.core.db import engine
from app.models import User
from app.models.mail_access import MailAccessType, MailboxConfig, MailboxScopeType
from app.models.order_ingestion import (
    InternalUnmappedSender,
    OrderIngestionArtifact,
    OrderIngestionArtifactKind,
    OrderIngestionRun,
    OrderIngestionStatus,
    OrderUserMessageId,
    RejectedCentralReason,
    RejectedCentralSender,
)
from app.services.ingestion_mail import (
    cc_formatted_for_storage,
    email_domain,
    get_header_single,
    html_for_po_attachment,
    list_non_image_attachments,
    normalize_message_id,
    primary_email_from_header,
    render_html_document,
)
from app.services.retrieval_period import parse_ingestion_period_minutes
from app.storage.order_ingestion import upload_order_ingestion_bytes
from app.temporal import imap_pool

logger = logging.getLogger(__name__)
_INTERNAL_DOMAIN = "brilliantoffice.in"


def _open_mailbox(cfg: MailboxConfig) -> MailBox | MailBoxUnencrypted:
    pwd = decrypt_secret(cfg.encrypted_app_password)
    if cfg.imap_ssl:
        return MailBox(cfg.imap_host, cfg.imap_port).login(cfg.email, pwd, initial_folder="INBOX")
    return MailBoxUnencrypted(cfg.imap_host, cfg.imap_port).login(
        cfg.email, pwd, initial_folder="INBOX"
    )


def _central_config(session: Session) -> MailboxConfig | None:
    return session.exec(
        select(MailboxConfig).where(
            MailboxConfig.scope_type == MailboxScopeType.CENTRAL_ORDER_MAIL,
            MailboxConfig.is_active == True,  # noqa: E712
        )
    ).first()


@activity.defn(name="load_scheduler_config_activity")
def load_scheduler_config_activity() -> dict[str, Any]:
    with Session(engine) as session:
        cfg = _central_config(session)
        if not cfg:
            raise RuntimeError("centralOrderMail mailbox not configured")
        period = parse_ingestion_period_minutes(
            cfg.ingestion_retrieval_period,
            default=settings.O2C_DEFAULT_INGESTION_PERIOD_MINUTES,
        )
        return {
            "central_mailbox_config_id": str(cfg.id),
            "period_minutes": period,
        }


@activity.defn(name="poll_central_unread_activity")
def poll_central_unread_activity() -> list[dict[str, str]]:
    with Session(engine) as session:
        cfg = _central_config(session)
        if not cfg:
            raise RuntimeError("centralOrderMail mailbox not configured")
        out: list[dict[str, str]] = []
        with _open_mailbox(cfg) as mb:
            for msg in mb.fetch(AND(seen=False), mark_seen=False, reverse=True):
                uid = msg.uid or ""
                mid = get_header_single(msg, "message-id")
                mid_norm = normalize_message_id(mid) if mid else f"no-msgid-{uid}"
                out.append({"uid": str(uid), "message_id_norm": mid_norm})
        return out


@activity.defn(name="ensure_mailbox_pool_activity")
def ensure_mailbox_pool_activity(central_mailbox_config_id: str) -> None:
    cid = uuid.UUID(central_mailbox_config_id)
    with Session(engine) as session:
        imap_pool.ensure_mailbox_pool(session, central_config_id=cid)


@activity.defn(name="release_mailbox_pool_activity")
def release_mailbox_pool_activity() -> None:
    imap_pool.clear_pool()


@activity.defn(name="classify_central_sender_activity")
def classify_central_sender_activity(central_mailbox_config_id: str, imap_uid: str) -> dict[str, str]:
    cid = uuid.UUID(central_mailbox_config_id)
    with Session(engine) as session:
        cfg = session.get(MailboxConfig, cid)
        if not cfg:
            raise RuntimeError("central mailbox not found")
        order_emails = _order_user_emails(session)
        internal_emails = _internal_order_user_emails(session)
        with _open_mailbox(cfg) as mb:
            msgs = list(mb.fetch(f"UID {imap_uid}", mark_seen=False, limit=1))
            if not msgs:
                return {"result": "rejected_central_sender", "reason": RejectedCentralReason.EXTERNAL.value}
            msg = msgs[0]
            from_email = primary_email_from_header(msg.from_ or "")
            sender_domain = email_domain(from_email)
            if from_email in order_emails:
                sender_cfg = session.exec(
                    select(MailboxConfig).where(
                        MailboxConfig.email == from_email,
                        MailboxConfig.scope_type == MailboxScopeType.USER_LINKED,
                        MailboxConfig.is_active == True,  # noqa: E712
                    )
                ).first()
                out: dict[str, str] = {"result": "order_user"}
                if sender_cfg:
                    out["sender_mailbox_email"] = sender_cfg.email
                return out
            if from_email in internal_emails:
                return {
                    "result": "internal_mail_access_sender",
                }
            if sender_domain == _INTERNAL_DOMAIN:
                return {"result": "internal_non_mail_access_sender"}
            return {"result": "rejected_central_sender", "reason": RejectedCentralReason.EXTERNAL.value}


def _order_user_emails(session: Session) -> set[str]:
    rows = session.exec(
        select(User.email)
        .join(MailboxConfig, MailboxConfig.user_id == User.id)
        .where(
            MailboxConfig.scope_type == MailboxScopeType.USER_LINKED,
            MailboxConfig.mail_access_type == MailAccessType.ORDER_USER,
            MailboxConfig.is_active == True,  # noqa: E712
            User.is_active == True,  # noqa: E712
        )
    ).all()
    return {str(e).lower() for e in rows}


def _internal_order_user_emails(session: Session) -> set[str]:
    rows = session.exec(
        select(User.email)
        .join(MailboxConfig, MailboxConfig.user_id == User.id)
        .where(
            MailboxConfig.scope_type == MailboxScopeType.USER_LINKED,
            MailboxConfig.mail_access_type == MailAccessType.ORDER_INTERNAL_USER,
            MailboxConfig.is_active == True,  # noqa: E712
            User.is_active == True,  # noqa: E712
        )
    ).all()
    return {str(e).lower() for e in rows}


@activity.defn(name="record_rejected_central_sender_activity")
def record_rejected_central_sender_activity(
    central_mailbox_config_id: str,
    imap_uid: str,
    rejection_reason: str,
) -> None:
    cid = uuid.UUID(central_mailbox_config_id)
    with Session(engine) as session:
        cfg = session.get(MailboxConfig, cid)
        if not cfg:
            return
        with _open_mailbox(cfg) as mb:
            msgs = list(mb.fetch(f"UID {imap_uid}", mark_seen=False, limit=1))
            if not msgs:
                return
            msg = msgs[0]
            from_email = primary_email_from_header(msg.from_ or "")
            mid = normalize_message_id(get_header_single(msg, "message-id"))
            existing = session.exec(
                select(RejectedCentralSender).where(
                    RejectedCentralSender.central_mailbox_config_id == cid,
                    RejectedCentralSender.imap_uid == str(imap_uid)[:32],
                    RejectedCentralSender.rejection_reason == rejection_reason[:32],
                )
            ).first()
            if existing:
                return
            row = RejectedCentralSender(
                central_mailbox_config_id=cid,
                from_address=from_email or (msg.from_ or "")[:512],
                subject=(msg.subject or "")[:998] or None,
                message_id_norm=mid or None,
                imap_uid=str(imap_uid)[:32],
                rejection_reason=rejection_reason[:32],
            )
            session.add(row)
            session.commit()


@activity.defn(name="record_internal_unmapped_sender_activity")
def record_internal_unmapped_sender_activity(
    central_mailbox_config_id: str,
    imap_uid: str,
) -> None:
    cid = uuid.UUID(central_mailbox_config_id)
    with Session(engine) as session:
        cfg = session.get(MailboxConfig, cid)
        if not cfg:
            return
        with _open_mailbox(cfg) as mb:
            msgs = list(mb.fetch(f"UID {imap_uid}", mark_seen=False, limit=1))
            if not msgs:
                return
            msg = msgs[0]
            from_email = primary_email_from_header(msg.from_ or "")
            mid = normalize_message_id(get_header_single(msg, "message-id"))
            existing = session.exec(
                select(InternalUnmappedSender).where(
                    InternalUnmappedSender.central_mailbox_config_id == cid,
                    InternalUnmappedSender.imap_uid == str(imap_uid)[:32],
                )
            ).first()
            if existing:
                return
            row = InternalUnmappedSender(
                central_mailbox_config_id=cid,
                from_address=from_email or (msg.from_ or "")[:512],
                subject=(msg.subject or "")[:998] or None,
                message_id_norm=mid or None,
                imap_uid=str(imap_uid)[:32],
            )
            session.add(row)
            session.commit()


@activity.defn(name="save_order_user_anchor_activity")
def save_order_user_anchor_activity(
    central_mailbox_config_id: str,
    imap_uid: str,
) -> dict[str, Any]:
    cid = uuid.UUID(central_mailbox_config_id)
    with Session(engine) as session:
        cfg = session.get(MailboxConfig, cid)
        if not cfg:
            raise RuntimeError("central mailbox not found")
        with _open_mailbox(cfg) as mb:
            msgs = list(mb.fetch(f"UID {imap_uid}", mark_seen=False, limit=1))
            if not msgs:
                raise RuntimeError("central message not found")
            msg = msgs[0]
            mid_raw = get_header_single(msg, "message-id")
            mid_norm = normalize_message_id(mid_raw) if mid_raw else f"no-msgid-{imap_uid}"
            irt = get_header_single(msg, "in-reply-to")
            # Anchor is always the central message; downstream hop resolution decides
            # when HTML/EML should be replaced from a traced message where this sender
            # appears in recipients.
            order_user_email = primary_email_from_header(msg.from_ or "") or ""
            persist_msg = msg

            run = OrderIngestionRun(
                central_mailbox_config_id=cid,
                source_message_id_norm=mid_norm[:512],
                order_user_message_id_norm=None,
                source_from=(primary_email_from_header(msg.from_ or "") or msg.from_ or "")[:1024] or None,
                source_subject=(msg.subject or "")[:998] or None,
                source_received_at=(
                    msg.date.replace(tzinfo=timezone.utc)
                    if msg.date and msg.date.tzinfo is None
                    else (msg.date.astimezone(timezone.utc) if msg.date else None)
                ),
                no_attachment_order=False,
                status=OrderIngestionStatus.IN_PROGRESS.value,
            )
            session.add(run)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.exec(
                    select(OrderIngestionRun).where(
                        OrderIngestionRun.central_mailbox_config_id == cid,
                        OrderIngestionRun.source_message_id_norm == mid_norm[:512],
                    )
                ).first()
                if existing:
                    return {
                        "duplicate": True,
                        "order_ingestion_id": str(existing.id),
                        "no_attachment_order": existing.no_attachment_order,
                        "order_user_message_id_norm": existing.order_user_message_id_norm,
                        "order_user_email": order_user_email,
                        "in_reply_to": irt,
                        "anchor_message_id_norm": mid_norm,
                    }
                raise

            session.refresh(run)
            oid = run.id

            raw_eml = persist_msg.obj.as_bytes()
            key_eml, sz_eml = upload_order_ingestion_bytes(
                storage_type="eml",
                file_name=f"{mid_norm[:80] or 'message'}.eml",
                content=raw_eml,
                content_type="message/rfc822",
            )
            art_eml = OrderIngestionArtifact(
                order_ingestion_id=oid,
                artifact_kind=OrderIngestionArtifactKind.EML.value,
                object_key=key_eml,
                file_name=f"{mid_norm[:80] or 'message'}.eml",
                mime_type="message/rfc822",
                size_bytes=sz_eml,
            )
            session.add(art_eml)

            html_doc = render_html_document(persist_msg)
            key_html, sz_html = upload_order_ingestion_bytes(
                storage_type="html",
                file_name=f"{mid_norm[:80] or 'message'}.html",
                content=html_doc.encode("utf-8"),
                content_type="text/html",
            )
            art_html = OrderIngestionArtifact(
                order_ingestion_id=oid,
                artifact_kind=OrderIngestionArtifactKind.HTML.value,
                object_key=key_html,
                file_name=f"{mid_norm[:80] or 'message'}.html",
                mime_type="text/html",
                size_bytes=sz_html,
            )
            session.add(art_html)

            non_img = list_non_image_attachments(persist_msg)
            for att in non_img:
                fn = att.filename or "attachment"
                payload = att.payload
                ct = att.content_type or "application/octet-stream"
                key_att, sz_att = upload_order_ingestion_bytes(
                    storage_type="POattachments",
                    file_name=fn,
                    content=payload,
                    content_type=ct,
                )
                session.add(
                    OrderIngestionArtifact(
                        order_ingestion_id=oid,
                        artifact_kind=OrderIngestionArtifactKind.PO_ATTACHMENT.value,
                        object_key=key_att,
                        file_name=fn[:255],
                        mime_type=ct[:255] if ct else None,
                        size_bytes=sz_att,
                    )
                )

            run.no_attachment_order = len(non_img) == 0
            run.updated_at = datetime.now(timezone.utc)
            session.add(run)
            session.commit()

            return {
                "duplicate": False,
                "order_ingestion_id": str(oid),
                "no_attachment_order": run.no_attachment_order,
                "order_user_email": order_user_email,
                "in_reply_to": irt,
                "anchor_message_id_norm": mid_norm,
            }


@activity.defn(name="save_order_user_html_eml_from_hop_activity")
def save_order_user_html_eml_from_hop_activity(
    order_ingestion_id: str,
    mailbox_email: str,
    imap_uid: str,
    order_user_email: str,
) -> dict[str, Any]:
    oid = uuid.UUID(order_ingestion_id)
    fetch_res = imap_pool.fetch_message_by_uid(mailbox_email, str(imap_uid))
    if fetch_res.reason == imap_pool.IMAP_SENDER_MAILBOX_ERROR:
        return {"saved": False, "reason": imap_pool.IMAP_SENDER_MAILBOX_ERROR}
    if not fetch_res.message:
        return {"saved": False, "reason": "hop_message_not_found"}
    msg = fetch_res.message

    recipient_emails = {
        str(a.email).strip().lower()
        for a in [*msg.to_values, *msg.cc_values]
        if a.email
    }
    target = str(order_user_email or "").strip().lower()
    if not target or target not in recipient_emails:
        return {"saved": False, "reason": "order_user_not_in_recipients"}

    with Session(engine) as session:
        run = session.get(OrderIngestionRun, oid)
        if not run:
            return {"saved": False, "reason": "run_not_found"}

        mid_raw = get_header_single(msg, "message-id")
        mid_norm = normalize_message_id(mid_raw)[:512] if mid_raw else None
        raw_eml = msg.obj.as_bytes()
        html_doc = render_html_document(msg)

        eml_art = session.exec(
            select(OrderIngestionArtifact).where(
                OrderIngestionArtifact.order_ingestion_id == oid,
                OrderIngestionArtifact.artifact_kind == OrderIngestionArtifactKind.EML.value,
            )
        ).first()
        html_art = session.exec(
            select(OrderIngestionArtifact).where(
                OrderIngestionArtifact.order_ingestion_id == oid,
                OrderIngestionArtifact.artifact_kind == OrderIngestionArtifactKind.HTML.value,
            )
        ).first()

        if eml_art:
            key_eml, sz_eml = upload_order_ingestion_bytes(
                storage_type="eml",
                file_name=eml_art.file_name,
                content=raw_eml,
                content_type="message/rfc822",
            )
            eml_art.object_key = key_eml
            eml_art.size_bytes = sz_eml
            eml_art.mime_type = "message/rfc822"
            session.add(eml_art)
        if html_art:
            key_html, sz_html = upload_order_ingestion_bytes(
                storage_type="html",
                file_name=html_art.file_name,
                content=html_doc.encode("utf-8"),
                content_type="text/html",
            )
            html_art.object_key = key_html
            html_art.size_bytes = sz_html
            html_art.mime_type = "text/html"
            session.add(html_art)

        row = session.exec(
            select(OrderUserMessageId).where(
                OrderUserMessageId.order_ingestion_id == oid,
                OrderUserMessageId.order_user_email == target,
            )
        ).first()
        if row:
            row.message_id_raw = mid_raw[:512] if mid_raw else None
            row.message_id_normalized = mid_norm
            session.add(row)
        else:
            session.add(
                OrderUserMessageId(
                    order_ingestion_id=oid,
                    order_user_email=target,
                    message_id_raw=mid_raw[:512] if mid_raw else None,
                    message_id_normalized=mid_norm,
                )
            )

        run.order_user_message_id_norm = mid_norm
        run.updated_at = datetime.now(timezone.utc)
        session.add(run)
        session.commit()
    return {"saved": True}


@activity.defn(name="resolve_in_reply_to_hop_activity")
def resolve_in_reply_to_hop_activity(in_reply_to: str, sender_email: str | None = None) -> dict[str, Any]:
    if not in_reply_to or not in_reply_to.strip():
        activity.logger.info(
            "resolve_in_reply_to_hop_activity: found=false",
            extra={
                "reason": "empty_in_reply_to",
                "in_reply_to": in_reply_to,
                "sender_email": sender_email,
            },
        )
        return {"found": False, "reason": "empty_in_reply_to"}
    if not sender_email or not str(sender_email).strip():
        activity.logger.info(
            "resolve_in_reply_to_hop_activity: found=false",
            extra={
                "reason": "missing_sender_email",
                "in_reply_to": in_reply_to,
                "sender_email": sender_email,
            },
        )
        return {"found": False, "reason": "missing_sender_email"}
    target_id = str(in_reply_to).strip()
    if not target_id:
        activity.logger.info(
            "resolve_in_reply_to_hop_activity: found=false",
            extra={
                "reason": "empty_target_id_after_strip",
                "in_reply_to": in_reply_to,
                "sender_email": sender_email,
                "target_id": target_id,
            },
        )
        return {"found": False, "reason": "empty_target_id_after_strip"}
    mailbox_email = str(sender_email).strip()
    if not imap_pool.has_mailbox_for_email(mailbox_email):
        activity.logger.info(
            "resolve_in_reply_to_hop_activity: found=false",
            extra={
                "reason": "sender_mailbox_not_in_pool",
                "in_reply_to": in_reply_to,
                "sender_email": sender_email,
                "target_id": target_id,
                "mailbox_email": mailbox_email,
            },
        )
        return {
            "found": False,
            "reason": "sender_mailbox_not_in_pool",
            "sender_email": mailbox_email,
        }
    inbox_res = imap_pool.find_message_in_sender_inbox(mailbox_email, target_id)
    if inbox_res.error_reason == imap_pool.IMAP_SENDER_MAILBOX_ERROR:
        activity.logger.warning(
            "resolve_in_reply_to_hop_activity: found=false (IMAP transport)",
            extra={
                "reason": imap_pool.IMAP_SENDER_MAILBOX_ERROR,
                "in_reply_to": in_reply_to,
                "sender_email": sender_email,
                "target_id": target_id,
                "mailbox_email": mailbox_email,
            },
        )
        return {
            "found": False,
            "reason": imap_pool.IMAP_SENDER_MAILBOX_ERROR,
            "sender_email": mailbox_email,
            "target_id": target_id,
        }
    if inbox_res.error_reason == imap_pool.SENDER_MAILBOX_NOT_IN_POOL:
        activity.logger.info(
            "resolve_in_reply_to_hop_activity: found=false",
            extra={
                "reason": imap_pool.SENDER_MAILBOX_NOT_IN_POOL,
                "in_reply_to": in_reply_to,
                "sender_email": sender_email,
                "target_id": target_id,
                "mailbox_email": mailbox_email,
            },
        )
        return {
            "found": False,
            "reason": imap_pool.SENDER_MAILBOX_NOT_IN_POOL,
            "sender_email": mailbox_email,
            "target_id": target_id,
        }
    if not inbox_res.message:
        activity.logger.info(
            "resolve_in_reply_to_hop_activity: found=false",
            extra={
                "reason": imap_pool.MESSAGE_ID_NOT_FOUND_IN_SENDER_MAILBOX,
                "in_reply_to": in_reply_to,
                "sender_email": sender_email,
                "target_id": target_id,
                "mailbox_email": mailbox_email,
            },
        )
        return {
            "found": False,
            "reason": imap_pool.MESSAGE_ID_NOT_FOUND_IN_SENDER_MAILBOX,
            "sender_email": mailbox_email,
            "target_id": target_id,
        }
    msg = inbox_res.message
    uid = msg.uid or ""
    mid = normalize_message_id(get_header_single(msg, "message-id"))
    next_irt = get_header_single(msg, "in-reply-to")
    from_email = primary_email_from_header(msg.from_ or "")
    return {
        "found": True,
        "mailbox_email": mailbox_email,
        "uid": str(uid),
        "message_id_norm": mid,
        "from_header": msg.from_ or "",
        "from_email": from_email,
        "to_emails": [str(a.email).strip().lower() for a in msg.to_values if a.email],
        "cc_emails": [str(a.email).strip().lower() for a in msg.cc_values if a.email],
        "cc_storage": cc_formatted_for_storage(msg),
        "in_reply_to": next_irt,
    }


@activity.defn(name="classify_hop_sender_activity")
def classify_hop_sender_activity(from_header: str) -> str:
    from_email = primary_email_from_header(from_header)
    with Session(engine) as session:
        if from_email in _order_user_emails(session):
            return "order_user"
        if from_email in _internal_order_user_emails(session):
            return "internal_order_user"
        return "non_internal"


@activity.defn(name="persist_external_correspondent_activity")
def persist_external_correspondent_activity(
    order_ingestion_id: str,
    mailbox_email: str,
    imap_uid: str,
) -> None:
    oid = uuid.UUID(order_ingestion_id)
    fetch_res = imap_pool.fetch_message_by_uid(mailbox_email, str(imap_uid))
    if fetch_res.reason == imap_pool.IMAP_SENDER_MAILBOX_ERROR:
        logger.warning(
            "persist_external_correspondent_activity: IMAP error fetching hop message",
            extra={"order_ingestion_id": order_ingestion_id, "mailbox_email": mailbox_email},
        )
        return
    msg = fetch_res.message
    if not msg:
        return
    with Session(engine) as session:
        run = session.get(OrderIngestionRun, oid)
        if not run:
            return
        from_email = primary_email_from_header(msg.from_ or "")
        run.external_correspondent_from = (from_email or msg.from_ or "")[:1024]
        run.external_correspondent_cc = cc_formatted_for_storage(msg)[:4096]
        run.external_correspondent_domain = email_domain(from_email)[:255] or None
        if msg.date:
            if msg.date.tzinfo is None:
                run.external_correspondent_at = msg.date.replace(tzinfo=timezone.utc)
            else:
                run.external_correspondent_at = msg.date.astimezone(timezone.utc)
        run.updated_at = datetime.now(timezone.utc)
        session.add(run)
        session.commit()


@activity.defn(name="save_po_html_if_needed_activity")
def save_po_html_if_needed_activity(
    order_ingestion_id: str,
    mailbox_email: str,
    imap_uid: str,
) -> dict[str, Any]:
    oid = uuid.UUID(order_ingestion_id)
    file_name = f"po-body-{imap_uid}.html"[:255]
    with Session(engine) as session:
        run = session.get(OrderIngestionRun, oid)
        if not run or not run.no_attachment_order:
            return {
                "saved_non_image_count": 0,
                "saved_html_fallback": False,
                "reason": "no_attachment_order_false_or_run_missing",
            }
        existing = session.exec(
            select(OrderIngestionArtifact).where(
                OrderIngestionArtifact.order_ingestion_id == oid,
                OrderIngestionArtifact.artifact_kind == OrderIngestionArtifactKind.PO_ATTACHMENT.value,
                OrderIngestionArtifact.file_name == file_name,
            )
        ).first()
        if existing:
            return {
                "saved_non_image_count": 0,
                "saved_html_fallback": False,
                "reason": "html_fallback_already_saved",
            }
    fetch_res = imap_pool.fetch_message_by_uid(mailbox_email, str(imap_uid))
    if fetch_res.reason == imap_pool.IMAP_SENDER_MAILBOX_ERROR:
        return {
            "saved_non_image_count": 0,
            "saved_html_fallback": False,
            "reason": imap_pool.IMAP_SENDER_MAILBOX_ERROR,
        }
    msg = fetch_res.message
    if not msg:
        return {
            "saved_non_image_count": 0,
            "saved_html_fallback": False,
            "reason": "external_message_not_found",
        }
    non_img = list_non_image_attachments(msg)
    if non_img:
        saved_count = 0
        with Session(engine) as session:
            existing_rows = session.exec(
                select(OrderIngestionArtifact).where(
                    OrderIngestionArtifact.order_ingestion_id == oid,
                    OrderIngestionArtifact.artifact_kind
                    == OrderIngestionArtifactKind.PO_ATTACHMENT.value,
                )
            ).all()
            existing_names = {row.file_name for row in existing_rows}
            for att in non_img:
                fn = f"external-{imap_uid}-{(att.filename or 'attachment')}"[:255]
                if fn in existing_names:
                    continue
                payload = att.payload
                ct = att.content_type or "application/octet-stream"
                key_att, sz_att = upload_order_ingestion_bytes(
                    storage_type="POattachments",
                    file_name=fn,
                    content=payload,
                    content_type=ct,
                )
                session.add(
                    OrderIngestionArtifact(
                        order_ingestion_id=oid,
                        artifact_kind=OrderIngestionArtifactKind.PO_ATTACHMENT.value,
                        object_key=key_att,
                        file_name=fn,
                        mime_type=ct[:255] if ct else None,
                        size_bytes=sz_att,
                    )
                )
                saved_count += 1
            session.commit()
        return {
            "saved_non_image_count": saved_count,
            "saved_html_fallback": False,
            "reason": "saved_external_non_image_attachments",
        }
    html_doc = html_for_po_attachment(msg)
    key, sz = upload_order_ingestion_bytes(
        storage_type="POattachments",
        file_name=f"po-body-{imap_uid}.html",
        content=html_doc.encode("utf-8"),
        content_type="text/html",
    )
    with Session(engine) as session:
        session.add(
            OrderIngestionArtifact(
                order_ingestion_id=oid,
                artifact_kind=OrderIngestionArtifactKind.PO_ATTACHMENT.value,
                object_key=key,
                file_name=file_name,
                mime_type="text/html",
                size_bytes=sz,
            )
        )
        session.commit()
    return {
        "saved_non_image_count": 0,
        "saved_html_fallback": True,
        "reason": "saved_external_html_fallback",
    }


@activity.defn(name="finalize_ingestion_activity")
def finalize_ingestion_activity(order_ingestion_id: str, status: str, _error_message: str | None = None) -> None:
    oid = uuid.UUID(order_ingestion_id)
    with Session(engine) as session:
        run = session.get(OrderIngestionRun, oid)
        if not run:
            return
        run.status = status[:32]
        run.updated_at = datetime.now(timezone.utc)
        session.add(run)
        session.commit()


@activity.defn(name="mark_central_message_seen_activity")
def mark_central_message_seen_activity(central_mailbox_config_id: str, imap_uid: str) -> None:
    cid = uuid.UUID(central_mailbox_config_id)
    with Session(engine) as session:
        cfg = session.get(MailboxConfig, cid)
        if not cfg:
            return
        with _open_mailbox(cfg) as mb:
            for _ in mb.fetch(f"UID {imap_uid}", mark_seen=True, limit=1):
                break
