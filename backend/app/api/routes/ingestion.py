import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import desc
from sqlmodel import func, select

from app.api.deps import SessionDep, get_current_active_superuser
from app.models import (
    IngestionStorageSummaryPublic,
    InternalUnmappedSender,
    InternalUnmappedSenderPublic,
    InternalUnmappedSendersPublic,
    OrderIngestionArtifact,
    OrderIngestionArtifactKind,
    OrderIngestionArtifactPublic,
    OrderIngestionRun,
    OrderIngestionRunDetailPublic,
    OrderIngestionRunPublic,
    OrderMailboxItemPublic,
    OrderMailboxItemsPublic,
    OrderUserMessageId,
    RejectedCentralSender,
    RejectedCentralSenderPublic,
    RejectedCentralSendersPublic,
)
from app.services.ingestion_mail import normalize_message_id
from app.storage.order_ingestion import read_order_ingestion_object_bytes

router = APIRouter(
    prefix="/ingestion",
    tags=["ingestion"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.get("/rejected-central", response_model=RejectedCentralSendersPublic)
def list_rejected_central(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> RejectedCentralSendersPublic:
    count = session.exec(select(func.count()).select_from(RejectedCentralSender)).one()
    rows = session.exec(
        select(RejectedCentralSender)
        .order_by(desc(RejectedCentralSender.created_at))
        .offset(skip)
        .limit(limit)
    ).all()
    return RejectedCentralSendersPublic(
        data=[RejectedCentralSenderPublic.model_validate(r) for r in rows],
        count=count,
    )


@router.get("/rejected-central/{event_id}", response_model=RejectedCentralSenderPublic)
def get_rejected_central(
    session: SessionDep, event_id: uuid.UUID
) -> RejectedCentralSenderPublic:
    row = session.get(RejectedCentralSender, event_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rejected event not found")
    return RejectedCentralSenderPublic.model_validate(row)


@router.get("/internal-unmapped", response_model=InternalUnmappedSendersPublic)
def list_internal_unmapped(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> InternalUnmappedSendersPublic:
    count = session.exec(select(func.count()).select_from(InternalUnmappedSender)).one()
    rows = session.exec(
        select(InternalUnmappedSender)
        .order_by(desc(InternalUnmappedSender.created_at))
        .offset(skip)
        .limit(limit)
    ).all()
    return InternalUnmappedSendersPublic(
        data=[InternalUnmappedSenderPublic.model_validate(r) for r in rows],
        count=count,
    )


@router.get("/internal-unmapped/{event_id}", response_model=InternalUnmappedSenderPublic)
def get_internal_unmapped(
    session: SessionDep, event_id: uuid.UUID
) -> InternalUnmappedSenderPublic:
    row = session.get(InternalUnmappedSender, event_id)
    if not row:
        raise HTTPException(status_code=404, detail="Internal unmapped event not found")
    return InternalUnmappedSenderPublic.model_validate(row)


@router.get("/runs/{run_id}", response_model=OrderIngestionRunDetailPublic)
def get_ingestion_run(session: SessionDep, run_id: uuid.UUID) -> OrderIngestionRunDetailPublic:
    run = session.get(OrderIngestionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Ingestion run not found")
    ous = session.exec(
        select(OrderUserMessageId).where(OrderUserMessageId.order_ingestion_id == run_id)
    ).all()
    chosen: OrderUserMessageId | None = None
    if run.order_user_message_id_norm:
        chosen = next(
            (
                row
                for row in ous
                if row.message_id_normalized == run.order_user_message_id_norm
            ),
            None,
        )
    if chosen is None and ous:
        chosen = ous[0]
    arts = session.exec(
        select(OrderIngestionArtifact).where(OrderIngestionArtifact.order_ingestion_id == run_id)
    ).all()
    run_public = OrderIngestionRunPublic.model_validate(run)
    run_public.order_user_message_id_raw = chosen.message_id_raw if chosen else None
    run_public.order_user_message_id_normalized = (
        chosen.message_id_normalized if chosen else None
    )
    run_public.order_user_email = chosen.order_user_email if chosen else None
    return OrderIngestionRunDetailPublic(
        run=run_public,
        artifacts=[OrderIngestionArtifactPublic.model_validate(a) for a in arts],
    )


@router.get("/mailbox", response_model=OrderMailboxItemsPublic)
def list_mailbox_runs(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> OrderMailboxItemsPublic:
    count = session.exec(select(func.count()).select_from(OrderIngestionRun)).one()
    runs = session.exec(
        select(OrderIngestionRun)
        .order_by(desc(OrderIngestionRun.created_at))
        .offset(skip)
        .limit(limit)
    ).all()
    run_ids = [r.id for r in runs]
    ous_by_run: dict[uuid.UUID, list[OrderUserMessageId]] = {}
    if run_ids:
        ous = session.exec(
            select(OrderUserMessageId).where(
                OrderUserMessageId.order_ingestion_id.in_(run_ids)
            )
        ).all()
        for row in ous:
            ous_by_run.setdefault(row.order_ingestion_id, []).append(row)
    html_by_run: dict[uuid.UUID, OrderIngestionArtifact] = {}
    if run_ids:
        html_arts = session.exec(
            select(OrderIngestionArtifact).where(
                OrderIngestionArtifact.order_ingestion_id.in_(run_ids),  # type: ignore[attr-defined]
                OrderIngestionArtifact.artifact_kind == OrderIngestionArtifactKind.HTML.value,
            )
        ).all()
        for art in html_arts:
            html_by_run.setdefault(art.order_ingestion_id, art)
    data: list[OrderMailboxItemPublic] = []
    for run in runs:
        art = html_by_run.get(run.id)
        candidates = ous_by_run.get(run.id, [])
        chosen: OrderUserMessageId | None = None
        if run.order_user_message_id_norm:
            chosen = next(
                (
                    row
                    for row in candidates
                    if row.message_id_normalized == run.order_user_message_id_norm
                ),
                None,
            )
        if chosen is None and candidates:
            chosen = candidates[0]
        run_public = OrderIngestionRunPublic.model_validate(run)
        run_public.order_user_message_id_raw = chosen.message_id_raw if chosen else None
        run_public.order_user_message_id_normalized = (
            chosen.message_id_normalized if chosen else None
        )
        run_public.order_user_email = chosen.order_user_email if chosen else None
        data.append(
            OrderMailboxItemPublic(
                run=run_public,
                html_artifact_id=art.id if art else None,
                html_file_name=art.file_name if art else None,
            )
        )
    return OrderMailboxItemsPublic(data=data, count=count)


@router.get("/runs/{run_id}/artifacts/{artifact_id}")
def get_run_artifact_file(
    session: SessionDep,
    run_id: uuid.UUID,
    artifact_id: uuid.UUID,
    disposition: Literal["inline", "attachment"] = Query("inline"),
) -> Response:
    run = session.get(OrderIngestionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Ingestion run not found")
    art = session.get(OrderIngestionArtifact, artifact_id)
    if not art or art.order_ingestion_id != run_id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    content = read_order_ingestion_object_bytes(art.object_key)
    media = art.mime_type or "application/octet-stream"
    cd_type = "inline" if disposition == "inline" else "attachment"
    cd = f'{cd_type}; filename="{art.file_name}"'
    return Response(content=content, media_type=media, headers={"Content-Disposition": cd})


@router.get("/runs/{run_id}/html")
def get_run_anchor_html(session: SessionDep, run_id: uuid.UUID) -> Response:
    run = session.get(OrderIngestionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Ingestion run not found")
    art = session.exec(
        select(OrderIngestionArtifact).where(
            OrderIngestionArtifact.order_ingestion_id == run_id,
            OrderIngestionArtifact.artifact_kind == OrderIngestionArtifactKind.HTML.value,
        )
    ).first()
    if not art:
        raise HTTPException(status_code=404, detail="Anchor HTML artifact not found")
    content = read_order_ingestion_object_bytes(art.object_key)
    return Response(content=content, media_type=art.mime_type or "text/html")


@router.get("/storage-summary", response_model=IngestionStorageSummaryPublic)
def get_ingestion_storage_summary(session: SessionDep) -> IngestionStorageSummaryPublic:
    runs = session.exec(select(func.count()).select_from(OrderIngestionRun)).one()
    artifacts = session.exec(select(func.count()).select_from(OrderIngestionArtifact)).one()
    rejected = session.exec(select(func.count()).select_from(RejectedCentralSender)).one()
    unmapped = session.exec(select(func.count()).select_from(InternalUnmappedSender)).one()
    return IngestionStorageSummaryPublic(
        runs=runs,
        artifacts=artifacts,
        rejected_central=rejected,
        internal_unmapped=unmapped,
    )


@router.get("/by-message-id/{message_id}", response_model=dict[str, Any])
def get_ingestion_by_message_id(
    session: SessionDep, message_id: str
) -> dict[str, Any]:
    mid = normalize_message_id(message_id)
    if not mid:
        raise HTTPException(status_code=400, detail="Invalid message_id")

    runs = session.exec(
        select(OrderIngestionRun)
        .where(OrderIngestionRun.source_message_id_norm == mid)
        .order_by(desc(OrderIngestionRun.created_at))
    ).all()
    run_details: list[dict[str, Any]] = []
    if runs:
        run_ids = [r.id for r in runs]
        ous = session.exec(
            select(OrderUserMessageId).where(
                OrderUserMessageId.order_ingestion_id.in_(run_ids)
            )
        ).all()
        ous_by_run: dict[uuid.UUID, list[OrderUserMessageId]] = {}
        for row in ous:
            ous_by_run.setdefault(row.order_ingestion_id, []).append(row)
        all_artifacts = session.exec(
            select(OrderIngestionArtifact).where(  # type: ignore[attr-defined]
                OrderIngestionArtifact.order_ingestion_id.in_(run_ids)
            )
        ).all()
        arts_by_run: dict[uuid.UUID, list[OrderIngestionArtifact]] = {}
        for a in all_artifacts:
            arts_by_run.setdefault(a.order_ingestion_id, []).append(a)
        for run in runs:
            candidates = ous_by_run.get(run.id, [])
            chosen: OrderUserMessageId | None = None
            if run.order_user_message_id_norm:
                chosen = next(
                    (
                        row
                        for row in candidates
                        if row.message_id_normalized == run.order_user_message_id_norm
                    ),
                    None,
                )
            if chosen is None and candidates:
                chosen = candidates[0]
            run_details.append(
                {
                    "processed order": {
                        "source_message_id_norm": run.source_message_id_norm,
                        "order_user_email": chosen.order_user_email if chosen else None,
                        "order_user_message_id_raw": chosen.message_id_raw if chosen else None,
                        "order_user_message_id_normalized": (
                            chosen.message_id_normalized if chosen else None
                        ),
                        # Back-compat key (existing frontend / callers may still reference it).
                        "order_user_message_id_norm": (
                            chosen.message_id_normalized
                            if chosen
                            else run.order_user_message_id_norm
                        ),
                        "source_from": run.source_from,
                        "source_subject": run.source_subject,
                        "source_received_at": run.source_received_at,
                        "no_attachment_order": run.no_attachment_order,
                        "status": run.status,
                        "external_correspondent_from": run.external_correspondent_from,
                        "external_correspondent_cc": run.external_correspondent_cc,
                        "external_correspondent_domain": run.external_correspondent_domain,
                        "external_correspondent_at": run.external_correspondent_at,
                        "created_at": run.created_at,
                        "updated_at": run.updated_at,
                    },
                    "artifacts": [
                        {
                            "artifact_kind": a.artifact_kind,
                            "object_key": a.object_key,
                            "file_name": a.file_name,
                            "mime_type": a.mime_type,
                            "size_bytes": a.size_bytes,
                        }
                        for a in arts_by_run.get(run.id, [])
                    ],
                }
            )

    rejected = session.exec(
        select(RejectedCentralSender)
        .where(RejectedCentralSender.message_id_norm == mid)
        .order_by(desc(RejectedCentralSender.created_at))
    ).all()
    internal_unmapped = session.exec(
        select(InternalUnmappedSender)
        .where(InternalUnmappedSender.message_id_norm == mid)
        .order_by(desc(InternalUnmappedSender.created_at))
    ).all()

    return {
        "message_id_norm": mid,
        "Order Ingestion": run_details,
        "rejected_central": [
            {
                "from_address": r.from_address,
                "subject": r.subject,
                "message_id_norm": r.message_id_norm,
                "imap_uid": r.imap_uid,
                "rejection_reason": r.rejection_reason,
                "created_at": r.created_at,
            }
            for r in rejected
        ],
        "internal_unmapped": [
            {
                "from_address": r.from_address,
                "subject": r.subject,
                "message_id_norm": r.message_id_norm,
                "imap_uid": r.imap_uid,
                "created_at": r.created_at,
            }
            for r in internal_unmapped
        ],
    }
