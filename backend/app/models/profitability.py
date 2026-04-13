"""Profitability snapshot model (רווחיות)."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class ProfitabilitySnapshot(Base):
    __tablename__ = "profitability_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    monthly_report_id: Mapped[int] = mapped_column(ForeignKey("monthly_reports.id"), unique=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    # דוח אפס
    income_report_0: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    cost_report_0: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    profit_report_0: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    profit_percent_report_0: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0)
    # נוכחי
    income_current: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    cost_current: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    profit_current: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    profit_percent_current: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    monthly_report = relationship("MonthlyReport", back_populates="profitability")
