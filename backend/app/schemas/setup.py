"""Schemas for project setup (budget, apartments, financing, contractor, milestones)."""

from datetime import date
from decimal import Decimal
from pydantic import BaseModel


# === Budget ===

class BudgetLineItemCreate(BaseModel):
    description: str
    source: str | None = None
    cost_no_vat: Decimal = Decimal("0")
    is_index_linked: bool = True
    vat_exempt: bool = False
    supplier_name: str | None = None
    notes: str | None = None


class BudgetCategoryCreate(BaseModel):
    category_type: str
    line_items: list[BudgetLineItemCreate] = []


class BudgetUploadResponse(BaseModel):
    categories_count: int
    items_count: int
    total_budget: float


class BudgetLineItemResponse(BaseModel):
    id: int
    line_number: int
    description: str
    source: str | None
    cost_no_vat: Decimal
    is_index_linked: bool
    vat_exempt: bool
    supplier_name: str | None
    notes: str | None
    model_config = {"from_attributes": True}


class BudgetCategoryResponse(BaseModel):
    id: int
    category_type: str
    display_order: int
    total_amount: Decimal
    line_items: list[BudgetLineItemResponse] = []
    model_config = {"from_attributes": True}


# === Apartments ===

class ApartmentCreate(BaseModel):
    building_number: str = "A"
    floor: str | None = None
    unit_number: str | None = None
    unit_type: str = "apartment"
    ownership: str = "developer"
    unit_status: str = "for_sale"
    room_count: Decimal | None = None
    net_area_sqm: Decimal | None = None
    balcony_area_sqm: Decimal | None = None
    terrace_area_sqm: Decimal | None = None
    parking_count: int = 0
    storage_count: int = 0
    list_price_with_vat: Decimal | None = None
    list_price_no_vat: Decimal | None = None
    report_0_price_no_vat: Decimal | None = None
    include_in_revenue: bool = True
    notes: str | None = None


class ApartmentResponse(BaseModel):
    id: int
    building_number: str
    floor: str | None
    unit_number: str | None
    unit_type: str
    direction: str | None = None
    ownership: str
    unit_status: str
    room_count: Decimal | None
    net_area_sqm: Decimal | None
    list_price_with_vat: Decimal | None
    list_price_no_vat: Decimal | None
    report_0_price_no_vat: Decimal | None
    owner_name: str | None = None
    gross_area_sqm: Decimal | None = None
    gallery_area_sqm: Decimal | None = None
    secondary_type: str | None = None
    include_in_revenue: bool
    model_config = {"from_attributes": True}


# === Financing ===

class GuaranteeFrameworkItem(BaseModel):
    label: str
    amount: Decimal | None = None
    kind: str | None = None  # "sale_law", "land_owner", "free_text"


class PreProjectInvestmentItem(BaseModel):
    label: str
    amount: Decimal | None = None
    approved_by: str | None = None


class FinancingUpdate(BaseModel):
    financing_type: str | None = None
    financing_body: str | None = None
    agreement_date: date | None = None
    credit_limit_total: Decimal | None = None
    credit_limit_construction: Decimal | None = None
    credit_limit_land: Decimal | None = None
    credit_limit_guarantees: Decimal | None = None
    guarantee_frameworks: list[GuaranteeFrameworkItem] | None = None
    equity_required_amount: Decimal | None = None
    equity_required_percent: Decimal | None = None
    pre_project_investments: list[PreProjectInvestmentItem] | None = None
    presale_units_required: int | None = None
    presale_amount_required: Decimal | None = None
    equity_required_after_presale: Decimal | None = None
    interest_rate: Decimal | None = None
    guarantee_fee_percent: Decimal | None = None
    notes: str | None = None


class FinancingResponse(FinancingUpdate):
    id: int
    project_id: int
    model_config = {"from_attributes": True}


# === Contractor ===

class ContractorUpdate(BaseModel):
    contractor_name: str | None = None
    contractor_company_number: str | None = None
    contractor_classification: str | None = None
    contract_date: date | None = None
    contract_amount_no_vat: Decimal | None = None
    contract_amount_with_vat: Decimal | None = None
    base_index_value: Decimal | None = None
    base_index_date: date | None = None
    guarantee_percent: Decimal | None = None
    guarantee_amount: Decimal | None = None
    retention_percent: Decimal | None = None
    construction_duration_months: int | None = None
    notes: str | None = None


class ContractorResponse(ContractorUpdate):
    id: int
    project_id: int
    model_config = {"from_attributes": True}


# === Milestones ===

class MilestoneCreate(BaseModel):
    name: str
    planned_date: date | None = None
    actual_date: date | None = None
    display_order: int = 0
    notes: str | None = None


class MilestoneUpdate(BaseModel):
    name: str | None = None
    planned_date: date | None = None
    actual_date: date | None = None
    display_order: int | None = None
    notes: str | None = None


class MilestoneResponse(BaseModel):
    id: int
    name: str
    planned_date: date | None
    actual_date: date | None
    display_order: int
    notes: str | None
    model_config = {"from_attributes": True}


# === Setup Status ===

class SetupStatus(BaseModel):
    budget: bool = False
    apartments: bool = False
    financing: bool = False
    contractor: bool = False
    milestones: bool = False
    budget_items_count: int = 0
    apartments_count: int = 0
    total_budget: float = 0
