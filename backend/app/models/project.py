"""Project and related setup models."""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, Boolean, ForeignKey, Numeric, JSON, Text, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
import enum


class ProjectPhase(str, enum.Enum):
    SETUP = "setup"
    ACTIVE = "active"
    COMPLETED = "completed"


class BankName(str, enum.Enum):
    LEUMI = "leumi"
    HAPOALIM = "hapoalim"
    DISCOUNT = "discount"
    MIZRAHI = "mizrahi"
    INTERNATIONAL = "international"
    JERUSALEM = "jerusalem"
    YAHAV = "yahav"
    OTSAR = "otsar"
    MASSAD = "massad"
    OTHER = "other"


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_firm_active", "firm_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firms.id"), index=True)
    project_name: Mapped[str] = mapped_column(String(300))
    address: Mapped[str | None] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(100))
    neighborhood: Mapped[str | None] = mapped_column(String(100))
    block: Mapped[str | None] = mapped_column(String(50))  # gush
    parcel: Mapped[str | None] = mapped_column(String(100))  # helka
    developer_name: Mapped[str | None] = mapped_column(String(200))
    developer_company_number: Mapped[str | None] = mapped_column(String(20))
    developer_contacts: Mapped[dict | None] = mapped_column(JSON, default=list)
    bank: Mapped[BankName | None] = mapped_column(SAEnum(BankName))
    bank_branch: Mapped[str | None] = mapped_column(String(50))
    project_account_number: Mapped[str | None] = mapped_column(String(50))
    escrow_account_number: Mapped[str | None] = mapped_column(String(50))
    phase: Mapped[ProjectPhase] = mapped_column(SAEnum(ProjectPhase), default=ProjectPhase.SETUP)
    report_0_date: Mapped[date | None] = mapped_column(Date)
    report_0_reference: Mapped[str | None] = mapped_column(String(50))
    base_index: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    base_index_date: Mapped[date | None] = mapped_column(Date)
    contractor_base_index: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    contractor_base_index_date: Mapped[date | None] = mapped_column(Date)
    current_report_number: Mapped[int] = mapped_column(default=0)
    total_units: Mapped[int | None] = mapped_column()
    total_buildings: Mapped[int | None] = mapped_column()
    project_type: Mapped[str | None] = mapped_column(String(50))  # pinui_binui, land, combination
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    firm = relationship("Firm", back_populates="projects")
    financing = relationship("ProjectFinancing", back_populates="project", uselist=False)
    contractor = relationship("ContractorAgreement", back_populates="project", uselist=False)
    milestones = relationship("Milestone", back_populates="project", order_by="Milestone.display_order")
    budget_categories = relationship("BudgetCategory", back_populates="project")
    apartments = relationship("Apartment", back_populates="project")
    monthly_reports = relationship("MonthlyReport", back_populates="project", order_by="MonthlyReport.report_number.desc()")


class ProjectFinancing(Base):
    __tablename__ = "project_financing"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    financing_type: Mapped[str | None] = mapped_column(String(20))  # banking / non_banking
    financing_body: Mapped[str | None] = mapped_column(String(100))
    agreement_date: Mapped[date | None] = mapped_column(Date)
    credit_limit_total: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    credit_limit_construction: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    credit_limit_land: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    credit_limit_guarantees: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # List of {label: str, amount: number} dicts. Sum is mirrored to credit_limit_guarantees.
    guarantee_frameworks: Mapped[list | None] = mapped_column(JSON)
    equity_required_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # List of {label: str, amount: number, approved_by: str} pre-project investments
    # that count toward the required equity (e.g., contractor-paid land deposits).
    pre_project_investments: Mapped[list | None] = mapped_column(JSON)
    equity_required_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    presale_units_required: Mapped[int | None] = mapped_column()
    presale_amount_required: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # Optional: equity required AFTER pre-sale conditions are met (often lower).
    equity_required_after_presale: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    guarantee_fee_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="financing")


class ContractorAgreement(Base):
    __tablename__ = "contractor_agreements"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    contractor_name: Mapped[str | None] = mapped_column(String(200))
    contractor_company_number: Mapped[str | None] = mapped_column(String(20))
    contractor_classification: Mapped[str | None] = mapped_column(String(50))
    contractor_license: Mapped[str | None] = mapped_column(String(50))
    contract_date: Mapped[date | None] = mapped_column(Date)
    contract_amount_no_vat: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    contract_amount_with_vat: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    base_index_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    base_index_date: Mapped[date | None] = mapped_column(Date)
    guarantee_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    guarantee_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    retention_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    retention_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    construction_duration_months: Mapped[int | None] = mapped_column()
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="contractor")


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    planned_date: Mapped[date | None] = mapped_column(Date)
    actual_date: Mapped[date | None] = mapped_column(Date)
    display_order: Mapped[int] = mapped_column(default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="milestones")
