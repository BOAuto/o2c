import uuid
from datetime import datetime

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class BranchBase(SQLModel):
    name: str = Field(max_length=255, unique=True, index=True)
    slug: str = Field(max_length=128, unique=True, index=True)
    branch_gstin: str = Field(max_length=15, unique=True, index=True)
    is_active: bool = True


class BranchCreate(BranchBase):
    pass


class BranchUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=128)
    branch_gstin: str | None = Field(default=None, max_length=15)
    is_active: bool | None = None


class Branch(BranchBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class BranchPublic(BranchBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GstStateCodeBase(SQLModel):
    code: str = Field(max_length=2, unique=True, index=True)
    description: str = Field(max_length=255)


class GstStateCode(GstStateCodeBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class GstStateCodePublic(GstStateCodeBase):
    id: uuid.UUID


class BranchGstStateBase(SQLModel):
    branch_id: uuid.UUID = Field(index=True)
    gst_state_code_id: uuid.UUID = Field(index=True)


class BranchGstStateCreate(BranchGstStateBase):
    pass


class BranchGstState(BranchGstStateBase, table=True):
    __table_args__ = (
        UniqueConstraint("branch_id", "gst_state_code_id", name="uq_branch_gst_state"),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class BranchGstStatePublic(BranchGstStateBase):
    id: uuid.UUID
    created_at: datetime | None = None


class BranchesPublic(SQLModel):
    data: list[BranchPublic]
    count: int


class GstStateCodesPublic(SQLModel):
    data: list[GstStateCodePublic]
    count: int


class BranchGstStatesPublic(SQLModel):
    data: list[BranchGstStatePublic]
    count: int
