import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select

from app.api.deps import SessionDep, get_current_active_superuser
from app.models import (
    Company,
    CompanyValidationAssignment,
    CompanyValidationAssignmentCreate,
    CompanyValidationAssignmentPublic,
    CompanyValidationAssignmentsPublic,
    CompanyValidationAssignmentUpdate,
    Message,
    ValidationRule,
    ValidationRuleCreate,
    ValidationRulePublic,
    ValidationRulesPublic,
    ValidationRuleUpdate,
)

router = APIRouter(
    prefix="/validations",
    tags=["validations"],
    dependencies=[Depends(get_current_active_superuser)],
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/rules", response_model=ValidationRulesPublic)
def list_validation_rules(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> ValidationRulesPublic:
    count = session.exec(select(func.count()).select_from(ValidationRule)).one()
    rows = session.exec(select(ValidationRule).offset(skip).limit(limit)).all()
    return ValidationRulesPublic(
        data=[ValidationRulePublic.model_validate(row) for row in rows],
        count=count,
    )


@router.post("/rules", response_model=ValidationRulePublic)
def create_validation_rule(
    *, session: SessionDep, body: ValidationRuleCreate
) -> ValidationRulePublic:
    row = ValidationRule.model_validate(body)
    session.add(row)
    session.commit()
    session.refresh(row)
    return ValidationRulePublic.model_validate(row)


@router.patch("/rules/{rule_id}", response_model=ValidationRulePublic)
def update_validation_rule(
    *, session: SessionDep, rule_id: uuid.UUID, body: ValidationRuleUpdate
) -> ValidationRulePublic:
    row = session.get(ValidationRule, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Validation rule not found")
    row.sqlmodel_update(body.model_dump(exclude_unset=True))
    row.updated_at = _now_utc()
    session.add(row)
    session.commit()
    session.refresh(row)
    return ValidationRulePublic.model_validate(row)


@router.delete("/rules/{rule_id}", response_model=Message)
def delete_validation_rule(*, session: SessionDep, rule_id: uuid.UUID) -> Any:
    row = session.get(ValidationRule, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Validation rule not found")
    session.delete(row)
    session.commit()
    return Message(message="Validation rule deleted")


@router.get("/assignments", response_model=CompanyValidationAssignmentsPublic)
def list_assignments(
    session: SessionDep, company_id: uuid.UUID | None = None
) -> CompanyValidationAssignmentsPublic:
    base_query = select(CompanyValidationAssignment)
    count_query = select(func.count()).select_from(CompanyValidationAssignment)
    if company_id:
        base_query = base_query.where(
            CompanyValidationAssignment.company_id == company_id
        )
        count_query = count_query.where(
            CompanyValidationAssignment.company_id == company_id
        )
    rows = session.exec(base_query).all()
    count = session.exec(count_query).one()
    return CompanyValidationAssignmentsPublic(
        data=[CompanyValidationAssignmentPublic.model_validate(row) for row in rows],
        count=count,
    )


@router.post("/assignments", response_model=CompanyValidationAssignmentPublic)
def create_assignment(
    *, session: SessionDep, body: CompanyValidationAssignmentCreate
) -> CompanyValidationAssignmentPublic:
    if not session.get(Company, body.company_id):
        raise HTTPException(status_code=404, detail="Company not found")
    if not session.get(ValidationRule, body.validation_rule_id):
        raise HTTPException(status_code=404, detail="Validation rule not found")
    row = CompanyValidationAssignment.model_validate(body)
    session.add(row)
    session.commit()
    session.refresh(row)
    return CompanyValidationAssignmentPublic.model_validate(row)


@router.patch("/assignments/{assignment_id}", response_model=CompanyValidationAssignmentPublic)
def update_assignment(
    *, session: SessionDep, assignment_id: uuid.UUID, body: CompanyValidationAssignmentUpdate
) -> CompanyValidationAssignmentPublic:
    row = session.get(CompanyValidationAssignment, assignment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Validation assignment not found")
    row.sqlmodel_update(body.model_dump(exclude_unset=True))
    row.updated_at = _now_utc()
    session.add(row)
    session.commit()
    session.refresh(row)
    return CompanyValidationAssignmentPublic.model_validate(row)


@router.delete("/assignments/{assignment_id}", response_model=Message)
def delete_assignment(*, session: SessionDep, assignment_id: uuid.UUID) -> Any:
    row = session.get(CompanyValidationAssignment, assignment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Validation assignment not found")
    session.delete(row)
    session.commit()
    return Message(message="Validation assignment deleted")
