import uuid
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.crypto import encrypt_secret
from app.models import (
    MailAccessType,
    MailboxConfig,
    MailboxScopeType,
    UserMailAccess,
)


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
    existing_link = session.exec(
        select(UserMailAccess).where(UserMailAccess.user_id == user_id)
    ).first()
    if access_type is None:
        if existing_link:
            existing_link.is_active = False
            existing_link.updated_at = _now_utc()
            session.add(existing_link)
            session.commit()
        return

    if not app_password:
        # Ignore provisioning when app password is absent.
        # This keeps user updates backward-compatible.
        return

    mailbox = session.exec(
        select(MailboxConfig).where(
            MailboxConfig.scope_type == MailboxScopeType.USER_LINKED,
            MailboxConfig.email == email,
        )
    ).first()
    if not mailbox:
        mailbox = MailboxConfig(
            scope_type=MailboxScopeType.USER_LINKED,
            email=email,
            encrypted_app_password=encrypt_secret(app_password),
        )
        session.add(mailbox)
        session.commit()
        session.refresh(mailbox)
    else:
        mailbox.encrypted_app_password = encrypt_secret(app_password)
        mailbox.updated_at = _now_utc()
        mailbox.is_active = True
        session.add(mailbox)
        session.commit()
        session.refresh(mailbox)

    if existing_link:
        existing_link.mailbox_config_id = mailbox.id
        existing_link.access_type = access_type
        existing_link.is_active = True
        existing_link.updated_at = _now_utc()
        session.add(existing_link)
        session.commit()
        return

    session.add(
        UserMailAccess(
            user_id=user_id,
            mailbox_config_id=mailbox.id,
            access_type=access_type,
            is_active=True,
        )
    )
    session.commit()
