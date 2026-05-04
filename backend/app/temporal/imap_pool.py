"""Process-local lazy IMAP mailbox pool (excluding central ingestion mailbox).

All pooled IMAP use for a given mailbox email is serialized (one in-flight command
stream per mailbox) so concurrent activities do not interleave reads on the same
imaplib client. Transport failures trigger evict + DB re-login + one retry.
"""

from __future__ import annotations

import errno
import imaplib
import logging
import ssl
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from imap_tools import MailBox, MailBoxUnencrypted, MailMessage
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.crypto import decrypt_secret
from app.core.db import engine
from app.models.mail_access import MailboxConfig, MailboxScopeType

logger = logging.getLogger(__name__)

_pool: dict[str, MailBox] = {}
_central_mailbox_config_id: uuid.UUID | None = None

_mailbox_locks: dict[str, threading.Lock] = {}
_mailbox_locks_guard = threading.Lock()

T = TypeVar("T")

# --- Explicit outcomes for workflows / logs (do not conflate transport with "not found") ---

SENDER_MAILBOX_NOT_IN_POOL = "sender_mailbox_not_in_pool"
IMAP_SENDER_MAILBOX_ERROR = "imap_sender_mailbox_error"
MESSAGE_ID_NOT_FOUND_IN_SENDER_MAILBOX = "message_id_not_found_in_sender_mailbox"
MESSAGE_NOT_FOUND = "message_not_found"


@dataclass(frozen=True)
class SenderInboxLookupResult:
    message: MailMessage | None
    """Set when a matching message was found."""

    error_reason: str | None = None
    """When ``message`` is None: why lookup failed (see module constants)."""


@dataclass(frozen=True)
class UidFetchResult:
    message: MailMessage | None
    reason: str | None = None
    """None on success; otherwise one of the module reason constants."""


def set_central_mailbox_config_id(central_id: uuid.UUID | None) -> None:
    global _central_mailbox_config_id
    _central_mailbox_config_id = central_id


def _lock_for_mailbox(mailbox_email: str) -> threading.Lock:
    key = mailbox_email.strip().lower()
    with _mailbox_locks_guard:
        lock = _mailbox_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _mailbox_locks[key] = lock
        return lock


def _is_transport_failure(exc: BaseException) -> bool:
    if isinstance(exc, imaplib.IMAP4.abort):
        return True
    if isinstance(
        exc,
        (
            BrokenPipeError,
            ConnectionResetError,
            ConnectionAbortedError,
            TimeoutError,
            ConnectionError,
        ),
    ):
        return True
    if isinstance(exc, ssl.SSLError):
        return True
    if isinstance(exc, OSError):
        err = getattr(exc, "errno", None)
        if err in {errno.ECONNRESET, errno.ECONNABORTED, errno.ETIMEDOUT, errno.EPIPE, errno.ENOTCONN}:
            return True
        winerr = getattr(exc, "winerror", None)
        if winerr in {10053, 10054, 10060, 10058}:
            return True
        msg = str(exc).lower()
        if any(s in msg for s in ("eof", "connection reset", "broken pipe", "timed out")):
            return True
    return False


def _ssl_context_if_needed(use_ssl: bool) -> ssl.SSLContext | None:
    if not use_ssl:
        return None
    return ssl.create_default_context()


def _login_from_config(cfg: MailboxConfig) -> MailBox:
    pwd = decrypt_secret(cfg.encrypted_app_password)
    if cfg.imap_ssl:
        ssl_ctx = _ssl_context_if_needed(True)
        return MailBox(cfg.imap_host, cfg.imap_port, ssl_context=ssl_ctx).login(
            cfg.email, pwd, initial_folder="INBOX"
        )
    return MailBoxUnencrypted(cfg.imap_host, cfg.imap_port).login(
        cfg.email, pwd, initial_folder="INBOX"
    )


def _resolve_pool_dict_key(mailbox_email: str) -> str | None:
    if mailbox_email in _pool:
        return mailbox_email
    lower = mailbox_email.lower()
    for k in _pool:
        if k.lower() == lower:
            return k
    return None


def _evict_mailbox_connection_nolock(mailbox_email: str) -> None:
    key = _resolve_pool_dict_key(mailbox_email)
    if not key:
        return
    mb = _pool.pop(key, None)
    if mb is not None:
        try:
            mb.logout()
        except Exception:
            logger.exception(
                "IMAP logout failed during pooled mailbox evict",
                extra={"pool_key": key},
            )


def _load_user_linked_cfg(session: Session, mailbox_email: str) -> MailboxConfig | None:
    target = mailbox_email.strip().lower()
    return session.exec(
        select(MailboxConfig).where(
            MailboxConfig.is_active == True,  # noqa: E712
            MailboxConfig.scope_type == MailboxScopeType.USER_LINKED,
            func.lower(MailboxConfig.email) == target,
        )
    ).first()


def _reconnect_mailbox_to_pool_nolock(mailbox_email: str) -> bool:
    """Re-login one mailbox and store under ``cfg.email``. Caller must hold the mailbox lock."""
    with Session(engine) as session:
        cfg = _load_user_linked_cfg(session, mailbox_email)
        if cfg is None:
            logger.error(
                "Cannot reconnect pooled mailbox: config not found",
                extra={"mailbox_email": mailbox_email},
            )
            return False
        if _central_mailbox_config_id is not None and cfg.id == _central_mailbox_config_id:
            logger.error(
                "Cannot reconnect: mailbox is central ingestion id",
                extra={"mailbox_config_id": str(cfg.id)},
            )
            return False
        try:
            mb = _login_from_config(cfg)
            _pool[cfg.email] = mb
            return True
        except Exception:
            logger.exception(
                "Failed to reconnect mailbox to IMAP pool",
                extra={"mailbox_config_id": str(cfg.id), "email": cfg.email},
            )
            return False


def _run_under_mailbox_lock(
    mailbox_email: str,
    fn: Callable[[MailBox], T],
) -> tuple[T | None, str | None]:
    """Run ``fn(mb)`` with exclusive access to that mailbox's connection.

    Returns ``(value, None)`` on success (``value`` may be None if ``fn`` returns that).
    On failure returns ``(None, error_reason_constant)``.
    """
    lock = _lock_for_mailbox(mailbox_email)
    with lock:
        for attempt in (0, 1):
            mb = _get_mailbox_for_email(mailbox_email)
            if mb is None:
                if attempt == 0:
                    return None, SENDER_MAILBOX_NOT_IN_POOL
                return None, IMAP_SENDER_MAILBOX_ERROR
            try:
                return fn(mb), None
            except Exception as exc:
                if _is_transport_failure(exc) and attempt == 0:
                    logger.warning(
                        "IMAP transport failure on pooled mailbox; evicting and reconnecting once",
                        extra={"mailbox_email": mailbox_email, "exc_type": type(exc).__name__},
                    )
                    _evict_mailbox_connection_nolock(mailbox_email)
                    if not _reconnect_mailbox_to_pool_nolock(mailbox_email):
                        return None, IMAP_SENDER_MAILBOX_ERROR
                    continue
                logger.exception(
                    "IMAP pooled operation failed",
                    extra={"mailbox_email": mailbox_email, "attempt": attempt},
                )
                return None, IMAP_SENDER_MAILBOX_ERROR
        return None, IMAP_SENDER_MAILBOX_ERROR


def clear_pool() -> None:
    global _pool
    for _email, mb in list(_pool.items()):
        try:
            mb.logout()
        except Exception:
            logger.exception("IMAP logout failed for pooled mailbox")
    _pool.clear()


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
        with _lock_for_mailbox(cfg.email):
            if _get_mailbox_for_email(cfg.email) is not None:
                continue
            try:
                mb = _login_from_config(cfg)
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


def _search_pool_mailbox_for_rfc_id(mb: MailBox, target: str, quoted: str) -> MailMessage | None:
    crit = f'HEADER Message-ID "{quoted}"'
    msgs = list(mb.fetch(crit, mark_seen=False))
    if msgs:
        return msgs[0]
    msgs = list(mb.fetch(f'TEXT "{quoted}"', mark_seen=False))
    for msg in msgs:
        mid = (msg.headers.get("message-id") or ("",))[0]
        if target in str(mid):
            return msg
    return None


def find_message_by_rfc_message_id(message_id: str) -> tuple[str | None, MailMessage | None]:
    """Search pool mailboxes for Message-ID; return (mailbox_email, message)."""
    target = str(message_id).strip().replace('"', "")
    if not target:
        return None, None
    quoted = target.replace("\\", "\\\\").replace('"', '\\"')
    for mailbox_key in list(_pool.keys()):

        def op(mb: MailBox, _q: str = quoted, _t: str = target) -> MailMessage | None:
            return _search_pool_mailbox_for_rfc_id(mb, _t, _q)

        msg, err = _run_under_mailbox_lock(mailbox_key, op)
        if err:
            logger.warning(
                "IMAP search skipped for mailbox after error",
                extra={"mailbox_email": mailbox_key, "error_reason": err},
            )
            continue
        if msg:
            return mailbox_key, msg
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
    """Search order-user mailbox across common folders for RFC Message-ID."""

    def op(mb: MailBox) -> MailMessage | None:
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
                    msg = _search_pool_mailbox_for_rfc_id(mb, target, quoted)
                    if msg:
                        return msg
                except Exception as exc:
                    if _is_transport_failure(exc):
                        raise
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

    msg, err = _run_under_mailbox_lock(mailbox_email, op)
    if err:
        logger.warning(
            "Folder search aborted for mailbox",
            extra={"mailbox_email": mailbox_email, "error_reason": err},
        )
    return msg


def find_message_by_rfc_message_id_in_mailbox(
    mailbox_email: str, message_id: str,
) -> MailMessage | None:
    target = str(message_id).strip().replace('"', "")
    if not target:
        return None
    quoted = target.replace("\\", "\\\\").replace('"', '\\"')

    def op(mb: MailBox) -> MailMessage | None:
        return _search_pool_mailbox_for_rfc_id(mb, target, quoted)

    msg, err = _run_under_mailbox_lock(mailbox_email, op)
    if err:
        logger.warning(
            "Targeted Message-ID search failed",
            extra={"mailbox_email": mailbox_email, "error_reason": err},
        )
    return msg


def find_message_in_sender_inbox(sender_email: str, target_id: str) -> SenderInboxLookupResult:
    """Search only sender mailbox (INBOX): header Message-ID match, then text fallback."""
    if not sender_email or not target_id:
        return SenderInboxLookupResult(None, MESSAGE_ID_NOT_FOUND_IN_SENDER_MAILBOX)

    quoted = str(target_id).strip().replace("\\", "\\\\").replace('"', '\\"')
    tid = str(target_id).strip()

    def op(mb: MailBox) -> MailMessage | None:
        messages = list(mb.fetch(f'HEADER Message-ID "{quoted}"', mark_seen=False))
        if messages:
            return messages[0]
        messages = list(mb.fetch(f'TEXT "{quoted}"', mark_seen=False))
        for msg in messages:
            header_val = msg.headers.get("message-id", "")
            if tid in str(header_val):
                return msg
        return None

    msg, err = _run_under_mailbox_lock(sender_email, op)
    if err:
        if err == SENDER_MAILBOX_NOT_IN_POOL:
            return SenderInboxLookupResult(None, SENDER_MAILBOX_NOT_IN_POOL)
        return SenderInboxLookupResult(None, IMAP_SENDER_MAILBOX_ERROR)
    if msg is None:
        return SenderInboxLookupResult(None, MESSAGE_ID_NOT_FOUND_IN_SENDER_MAILBOX)
    return SenderInboxLookupResult(msg, None)


def fetch_message_by_uid(mailbox_email: str, uid: str) -> UidFetchResult:
    if not mailbox_email or not uid:
        return UidFetchResult(None, MESSAGE_NOT_FOUND)

    def op(mb: MailBox) -> MailMessage | None:
        for msg in mb.fetch(f"UID {uid}", mark_seen=False, limit=1):
            return msg
        return None

    msg, err = _run_under_mailbox_lock(mailbox_email, op)
    if err:
        return UidFetchResult(None, err)
    if msg is None:
        return UidFetchResult(None, MESSAGE_NOT_FOUND)
    return UidFetchResult(msg, None)
