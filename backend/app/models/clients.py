import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, Numeric, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class CompanyBase(SQLModel):
    name: str = Field(unique=True, index=True, max_length=255)
    payment_term: int | None = Field(default=None, ge=0)
    aka_names: list[str] = Field(default_factory=list, sa_type=JSON)  # type: ignore[arg-type]
    is_active: bool = True


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    payment_term: int | None = Field(default=None, ge=0)
    aka_names: list[str] | None = None
    is_active: bool | None = None


class Company(CompanyBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class CompanyPublic(CompanyBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CompanyEmailDomainBase(SQLModel):
    company_id: uuid.UUID = Field(index=True)
    domain_pattern: str = Field(max_length=255)
    is_active: bool = True


class CompanyEmailDomainCreate(CompanyEmailDomainBase):
    pass


class CompanyEmailDomainUpdate(SQLModel):
    domain_pattern: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class CompanyEmailDomain(CompanyEmailDomainBase, table=True):
    __table_args__ = (
        UniqueConstraint("company_id", "domain_pattern", name="uq_company_domain_pattern"),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class CompanyEmailDomainPublic(CompanyEmailDomainBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ClientRateContractBase(SQLModel):
    company_id: uuid.UUID = Field(index=True)
    product_name: str = Field(max_length=255)
    sku: str = Field(max_length=128)
    agreed_rate: Decimal = Field(sa_type=Numeric(12, 2))
    gst_rate: Decimal = Field(sa_type=Numeric(5, 2))
    is_active: bool = True


class ClientRateContractCreate(ClientRateContractBase):
    pass


class ClientRateContractUpdate(SQLModel):
    product_name: str | None = Field(default=None, max_length=255)
    sku: str | None = Field(default=None, max_length=128)
    agreed_rate: Decimal | None = None
    gst_rate: Decimal | None = None
    is_active: bool | None = None


class ClientRateContract(ClientRateContractBase, table=True):
    __table_args__ = (
        UniqueConstraint("company_id", "sku", name="uq_client_contract_company_sku"),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ClientRateContractPublic(ClientRateContractBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ValidationRuleBase(SQLModel):
    key: str = Field(unique=True, index=True, max_length=128)
    label: str = Field(max_length=255)
    definition_json: str = Field(default="{}", max_length=5000)
    is_active: bool = True


class ValidationRuleCreate(ValidationRuleBase):
    pass


class ValidationRuleUpdate(SQLModel):
    label: str | None = Field(default=None, max_length=255)
    definition_json: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None


class ValidationRule(ValidationRuleBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ValidationRulePublic(ValidationRuleBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CompanyValidationAssignmentBase(SQLModel):
    company_id: uuid.UUID = Field(index=True)
    validation_rule_id: uuid.UUID = Field(index=True)
    is_enabled: bool = True


class CompanyValidationAssignmentCreate(CompanyValidationAssignmentBase):
    pass


class CompanyValidationAssignmentUpdate(SQLModel):
    is_enabled: bool | None = None


class CompanyValidationAssignment(CompanyValidationAssignmentBase, table=True):
    __table_args__ = (
        UniqueConstraint(
            "company_id", "validation_rule_id", name="uq_company_validation_assignment"
        ),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class CompanyValidationAssignmentPublic(CompanyValidationAssignmentBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CompaniesPublic(SQLModel):
    data: list[CompanyPublic]
    count: int


class CompanyEmailDomainsPublic(SQLModel):
    data: list[CompanyEmailDomainPublic]
    count: int


class ClientRateContractsPublic(SQLModel):
    data: list[ClientRateContractPublic]
    count: int


class ValidationRulesPublic(SQLModel):
    data: list[ValidationRulePublic]
    count: int


class CompanyValidationAssignmentsPublic(SQLModel):
    data: list[CompanyValidationAssignmentPublic]
    count: int
