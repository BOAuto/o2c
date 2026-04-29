import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, func, select

from app.api.deps import SessionDep, get_current_active_superuser
from app.core.config import settings
from app.core.crypto import encrypt_secret
from app.models import (
    MailboxConfig,
    MailboxConfigCreate,
    MailboxConfigPublic,
    MailboxConfigUpdate,
    MailboxScopeType,
    Message,
    User,
    UserMailAccessCreate,
    UserMailAccessesPublic,
    UserMailAccessPublic,
    UserMailAccessUpdate,
    user_mail_access_public_from_mailbox,
)
from app.services.o2c_scheduler import ensure_and_sync_o2c_scheduler
from app.services.retrieval_period import parse_ingestion_period_minutes

router = APIRouter(
    prefix="/mail-access",
    tags=["mail-access"],
    dependencies=[Depends(get_current_active_superuser)],
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _user_linked_mail_filters():
    return (
        MailboxConfig.scope_type == MailboxScopeType.USER_LINKED,
        col(MailboxConfig.user_id).isnot(None),
        col(MailboxConfig.mail_access_type).isnot(None),
    )


@router.get("/central", response_model=MailboxConfigPublic | None)
def get_central_mailbox(session: SessionDep) -> MailboxConfigPublic | None:
    mailbox = session.exec(
        select(MailboxConfig).where(
            MailboxConfig.scope_type == MailboxScopeType.CENTRAL_ORDER_MAIL
        )
    ).first()
    return MailboxConfigPublic.model_validate(mailbox) if mailbox else None


@router.put("/central", response_model=MailboxConfigPublic)
async def upsert_central_mailbox(
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
        minutes = parse_ingestion_period_minutes(
            mailbox.ingestion_retrieval_period,
            default=settings.O2C_DEFAULT_INGESTION_PERIOD_MINUTES,
        )
        await ensure_and_sync_o2c_scheduler(minutes)
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
    minutes = parse_ingestion_period_minutes(
        mailbox.ingestion_retrieval_period,
        default=settings.O2C_DEFAULT_INGESTION_PERIOD_MINUTES,
    )
    await ensure_and_sync_o2c_scheduler(minutes)
    return MailboxConfigPublic.model_validate(mailbox)


@router.patch("/central", response_model=MailboxConfigPublic)
async def update_central_mailbox(
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
    minutes = parse_ingestion_period_minutes(
        mailbox.ingestion_retrieval_period,
        default=settings.O2C_DEFAULT_INGESTION_PERIOD_MINUTES,
    )
    await ensure_and_sync_o2c_scheduler(minutes)
    return MailboxConfigPublic.model_validate(mailbox)


@router.get("/users", response_model=UserMailAccessesPublic)
def list_user_mail_accesses(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> UserMailAccessesPublic:
    uf = _user_linked_mail_filters()
    count = session.exec(
        select(func.count()).select_from(MailboxConfig).where(*uf)
    ).one()
    rows = session.exec(
        select(MailboxConfig).where(*uf).offset(skip).limit(limit)
    ).all()
    return UserMailAccessesPublic(
        data=[user_mail_access_public_from_mailbox(row) for row in rows],
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
    prev = session.exec(
        select(MailboxConfig).where(
            MailboxConfig.user_id == body.user_id,
            MailboxConfig.scope_type == MailboxScopeType.USER_LINKED,
        )
    ).first()
    if mailbox:
        if prev and prev.id != mailbox.id:
            prev.user_id = None
            prev.mail_access_type = None
            session.add(prev)
        mailbox.encrypted_app_password = encrypt_secret(body.app_password)
        mailbox.user_id = body.user_id
        mailbox.mail_access_type = body.access_type
        mailbox.updated_at = _now_utc()
        mailbox.is_active = True
    else:
        if prev:
            prev.user_id = None
            prev.mail_access_type = None
            session.add(prev)
        mailbox = MailboxConfig(
            scope_type=MailboxScopeType.USER_LINKED,
            email=user.email,
            user_id=body.user_id,
            mail_access_type=body.access_type,
            encrypted_app_password=encrypt_secret(body.app_password),
        )
    session.add(mailbox)
    session.commit()
    session.refresh(mailbox)
    return user_mail_access_public_from_mailbox(mailbox)


@router.patch("/users/{user_id}", response_model=UserMailAccessPublic)
def update_user_mail_access(
    *, session: SessionDep, user_id: uuid.UUID, body: UserMailAccessUpdate
) -> UserMailAccessPublic:
    mailbox = session.exec(
        select(MailboxConfig).where(
            MailboxConfig.user_id == user_id,
            MailboxConfig.scope_type == MailboxScopeType.USER_LINKED,
        )
    ).first()
    if not mailbox or mailbox.mail_access_type is None:
        raise HTTPException(status_code=404, detail="User mail access not found")
    data = body.model_dump(exclude_unset=True)
    if "app_password" in data:
        mailbox.encrypted_app_password = encrypt_secret(data.pop("app_password"))
        mailbox.updated_at = _now_utc()
    for key, value in data.items():
        if key == "access_type":
            mailbox.mail_access_type = value
        else:
            setattr(mailbox, key, value)
    mailbox.updated_at = _now_utc()
    session.add(mailbox)
    session.commit()
    session.refresh(mailbox)
    return user_mail_access_public_from_mailbox(mailbox)


@router.delete("/users/{user_id}", response_model=Message)
def revoke_user_mail_access(*, session: SessionDep, user_id: uuid.UUID) -> Any:
    mailbox = session.exec(
        select(MailboxConfig).where(
            MailboxConfig.user_id == user_id,
            MailboxConfig.scope_type == MailboxScopeType.USER_LINKED,
        )
    ).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="User mail access not found")
    mailbox.is_active = False
    mailbox.updated_at = _now_utc()
    session.add(mailbox)
    session.commit()
    return Message(message="User mail access revoked")
