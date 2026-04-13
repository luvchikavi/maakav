"""Project schemas."""

from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    project_name: str
    address: str | None = None
    city: str | None = None
    developer_name: str | None = None
    bank: str | None = None
    project_account_number: str | None = None
    project_type: str | None = None


class ProjectUpdate(BaseModel):
    project_name: str | None = None
    address: str | None = None
    city: str | None = None
    neighborhood: str | None = None
    block: str | None = None
    parcel: str | None = None
    developer_name: str | None = None
    developer_company_number: str | None = None
    bank: str | None = None
    bank_branch: str | None = None
    project_account_number: str | None = None
    escrow_account_number: str | None = None
    base_index: Decimal | None = None
    base_index_date: date | None = None
    contractor_base_index: Decimal | None = None
    report_0_date: date | None = None
    total_units: int | None = None
    total_buildings: int | None = None
    project_type: str | None = None
    notes: str | None = None


class ProjectResponse(BaseModel):
    id: int
    firm_id: int
    project_name: str
    address: str | None
    city: str | None
    bank: str | None
    phase: str
    current_report_number: int
    total_units: int | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectDetailResponse(ProjectResponse):
    neighborhood: str | None
    block: str | None
    parcel: str | None
    developer_name: str | None
    developer_company_number: str | None
    bank_branch: str | None
    project_account_number: str | None
    escrow_account_number: str | None
    base_index: Decimal | None
    base_index_date: date | None
    contractor_base_index: Decimal | None
    report_0_date: date | None
    total_buildings: int | None
    project_type: str | None
    notes: str | None
    updated_at: datetime
