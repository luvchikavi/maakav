"""Sources & Uses balance model (מקורות ושימושים)."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Numeric, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class SourcesUses(Base):
    __tablename__ = "sources_uses"

    id: Mapped[int] = mapped_column(primary_key=True)
    monthly_report_id: Mapped[int] = mapped_column(ForeignKey("monthly_reports.id"), unique=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    # מקורות
    source_equity: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    source_sales_receipts: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    source_bank_credit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    source_vat_refunds: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    source_other: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_sources: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    # שימושים
    use_payments: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    use_surplus_release: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    use_extraordinary: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    use_balance_remaining: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_uses: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    # מאזן
    balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    monthly_report = relationship("MonthlyReport", back_populates="sources_uses")
