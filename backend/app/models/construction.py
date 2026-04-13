"""Construction progress model."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Numeric, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class ConstructionProgress(Base):
    __tablename__ = "construction_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    monthly_report_id: Mapped[int] = mapped_column(ForeignKey("monthly_reports.id"), unique=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    overall_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    monthly_delta_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    description_text: Mapped[str | None] = mapped_column(Text)  # תיאור עבודות שבוצעו
    visit_date: Mapped[datetime | None] = mapped_column(DateTime)
    visitor_name: Mapped[str | None] = mapped_column(Text)
    photos: Mapped[list | None] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    monthly_report = relationship("MonthlyReport", back_populates="construction_progress")
