import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select

from app.api.deps import SessionDep, get_current_active_superuser
from app.models import (
    CompaniesPublic,
    Company,
    CompanyCreate,
    CompanyEmailDomain,
    CompanyEmailDomainCreate,
    CompanyEmailDomainPublic,
    CompanyEmailDomainsPublic,
    CompanyEmailDomainUpdate,
    CompanyPublic,
    CompanyUpdate,
    Message,
)

router = APIRouter(
    prefix="/companies",
    tags=["companies"],
    dependencies=[Depends(get_current_active_superuser)],
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _clean_aka_names(values: list[str] | None) -> list[str]:
    if not values:
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        lower = normalized.lower()
        if lower in seen:
            continue
        seen.add(lower)
        cleaned.append(normalized)
    return cleaned


@router.get("/", response_model=CompaniesPublic)
def list_companies(session: SessionDep, skip: int = 0, limit: int = 100) -> CompaniesPublic:
    count = session.exec(select(func.count()).select_from(Company)).one()
    rows = session.exec(select(Company).offset(skip).limit(limit)).all()
    return CompaniesPublic(
        data=[CompanyPublic.model_validate(row) for row in rows],
        count=count,
    )


@router.post("/", response_model=CompanyPublic)
def create_company(*, session: SessionDep, body: CompanyCreate) -> CompanyPublic:
    payload = body.model_copy(update={"aka_names": _clean_aka_names(body.aka_names)})
    company = Company.model_validate(payload)
    session.add(company)
    session.commit()
    session.refresh(company)
    return CompanyPublic.model_validate(company)


@router.patch("/{company_id}", response_model=CompanyPublic)
def update_company(
    *, session: SessionDep, company_id: uuid.UUID, body: CompanyUpdate
) -> CompanyPublic:
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    update_data = body.model_dump(exclude_unset=True)
    if "aka_names" in update_data:
        update_data["aka_names"] = _clean_aka_names(update_data["aka_names"])
    company.sqlmodel_update(update_data)
    company.updated_at = _now_utc()
    session.add(company)
    session.commit()
    session.refresh(company)
    return CompanyPublic.model_validate(company)


@router.delete("/{company_id}", response_model=Message)
def delete_company(*, session: SessionDep, company_id: uuid.UUID) -> Any:
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    session.delete(company)
    session.commit()
    return Message(message="Company deleted")


@router.get("/{company_id}/domains", response_model=CompanyEmailDomainsPublic)
def list_company_domains(
    *, session: SessionDep, company_id: uuid.UUID
) -> CompanyEmailDomainsPublic:
    count = session.exec(
        select(func.count()).select_from(CompanyEmailDomain).where(
            CompanyEmailDomain.company_id == company_id
        )
    ).one()
    rows = session.exec(
        select(CompanyEmailDomain).where(CompanyEmailDomain.company_id == company_id)
    ).all()
    return CompanyEmailDomainsPublic(
        data=[CompanyEmailDomainPublic.model_validate(row) for row in rows],
        count=count,
    )


@router.post("/{company_id}/domains", response_model=CompanyEmailDomainPublic)
def create_company_domain(
    *, session: SessionDep, company_id: uuid.UUID, body: CompanyEmailDomainCreate
) -> CompanyEmailDomainPublic:
    if body.company_id != company_id:
        raise HTTPException(status_code=400, detail="company_id mismatch")
    if not session.get(Company, company_id):
        raise HTTPException(status_code=404, detail="Company not found")
    payload = body.model_copy(
        update={"domain_pattern": body.domain_pattern.strip().lower()}
    )
    row = CompanyEmailDomain.model_validate(payload)
    session.add(row)
    session.commit()
    session.refresh(row)
    return CompanyEmailDomainPublic.model_validate(row)


@router.patch("/domains/{domain_id}", response_model=CompanyEmailDomainPublic)
def update_company_domain(
    *, session: SessionDep, domain_id: uuid.UUID, body: CompanyEmailDomainUpdate
) -> CompanyEmailDomainPublic:
    row = session.get(CompanyEmailDomain, domain_id)
    if not row:
        raise HTTPException(status_code=404, detail="Domain pattern not found")
    data = body.model_dump(exclude_unset=True)
    if "domain_pattern" in data and data["domain_pattern"]:
        data["domain_pattern"] = data["domain_pattern"].strip().lower()
    row.sqlmodel_update(data)
    row.updated_at = _now_utc()
    session.add(row)
    session.commit()
    session.refresh(row)
    return CompanyEmailDomainPublic.model_validate(row)


@router.delete("/domains/{domain_id}", response_model=Message)
def delete_company_domain(*, session: SessionDep, domain_id: uuid.UUID) -> Any:
    row = session.get(CompanyEmailDomain, domain_id)
    if not row:
        raise HTTPException(status_code=404, detail="Domain pattern not found")
    session.delete(row)
    session.commit()
    return Message(message="Domain pattern deleted")
