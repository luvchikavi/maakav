"""Guarantee snapshot model (ערבויות)."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Numeric, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class GuaranteeSnapshot(Base):
    __tablename__ = "guarantee_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    monthly_report_id: Mapped[int] = mapped_column(ForeignKey("monthly_reports.id"), unique=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    total_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_receipts: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)  # תקבולים ללא מע"מ
    gap: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)  # הפרש
    uploaded_file_url: Mapped[str | None] = mapped_column(String(500))
    items: Mapped[list | None] = mapped_column(JSON, default=list)  # [{buyer, amount, type, expiry}]
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    monthly_report = relationship("MonthlyReport", back_populates="guarantee_snapshot")
