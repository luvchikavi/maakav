"""VAT tracking model (מעקב מע"מ)."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class VatTracking(Base):
    __tablename__ = "vat_tracking"

    id: Mapped[int] = mapped_column(primary_key=True)
    monthly_report_id: Mapped[int] = mapped_column(ForeignKey("monthly_reports.id"), unique=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    # חודשי
    transactions_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)  # עסקאות
    output_vat: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)           # מע"מ עסקאות
    inputs_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)         # תשומות
    input_vat: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)            # מע"מ תשומות
    vat_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)          # לקבל / (לשלם)
    vat_received: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)         # התקבל בפועל
    # מצטבר
    cumulative_vat_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    monthly_report = relationship("MonthlyReport", back_populates="vat_tracking")
