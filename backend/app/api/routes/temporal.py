from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep, get_current_active_superuser
from app.core.config import settings
from app.models import MailboxConfig, MailboxScopeType, Message
from app.services.o2c_scheduler import ensure_o2c_scheduler_started, signal_o2c_poll_now
from app.services.retrieval_period import parse_ingestion_period_minutes
from app.temporal.client import connect_temporal_client

router = APIRouter(
    prefix="/temporal",
    tags=["temporal"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.post("/o2c/scheduler/start", response_model=Message)
async def start_o2c_scheduler(session: SessionDep) -> Message:
    mailbox = session.exec(
        select(MailboxConfig).where(
            MailboxConfig.scope_type == MailboxScopeType.CENTRAL_ORDER_MAIL,
            MailboxConfig.is_active == True,  # noqa: E712
        )
    ).first()
    if not mailbox:
        raise HTTPException(status_code=400, detail="Configure centralOrderMail first")
    minutes = parse_ingestion_period_minutes(
        mailbox.ingestion_retrieval_period,
        default=settings.O2C_DEFAULT_INGESTION_PERIOD_MINUTES,
    )
    client = await connect_temporal_client()
    await ensure_o2c_scheduler_started(client, period_minutes=minutes)
    return Message(message="O2C scheduler start requested")


@router.post("/o2c/scheduler/poll-now", response_model=Message)
async def request_o2c_poll_now(session: SessionDep) -> Message:
    """Signal the ingestion scheduler to skip the sleep countdown and poll central unread soon.

    Requires the scheduler workflow to exist (call ``/o2c/scheduler/start`` once if needed).
    """
    mailbox = session.exec(
        select(MailboxConfig).where(
            MailboxConfig.scope_type == MailboxScopeType.CENTRAL_ORDER_MAIL,
            MailboxConfig.is_active == True,  # noqa: E712
        )
    ).first()
    if not mailbox:
        raise HTTPException(status_code=400, detail="Configure centralOrderMail first")
    minutes = parse_ingestion_period_minutes(
        mailbox.ingestion_retrieval_period,
        default=settings.O2C_DEFAULT_INGESTION_PERIOD_MINUTES,
    )
    client = await connect_temporal_client()
    await ensure_o2c_scheduler_started(client, period_minutes=minutes)
    await signal_o2c_poll_now()
    return Message(message="O2C central poll requested")
