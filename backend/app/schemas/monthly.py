"""Schemas for monthly tracking workflow."""

from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel


# === Monthly Report ===

class MonthlyReportCreate(BaseModel):
    report_month: date  # First day of month
    current_index: Decimal  # required — captured at report open
    vat_rate: Decimal       # required — captured at report open (e.g. 0.18 for 18%)


class MonthlyReportResponse(BaseModel):
    id: int
    project_id: int
    report_month: date
    report_number: int
    status: str
    current_index: Decimal | None
    vat_rate: Decimal
    data_completeness: dict | None
    generated_word_url: str | None
    generated_pdf_url: str | None
    generated_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


# === Bank Statement ===

class BankStatementResponse(BaseModel):
    id: int
    account_type: str
    original_filename: str | None
    bank_name: str | None
    account_number: str | None
    statement_start_date: date | None
    statement_end_date: date | None
    opening_balance: Decimal | None
    closing_balance: Decimal | None
    parsing_status: str
    ai_warnings: list | None
    transactions_count: int = 0
    model_config = {"from_attributes": True}


class BankTransactionResponse(BaseModel):
    id: int
    transaction_date: date
    description: str
    amount: Decimal
    balance: Decimal | None
    transaction_type: str
    category: str | None
    ai_suggested_category: str | None
    ai_confidence: Decimal | None
    is_manually_classified: bool
    reference_number: str | None
    notes: str | None
    model_config = {"from_attributes": True}


class TransactionClassifyRequest(BaseModel):
    category: str
    notes: str | None = None
    linked_apartment_id: int | None = None


# === Construction Progress ===

class ConstructionProgressUpdate(BaseModel):
    overall_percent: Decimal
    description_text: str | None = None
    visit_date: datetime | None = None
    visitor_name: str | None = None


class ConstructionProgressResponse(BaseModel):
    id: int
    overall_percent: Decimal
    monthly_delta_percent: Decimal
    description_text: str | None
    visit_date: datetime | None
    visitor_name: str | None
    model_config = {"from_attributes": True}


# === Sales ===

class SalesContractCreate(BaseModel):
    apartment_id: int
    buyer_name: str
    buyer_id_number: str | None = None
    contract_date: date
    original_price_with_vat: Decimal | None = None
    final_price_with_vat: Decimal
    final_price_no_vat: Decimal
    vat_rate: Decimal | None = None  # snapshot of project VAT rate at sale time
    notes: str | None = None


class SalesContractResponse(BaseModel):
    id: int
    apartment_id: int
    buyer_name: str
    buyer_id_number: str | None
    contract_date: date
    original_price_with_vat: Decimal | None
    final_price_with_vat: Decimal
    final_price_no_vat: Decimal
    vat_rate: Decimal | None = None
    is_recognized_by_bank: bool
    is_non_linear: bool
    notes: str | None
    model_config = {"from_attributes": True}


# === Payment Schedule ===

class PaymentScheduleItemCreate(BaseModel):
    payment_number: int = 1
    description: str | None = None
    scheduled_amount: Decimal
    scheduled_date: date
    actual_amount: Decimal | None = None
    actual_date: date | None = None
    status: str = "scheduled"
    reference_number: str | None = None
    notes: str | None = None


class PaymentScheduleItemUpdate(BaseModel):
    description: str | None = None
    scheduled_amount: Decimal | None = None
    scheduled_date: date | None = None
    actual_amount: Decimal | None = None
    actual_date: date | None = None
    status: str | None = None
    reference_number: str | None = None
    notes: str | None = None


class PaymentScheduleItemResponse(BaseModel):
    id: int
    contract_id: int
    payment_number: int
    description: str | None
    scheduled_amount: Decimal
    scheduled_date: date
    actual_amount: Decimal | None
    actual_date: date | None
    status: str
    reference_number: str | None
    notes: str | None
    model_config = {"from_attributes": True}


# === Data Completeness ===

class DataCompleteness(BaseModel):
    bank_statement_uploaded: bool = False
    all_transactions_classified: bool = False
    construction_progress_entered: bool = False
    index_updated: bool = False
    sales_updated: bool = True  # Optional - only if new sales
    guarantees_uploaded: bool = False
    ready_to_generate: bool = False
    missing_items: list[str] = []
