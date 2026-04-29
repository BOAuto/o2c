"""O2C scheduler and per-message ingestion workflows."""

from __future__ import annotations

import re
from datetime import timedelta

from temporalio import workflow
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

with workflow.unsafe.imports_passed_through():
    import asyncio

    from app.temporal.activities.ingestion_activities import (
        classify_central_sender_activity,
        classify_hop_sender_activity,
        ensure_mailbox_pool_activity,
        finalize_ingestion_activity,
        load_scheduler_config_activity,
        mark_central_message_seen_activity,
        persist_external_correspondent_activity,
        poll_central_unread_activity,
        record_internal_unmapped_sender_activity,
        record_rejected_central_sender_activity,
        resolve_in_reply_to_hop_activity,
        save_order_user_anchor_activity,
        save_order_user_html_eml_from_hop_activity,
        save_po_html_if_needed_activity,
    )

_ACTIVITY_TIMEOUT = timedelta(minutes=15)
_SHORT_ACTIVITY = timedelta(minutes=2)


def _normalize_message_id(value: str | None) -> str:
    if not value:
        return ""
    s = value.strip()
    s = re.sub(r"^[<>]+|[<>]+$", "", s)
    return s.strip().lower()


@workflow.defn(name="O2CIngestionSchedulerWorkflow")
class O2CIngestionSchedulerWorkflow:
    def __init__(self) -> None:
        self._period_minutes: int = 5
        self._period_dirty: bool = False
        self._started_uids: set[str] = set()
        self._poll_now: bool = False
        self._last_poll_now_signal_at = None

    @workflow.signal
    async def retrieval_period_updated(self, minutes: int) -> None:
        self._period_minutes = max(1, int(minutes))
        self._period_dirty = True

    @workflow.signal
    async def poll_now_requested(self) -> None:
        """Wake the scheduler to run ``poll_central_unread_activity`` on the next loop."""
        now = workflow.now()
        if self._last_poll_now_signal_at is not None:
            elapsed = now - self._last_poll_now_signal_at
            if elapsed < timedelta(minutes=1):
                return
        self._last_poll_now_signal_at = now
        self._poll_now = True

    async def _sleep_until_next_poll(self) -> None:
        """Sleep until the poll interval elapses, or wake immediately on signal ``poll_now`` / period change."""
        while True:
            deadline = workflow.now() + timedelta(minutes=max(1, self._period_minutes))
            while True:
                if self._poll_now:
                    self._poll_now = False
                    return
                if self._period_dirty:
                    self._period_dirty = False
                    break
                remaining_sec = (deadline - workflow.now()).total_seconds()
                if remaining_sec <= 0:
                    return
                try:
                    await workflow.wait_condition(
                        lambda: self._poll_now or self._period_dirty,
                        timeout=timedelta(seconds=remaining_sec),
                    )
                except asyncio.TimeoutError:
                    return

    @workflow.run
    async def run(self, initial_period_minutes: int) -> None:
        self._period_minutes = max(1, int(initial_period_minutes))
        first_tick = True
        while True:
            if not first_tick:
                await self._sleep_until_next_poll()
            first_tick = False
            cfg = await workflow.execute_activity(
                load_scheduler_config_activity,
                start_to_close_timeout=_SHORT_ACTIVITY,
            )
            self._period_minutes = max(1, int(cfg["period_minutes"]))
            items = await workflow.execute_activity(
                poll_central_unread_activity,
                start_to_close_timeout=_ACTIVITY_TIMEOUT,
            )
            central_id = cfg["central_mailbox_config_id"]
            to_start: list[tuple[str, str]] = []
            for it in items:
                uid = it["uid"]
                if uid in self._started_uids:
                    continue
                self._started_uids.add(uid)
                child_id = f"o2c-msg-{central_id}-{uid}"
                to_start.append((uid, child_id))

            async def _start_child(
                uid: str, child_id: str, start_central_id: str = central_id
            ) -> None:
                try:
                    await workflow.start_child_workflow(
                        O2CMessageIngestionWorkflow.run,
                        args=[start_central_id, uid],
                        id=child_id,
                        id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY,
                    )
                except WorkflowAlreadyStartedError:
                    # Child is already running/open under same deterministic ID.
                    # Skip and keep scheduler alive for subsequent messages.
                    pass

            if to_start:
                await asyncio.gather(*[_start_child(uid, child_id) for uid, child_id in to_start])


@workflow.defn(name="O2CMessageIngestionWorkflow")
class O2CMessageIngestionWorkflow:
    @workflow.run
    async def run(self, central_mailbox_config_id: str, imap_uid: str) -> None:
        cls = await workflow.execute_activity(
            classify_central_sender_activity,
            args=[central_mailbox_config_id, imap_uid],
            start_to_close_timeout=_ACTIVITY_TIMEOUT,
        )
        if cls.get("result") != "order_user":
            if cls.get("result") == "internal_non_mail_access_sender":
                await workflow.execute_activity(
                    record_internal_unmapped_sender_activity,
                    args=[central_mailbox_config_id, imap_uid],
                    start_to_close_timeout=_ACTIVITY_TIMEOUT,
                )
            else:
                reason = cls.get("reason") or "external"
                await workflow.execute_activity(
                    record_rejected_central_sender_activity,
                    args=[central_mailbox_config_id, imap_uid, str(reason)],
                    start_to_close_timeout=_ACTIVITY_TIMEOUT,
                )
            await workflow.execute_activity(
                mark_central_message_seen_activity,
                args=[central_mailbox_config_id, imap_uid],
                start_to_close_timeout=_SHORT_ACTIVITY,
            )
            return

        await workflow.execute_activity(
            ensure_mailbox_pool_activity,
            args=[central_mailbox_config_id],
            start_to_close_timeout=_ACTIVITY_TIMEOUT,
        )

        anchor = await workflow.execute_activity(
            save_order_user_anchor_activity,
            args=[central_mailbox_config_id, imap_uid],
            start_to_close_timeout=_ACTIVITY_TIMEOUT,
        )
        order_id = str(anchor["order_ingestion_id"])
        is_duplicate = bool(anchor.get("duplicate"))
        if is_duplicate:
            workflow.logger.info(
                "Duplicate anchor detected; reusing existing run and continuing hop resolution",
                extra={"order_ingestion_id": order_id, "imap_uid": imap_uid},
            )

        no_attachment_order = bool(anchor.get("no_attachment_order"))
        target_order_user_email = str(anchor.get("order_user_email") or "").strip().lower()
        order_user_hop_saved = False
        irt: str | None = anchor.get("in_reply_to")
        next_sender_email: str | None = cls.get("sender_mailbox_email")
        visited_msg: set[str] = set()
        anchor_mid = str(anchor.get("anchor_message_id_norm") or "")
        if anchor_mid:
            visited_msg.add(anchor_mid)
        visited_irt: set[str] = set()
        external_found = False

        if not irt or not str(irt).strip():
            workflow.logger.info(
                "No in-reply-to present on anchor; finishing without hop traversal",
                extra={"order_ingestion_id": order_id, "imap_uid": imap_uid},
            )

        while irt and str(irt).strip():
            nk = _normalize_message_id(str(irt))
            if not nk or nk in visited_irt:
                workflow.logger.info(
                    "Stopping hop traversal due to empty/visited in-reply-to",
                    extra={
                        "order_ingestion_id": order_id,
                        "in_reply_to_normalized": nk,
                    },
                )
                break
            visited_irt.add(nk)
            hop = await workflow.execute_activity(
                resolve_in_reply_to_hop_activity,
                args=[str(irt), next_sender_email],
                start_to_close_timeout=_ACTIVITY_TIMEOUT,
            )
            if not hop.get("found"):
                workflow.logger.info(
                    "Stopping hop traversal because in-reply-to message was not found",
                    extra={"order_ingestion_id": order_id, "in_reply_to": str(irt)},
                )
                break
            pid = str(hop.get("message_id_norm") or "")
            if pid and pid in visited_msg:
                workflow.logger.info(
                    "Stopping hop traversal due to visited message-id loop guard",
                    extra={"order_ingestion_id": order_id, "message_id_norm": pid},
                )
                break
            if pid:
                visited_msg.add(pid)

            if not order_user_hop_saved and target_order_user_email:
                to_emails = {str(x).strip().lower() for x in (hop.get("to_emails") or []) if x}
                cc_emails = {str(x).strip().lower() for x in (hop.get("cc_emails") or []) if x}
                if target_order_user_email in to_emails or target_order_user_email in cc_emails:
                    _ = await workflow.execute_activity(
                        save_order_user_html_eml_from_hop_activity,
                        args=[
                            order_id,
                            str(hop["mailbox_email"]),
                            str(hop["uid"]),
                            target_order_user_email,
                        ],
                        start_to_close_timeout=_ACTIVITY_TIMEOUT,
                    )
                    order_user_hop_saved = True

            hop_kind = await workflow.execute_activity(
                classify_hop_sender_activity,
                args=[str(hop.get("from_header") or "")],
                start_to_close_timeout=_SHORT_ACTIVITY,
            )
            if hop_kind in ("order_user", "internal_order_user"):
                workflow.logger.info(
                    "Internal chain hop continued",
                    extra={
                        "order_ingestion_id": order_id,
                        "hop_kind": hop_kind,
                        "mailbox_email": str(hop.get("mailbox_email") or ""),
                    },
                )
                irt = hop.get("in_reply_to")
                next_sender_email = str(hop.get("from_email") or "")
                continue

            await workflow.execute_activity(
                persist_external_correspondent_activity,
                args=[
                    order_id,
                    str(hop["mailbox_email"]),
                    str(hop["uid"]),
                ],
                start_to_close_timeout=_ACTIVITY_TIMEOUT,
            )
            if no_attachment_order:
                po_result = await workflow.execute_activity(
                    save_po_html_if_needed_activity,
                    args=[
                        order_id,
                        str(hop["mailbox_email"]),
                        str(hop["uid"]),
                    ],
                    start_to_close_timeout=_ACTIVITY_TIMEOUT,
                )
                workflow.logger.info(
                    "PO attachment fallback step completed",
                    extra={
                        "order_ingestion_id": order_id,
                        "po_result": po_result,
                    },
                )
            external_found = True
            workflow.logger.info(
                "External hop found and persisted",
                extra={
                    "order_ingestion_id": order_id,
                    "mailbox_email": str(hop["mailbox_email"]),
                    "uid": str(hop["uid"]),
                    "no_attachment_order": no_attachment_order,
                },
            )
            break

        if not external_found:
            workflow.logger.info(
                "No external correspondent found before workflow completion",
                extra={"order_ingestion_id": order_id},
            )

        await workflow.execute_activity(
            finalize_ingestion_activity,
            args=[order_id, "completed", None],
            start_to_close_timeout=_SHORT_ACTIVITY,
        )
        await workflow.execute_activity(
            mark_central_message_seen_activity,
            args=[central_mailbox_config_id, imap_uid],
            start_to_close_timeout=_SHORT_ACTIVITY,
        )
