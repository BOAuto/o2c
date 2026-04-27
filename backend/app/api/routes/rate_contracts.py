import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select

from app.api.deps import SessionDep, get_current_active_superuser
from app.models import (
    ClientRateContract,
    ClientRateContractCreate,
    ClientRateContractPublic,
    ClientRateContractsPublic,
    ClientRateContractUpdate,
    Company,
    Message,
)

router = APIRouter(
    prefix="/rate-contracts",
    tags=["rate-contracts"],
    dependencies=[Depends(get_current_active_superuser)],
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/", response_model=ClientRateContractsPublic)
def list_rate_contracts(
    session: SessionDep, company_id: uuid.UUID | None = None, skip: int = 0, limit: int = 100
) -> ClientRateContractsPublic:
    base_query = select(ClientRateContract)
    count_query = select(func.count()).select_from(ClientRateContract)
    if company_id:
        base_query = base_query.where(ClientRateContract.company_id == company_id)
        count_query = count_query.where(ClientRateContract.company_id == company_id)
    rows = session.exec(base_query.offset(skip).limit(limit)).all()
    count = session.exec(count_query).one()
    return ClientRateContractsPublic(
        data=[ClientRateContractPublic.model_validate(row) for row in rows],
        count=count,
    )


@router.post("/", response_model=ClientRateContractPublic)
def create_rate_contract(
    *, session: SessionDep, body: ClientRateContractCreate
) -> ClientRateContractPublic:
    if not session.get(Company, body.company_id):
        raise HTTPException(status_code=404, detail="Company not found")
    row = ClientRateContract.model_validate(body)
    session.add(row)
    session.commit()
    session.refresh(row)
    return ClientRateContractPublic.model_validate(row)


@router.patch("/{contract_id}", response_model=ClientRateContractPublic)
def update_rate_contract(
    *, session: SessionDep, contract_id: uuid.UUID, body: ClientRateContractUpdate
) -> ClientRateContractPublic:
    row = session.get(ClientRateContract, contract_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rate contract not found")
    row.sqlmodel_update(body.model_dump(exclude_unset=True))
    row.updated_at = _now_utc()
    session.add(row)
    session.commit()
    session.refresh(row)
    return ClientRateContractPublic.model_validate(row)


@router.delete("/{contract_id}", response_model=Message)
def delete_rate_contract(*, session: SessionDep, contract_id: uuid.UUID) -> Any:
    row = session.get(ClientRateContract, contract_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rate contract not found")
    session.delete(row)
    session.commit()
    return Message(message="Rate contract deleted")
