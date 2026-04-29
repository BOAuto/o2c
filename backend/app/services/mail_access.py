import uuid
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.crypto import encrypt_secret
from app.models import MailAccessType, MailboxConfig, MailboxScopeType


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def upsert_user_mail_access(
    *,
    session: Session,
    user_id: uuid.UUID,
    email: str,
    access_type: MailAccessType | None,
    app_password: str | None,
) -> None:
    existing_by_user = session.exec(
        select(MailboxConfig).where(
            MailboxConfig.user_id == user_id,
            MailboxConfig.scope_type == MailboxScopeType.USER_LINKED,
        )
    ).first()
    if access_type is None:
        if existing_by_user:
            existing_by_user.is_active = False
            existing_by_user.updated_at = _now_utc()
            session.add(existing_by_user)
            session.commit()
        return

    if not app_password:
        return

    mailbox = session.exec(
        select(MailboxConfig).where(
            MailboxConfig.scope_type == MailboxScopeType.USER_LINKED,
            MailboxConfig.email == email,
        )
    ).first()

    if not mailbox:
        if existing_by_user:
            existing_by_user.user_id = None
            existing_by_user.mail_access_type = None
            session.add(existing_by_user)
        mailbox = MailboxConfig(
            scope_type=MailboxScopeType.USER_LINKED,
            email=email,
            user_id=user_id,
            mail_access_type=access_type,
            encrypted_app_password=encrypt_secret(app_password),
        )
        session.add(mailbox)
        session.commit()
        return

    if existing_by_user and existing_by_user.id != mailbox.id:
        existing_by_user.user_id = None
        existing_by_user.mail_access_type = None
        session.add(existing_by_user)

    mailbox.user_id = user_id
    mailbox.mail_access_type = access_type
    mailbox.encrypted_app_password = encrypt_secret(app_password)
    mailbox.updated_at = _now_utc()
    mailbox.is_active = True
    session.add(mailbox)
    session.commit()
