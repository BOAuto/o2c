import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select

from app.api.deps import SessionDep, get_current_active_superuser
from app.core.crypto import encrypt_secret
from app.models import (
    MailboxConfig,
    MailboxConfigCreate,
    MailboxConfigPublic,
    MailboxConfigUpdate,
    MailboxScopeType,
    Message,
    User,
    UserMailAccess,
    UserMailAccessCreate,
    UserMailAccessesPublic,
    UserMailAccessPublic,
    UserMailAccessUpdate,
)

router = APIRouter(
    prefix="/mail-access",
    tags=["mail-access"],
    dependencies=[Depends(get_current_active_superuser)],
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/central", response_model=MailboxConfigPublic | None)
def get_central_mailbox(session: SessionDep) -> MailboxConfigPublic | None:
    mailbox = session.exec(
        select(MailboxConfig).where(
            MailboxConfig.scope_type == MailboxScopeType.CENTRAL_ORDER_MAIL
        )
    ).first()
    return MailboxConfigPublic.model_validate(mailbox) if mailbox else None


@router.put("/central", response_model=MailboxConfigPublic)
def upsert_central_mailbox(
    *, session: SessionDep, body: MailboxConfigCreate
) -> MailboxConfigPublic:
    mailbox = session.exec(
        select(MailboxConfig).where(
            MailboxConfig.scope_type == MailboxScopeType.CENTRAL_ORDER_MAIL
        )
    ).first()
    if mailbox:
        mailbox.email = body.email
        mailbox.encrypted_app_password = encrypt_secret(body.app_password)
        mailbox.ingestion_retrieval_period = body.ingestion_retrieval_period
        mailbox.updated_at = _now_utc()
        mailbox.is_active = True
        session.add(mailbox)
        session.commit()
        session.refresh(mailbox)
        return MailboxConfigPublic.model_validate(mailbox)

    mailbox = MailboxConfig(
        scope_type=MailboxScopeType.CENTRAL_ORDER_MAIL,
        email=body.email,
        encrypted_app_password=encrypt_secret(body.app_password),
        ingestion_retrieval_period=body.ingestion_retrieval_period,
    )
    session.add(mailbox)
    session.commit()
    session.refresh(mailbox)
    return MailboxConfigPublic.model_validate(mailbox)


@router.patch("/central", response_model=MailboxConfigPublic)
def update_central_mailbox(
    *, session: SessionDep, body: MailboxConfigUpdate
) -> MailboxConfigPublic:
    mailbox = session.exec(
        select(MailboxConfig).where(
            MailboxConfig.scope_type == MailboxScopeType.CENTRAL_ORDER_MAIL
        )
    ).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="centralOrderMail config not found")

    data = body.model_dump(exclude_unset=True)
    if "app_password" in data:
        mailbox.encrypted_app_password = encrypt_secret(data.pop("app_password"))
    for key, value in data.items():
        setattr(mailbox, key, value)
    mailbox.updated_at = _now_utc()
    session.add(mailbox)
    session.commit()
    session.refresh(mailbox)
    return MailboxConfigPublic.model_validate(mailbox)


@router.get("/users", response_model=UserMailAccessesPublic)
def list_user_mail_accesses(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> UserMailAccessesPublic:
    count = session.exec(select(func.count()).select_from(UserMailAccess)).one()
    rows = session.exec(select(UserMailAccess).offset(skip).limit(limit)).all()
    return UserMailAccessesPublic(
        data=[UserMailAccessPublic.model_validate(row) for row in rows],
        count=count,
    )


@router.post("/users", response_model=UserMailAccessPublic)
def grant_user_mail_access(
    *, session: SessionDep, body: UserMailAccessCreate
) -> UserMailAccessPublic:
    user = session.get(User, body.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    mailbox = session.exec(
        select(MailboxConfig).where(
            MailboxConfig.scope_type == MailboxScopeType.USER_LINKED,
            MailboxConfig.email == user.email,
        )
    ).first()
    if mailbox:
        mailbox.encrypted_app_password = encrypt_secret(body.app_password)
        mailbox.updated_at = _now_utc()
        mailbox.is_active = True
    else:
        mailbox = MailboxConfig(
            scope_type=MailboxScopeType.USER_LINKED,
            email=user.email,
            encrypted_app_password=encrypt_secret(body.app_password),
        )
    session.add(mailbox)
    session.commit()
    session.refresh(mailbox)

    access = session.exec(
        select(UserMailAccess).where(UserMailAccess.user_id == body.user_id)
    ).first()
    if access:
        access.mailbox_config_id = mailbox.id
        access.access_type = body.access_type
        access.is_active = True
        access.updated_at = _now_utc()
    else:
        access = UserMailAccess(
            user_id=body.user_id,
            mailbox_config_id=mailbox.id,
            access_type=body.access_type,
            is_active=True,
        )
    session.add(access)
    session.commit()
    session.refresh(access)
    return UserMailAccessPublic.model_validate(access)


@router.patch("/users/{user_id}", response_model=UserMailAccessPublic)
def update_user_mail_access(
    *, session: SessionDep, user_id: uuid.UUID, body: UserMailAccessUpdate
) -> UserMailAccessPublic:
    access = session.exec(
        select(UserMailAccess).where(UserMailAccess.user_id == user_id)
    ).first()
    if not access:
        raise HTTPException(status_code=404, detail="User mail access not found")
    data = body.model_dump(exclude_unset=True)
    if "app_password" in data:
        mailbox = session.get(MailboxConfig, access.mailbox_config_id)
        if not mailbox:
            raise HTTPException(status_code=404, detail="Mailbox config not found")
        mailbox.encrypted_app_password = encrypt_secret(data.pop("app_password"))
        mailbox.updated_at = _now_utc()
        session.add(mailbox)
        session.commit()
    for key, value in data.items():
        setattr(access, key, value)
    access.updated_at = _now_utc()
    session.add(access)
    session.commit()
    session.refresh(access)
    return UserMailAccessPublic.model_validate(access)


@router.delete("/users/{user_id}", response_model=Message)
def revoke_user_mail_access(*, session: SessionDep, user_id: uuid.UUID) -> Any:
    access = session.exec(
        select(UserMailAccess).where(UserMailAccess.user_id == user_id)
    ).first()
    if not access:
        raise HTTPException(status_code=404, detail="User mail access not found")
    access.is_active = False
    access.updated_at = _now_utc()
    session.add(access)
    session.commit()
    return Message(message="User mail access revoked")
