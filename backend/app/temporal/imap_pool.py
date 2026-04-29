"""Process-local lazy IMAP mailbox pool (excluding central ingestion mailbox)."""

from __future__ import annotations

import logging
import ssl
import uuid

from imap_tools import MailBox, MailBoxUnencrypted, MailMessage
from sqlmodel import Session, select

from app.core.crypto import decrypt_secret
from app.models.mail_access import MailboxConfig, MailboxScopeType

logger = logging.getLogger(__name__)

_pool: dict[str, MailBox] = {}
_central_mailbox_config_id: uuid.UUID | None = None


def set_central_mailbox_config_id(central_id: uuid.UUID | None) -> None:
    global _central_mailbox_config_id
    _central_mailbox_config_id = central_id


def clear_pool() -> None:
    global _pool
    for _email, mb in list(_pool.items()):
        try:
            mb.logout()
        except Exception:
            logger.exception("IMAP logout failed for pooled mailbox")
    _pool.clear()


def _ssl_context_if_needed(use_ssl: bool) -> ssl.SSLContext | None:
    if not use_ssl:
        return None
    return ssl.create_default_context()


def ensure_mailbox_pool(session: Session, *, central_config_id: uuid.UUID) -> None:
    """Login all active user-linked mailboxes; skip central id."""
    global _pool
    set_central_mailbox_config_id(central_config_id)
    rows = session.exec(
        select(MailboxConfig).where(
            MailboxConfig.is_active == True,  # noqa: E712
            MailboxConfig.scope_type == MailboxScopeType.USER_LINKED,
        )
    ).all()
    for cfg in rows:
        if cfg.id == central_config_id:
            continue
        if cfg.email in _pool:
            continue
        try:
            pwd = decrypt_secret(cfg.encrypted_app_password)
            if cfg.imap_ssl:
                ssl_ctx = _ssl_context_if_needed(True)
                mb = MailBox(cfg.imap_host, cfg.imap_port, ssl_context=ssl_ctx).login(
                    cfg.email, pwd, initial_folder="INBOX"
                )
            else:
                mb = MailBoxUnencrypted(cfg.imap_host, cfg.imap_port).login(
                    cfg.email, pwd, initial_folder="INBOX"
                )
            _pool[cfg.email] = mb
        except Exception:
            logger.exception(
                "Failed to add mailbox to pool",
                extra={"mailbox_config_id": str(cfg.id), "email": cfg.email},
            )


def _get_mailbox_for_email(mailbox_email: str) -> MailBox | None:
    mb = _pool.get(mailbox_email)
    if mb:
        return mb
    lower = mailbox_email.lower()
    for k, val in _pool.items():
        if k.lower() == lower:
            return val
    return None


def has_mailbox_for_email(mailbox_email: str) -> bool:
    return _get_mailbox_for_email(mailbox_email) is not None


def find_message_by_rfc_message_id(message_id: str) -> tuple[str | None, MailMessage | None]:
    """Search pool mailboxes for Message-ID; return (mailbox_email, message)."""
    target = str(message_id).strip().replace('"', "")
    if not target:
        return None, None
    quoted = target.replace("\\", "\\\\").replace('"', '\\"')
    for mailbox_email, mb in list(_pool.items()):
        try:
            crit = f'HEADER Message-ID "{quoted}"'
            msgs = list(mb.fetch(crit, mark_seen=False))
            if msgs:
                return mailbox_email, msgs[0]
            msgs = list(mb.fetch(f'TEXT "{quoted}"', mark_seen=False))
            for msg in msgs:
                mid = (msg.headers.get("message-id") or ("",))[0]
                if target in str(mid):
                    return mailbox_email, msg
        except Exception:
            logger.exception(
                "IMAP search failed in pooled mailbox",
                extra={"mailbox_email": mailbox_email},
            )
    return None, None


_ORDER_USER_MESSAGE_FOLDERS: tuple[str, ...] = (
    "INBOX",
    "Sent",
    "[Gmail]/Sent Mail",
    "Sent Items",
    "INBOX.Sent",
)


def find_message_by_rfc_message_id_in_mailbox_folders(
    mailbox_email: str, message_id: str,
) -> MailMessage | None:
    """Search order-user (or any pooled) mailbox across common folders for RFC Message-ID.

    A message sent to central often lives in the sender's **Sent** folder with the same
    Message-ID as seen on the central copy; INBOX alone is not always enough.
    """
    mb = _get_mailbox_for_email(mailbox_email)
    if not mb:
        return None
    target = str(message_id).strip().replace('"', "")
    if not target:
        return None
    quoted = target.replace("\\", "\\\\").replace('"', '\\"')
    previous = mb.folder.get()
    folder_order: list[str] = []
    if previous:
        folder_order.append(str(previous))
    for name in _ORDER_USER_MESSAGE_FOLDERS:
        if name not in folder_order:
            folder_order.append(name)

    try:
        for folder in folder_order:
            try:
                mb.folder.set(folder)
            except Exception:
                continue
            try:
                msgs = list(mb.fetch(f'HEADER Message-ID "{quoted}"', mark_seen=False))
                if msgs:
                    return msgs[0]
                msgs = list(mb.fetch(f'TEXT "{quoted}"', mark_seen=False))
                for msg in msgs:
                    mid = (msg.headers.get("message-id") or ("",))[0]
                    if target in str(mid):
                        return msg
            except Exception:
                logger.exception(
                    "IMAP Message-ID folder search failed",
                    extra={"mailbox_email": mailbox_email, "folder": folder},
                )
        return None
    finally:
        restore_to = previous or "INBOX"
        try:
            mb.folder.set(restore_to)
        except Exception:
            try:
                mb.folder.set("INBOX")
            except Exception:
                logger.exception(
                    "IMAP folder restore failed",
                    extra={"mailbox_email": mailbox_email},
                )


def find_message_by_rfc_message_id_in_mailbox(
    mailbox_email: str, message_id: str
) -> MailMessage | None:
    target = str(message_id).strip().replace('"', "")
    if not target:
        return None
    mb = _get_mailbox_for_email(mailbox_email)
    if not mb:
        return None
    quoted = target.replace("\\", "\\\\").replace('"', '\\"')
    try:
        crit = f'HEADER Message-ID "{quoted}"'
        msgs = list(mb.fetch(crit, mark_seen=False))
        if msgs:
            return msgs[0]
        msgs = list(mb.fetch(f'TEXT "{quoted}"', mark_seen=False))
        for msg in msgs:
            mid = (msg.headers.get("message-id") or ("",))[0]
            if target in str(mid):
                return msg
    except Exception:
        logger.exception(
            "IMAP targeted Message-ID search failed",
            extra={"mailbox_email": mailbox_email},
        )
    return None


def find_message_in_sender_inbox(sender_email: str, target_id: str) -> MailMessage | None:
    """Match debug-script behavior: search only sender mailbox, header first then text."""
    if not sender_email or not target_id:
        return None
    mb = _get_mailbox_for_email(sender_email)
    if not mb:
        return None
    try:
        messages = list(mb.fetch(f'HEADER Message-ID "{target_id}"', mark_seen=False))
        if messages:
            return messages[0]
        messages = list(mb.fetch(f'TEXT "{target_id}"', mark_seen=False))
        for msg in messages:
            header_val = msg.headers.get("message-id", "")
            if target_id in str(header_val):
                return msg
    except Exception:
        logger.exception(
            "IMAP sender mailbox search failed",
            extra={"sender_email": sender_email},
        )
    return None


def fetch_message_by_uid(mailbox_email: str, uid: str) -> MailMessage | None:
    mb = _get_mailbox_for_email(mailbox_email)
    if not mb:
        return None
    try:
        for msg in mb.fetch(f"UID {uid}", mark_seen=False, limit=1):
            return msg
    except Exception:
        logger.exception(
            "UID fetch failed",
            extra={"mailbox_email": mailbox_email, "uid": uid},
        )
    return None
