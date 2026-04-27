import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select

from app.api.deps import SessionDep, get_current_active_superuser
from app.models import (
    Branch,
    BranchCreate,
    BranchesPublic,
    BranchGstState,
    BranchGstStateCreate,
    BranchGstStatePublic,
    BranchGstStatesPublic,
    BranchPublic,
    BranchUpdate,
    GstStateCode,
    GstStateCodePublic,
    GstStateCodesPublic,
    Message,
)

router = APIRouter(
    prefix="/branches",
    tags=["branches"],
    dependencies=[Depends(get_current_active_superuser)],
)

GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _validate_gstin(gstin: str) -> str:
    normalized = gstin.strip().upper()
    if not GSTIN_REGEX.match(normalized):
        raise HTTPException(status_code=422, detail="Invalid GSTIN format")
    return normalized


@router.get("/", response_model=BranchesPublic)
def list_branches(session: SessionDep, skip: int = 0, limit: int = 100) -> BranchesPublic:
    count = session.exec(select(func.count()).select_from(Branch)).one()
    rows = session.exec(select(Branch).offset(skip).limit(limit)).all()
    return BranchesPublic(
        data=[BranchPublic.model_validate(row) for row in rows],
        count=count,
    )


@router.post("/", response_model=BranchPublic)
def create_branch(*, session: SessionDep, body: BranchCreate) -> BranchPublic:
    row = Branch.model_validate(
        body.model_copy(update={"branch_gstin": _validate_gstin(body.branch_gstin)})
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return BranchPublic.model_validate(row)


@router.patch("/{branch_id}", response_model=BranchPublic)
def update_branch(
    *, session: SessionDep, branch_id: uuid.UUID, body: BranchUpdate
) -> BranchPublic:
    row = session.get(Branch, branch_id)
    if not row:
        raise HTTPException(status_code=404, detail="Branch not found")
    data = body.model_dump(exclude_unset=True)
    if "branch_gstin" in data and data["branch_gstin"]:
        data["branch_gstin"] = _validate_gstin(data["branch_gstin"])
    row.sqlmodel_update(data)
    row.updated_at = _now_utc()
    session.add(row)
    session.commit()
    session.refresh(row)
    return BranchPublic.model_validate(row)


@router.delete("/{branch_id}", response_model=Message)
def delete_branch(*, session: SessionDep, branch_id: uuid.UUID) -> Any:
    row = session.get(Branch, branch_id)
    if not row:
        raise HTTPException(status_code=404, detail="Branch not found")
    session.delete(row)
    session.commit()
    return Message(message="Branch deleted")


@router.get("/gst-states", response_model=GstStateCodesPublic)
def list_gst_states(session: SessionDep) -> GstStateCodesPublic:
    rows = session.exec(select(GstStateCode).order_by(GstStateCode.code)).all()
    return GstStateCodesPublic(
        data=[GstStateCodePublic.model_validate(row) for row in rows],
        count=len(rows),
    )


@router.get("/{branch_id}/gst-states", response_model=BranchGstStatesPublic)
def list_branch_states(*, session: SessionDep, branch_id: uuid.UUID) -> BranchGstStatesPublic:
    rows = session.exec(
        select(BranchGstState).where(BranchGstState.branch_id == branch_id)
    ).all()
    return BranchGstStatesPublic(
        data=[BranchGstStatePublic.model_validate(row) for row in rows],
        count=len(rows),
    )


@router.post("/{branch_id}/gst-states", response_model=BranchGstStatePublic)
def attach_branch_state(
    *, session: SessionDep, branch_id: uuid.UUID, body: BranchGstStateCreate
) -> BranchGstStatePublic:
    if body.branch_id != branch_id:
        raise HTTPException(status_code=400, detail="branch_id mismatch")
    if not session.get(Branch, branch_id):
        raise HTTPException(status_code=404, detail="Branch not found")
    if not session.get(GstStateCode, body.gst_state_code_id):
        raise HTTPException(status_code=404, detail="GST state not found")
    row = BranchGstState.model_validate(body)
    session.add(row)
    session.commit()
    session.refresh(row)
    return BranchGstStatePublic.model_validate(row)


@router.delete("/{branch_id}/gst-states/{mapping_id}", response_model=Message)
def detach_branch_state(
    *, session: SessionDep, branch_id: uuid.UUID, mapping_id: uuid.UUID
) -> Any:
    row = session.get(BranchGstState, mapping_id)
    if not row or row.branch_id != branch_id:
        raise HTTPException(status_code=404, detail="Branch state mapping not found")
    session.delete(row)
    session.commit()
    return Message(message="Branch state detached")
