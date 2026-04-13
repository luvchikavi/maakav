"""Monthly report - the central entity for each tracking month."""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, ForeignKey, Numeric, JSON, Text, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
import enum


class ReportStatus(str, enum.Enum):
    DRAFT = "draft"            # נוצר, טרם הוזנו נתונים
    DATA_ENTRY = "data_entry"  # בהזנת נתונים
    REVIEW = "review"          # סקירה וחישובים
    APPROVED = "approved"      # אושר
    LOCKED = "locked"          # נעול (לאחר הפקת דוח)


class MonthlyReport(Base):
    __tablename__ = "monthly_reports"
    __table_args__ = (
        Index("ix_monthly_project_month", "project_id", "report_month", unique=True),
        Index("ix_monthly_project_number", "project_id", "report_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    report_month: Mapped[date] = mapped_column(Date)  # First day of the month
    report_number: Mapped[int] = mapped_column()
    status: Mapped[ReportStatus] = mapped_column(SAEnum(ReportStatus), default=ReportStatus.DRAFT)
    current_index: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.18"))

    # Data completeness tracking
    data_completeness: Mapped[dict | None] = mapped_column(JSON, default=dict)
    # e.g. {"bank_statement": true, "transactions_classified": false, "construction": true, ...}

    # Generated report files
    generated_word_url: Mapped[str | None] = mapped_column(String(500))
    generated_pdf_url: Mapped[str | None] = mapped_column(String(500))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime)

    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="monthly_reports")
    bank_statements = relationship("BankStatement", back_populates="monthly_report")
    budget_tracking = relationship("BudgetTrackingSnapshot", back_populates="monthly_report", uselist=False)
    construction_progress = relationship("ConstructionProgress", back_populates="monthly_report", uselist=False)
    vat_tracking = relationship("VatTracking", back_populates="monthly_report", uselist=False)
    equity_tracking = relationship("EquityTracking", back_populates="monthly_report", uselist=False)
    guarantee_snapshot = relationship("GuaranteeSnapshot", back_populates="monthly_report", uselist=False)
    profitability = relationship("ProfitabilitySnapshot", back_populates="monthly_report", uselist=False)
    sources_uses = relationship("SourcesUses", back_populates="monthly_report", uselist=False)
