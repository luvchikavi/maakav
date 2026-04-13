"""Equity tracking model (הון עצמי)."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Numeric, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class EquityTracking(Base):
    __tablename__ = "equity_tracking"

    id: Mapped[int] = mapped_column(primary_key=True)
    monthly_report_id: Mapped[int] = mapped_column(ForeignKey("monthly_reports.id"), unique=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    required_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_deposits: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_withdrawals: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    gap: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)  # עודף / (חסר)
    # פירוט תנועות הון עצמי לפי דוח
    transactions_detail: Mapped[list | None] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    monthly_report = relationship("MonthlyReport", back_populates="equity_tracking")
