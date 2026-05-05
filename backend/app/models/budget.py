"""Budget models (Section 8 / Report 0 data)."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Numeric, Text, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
import enum


class CategoryType(str, enum.Enum):
    TENANT_EXPENSES = "tenant_expenses"          # הוצאות דיירים
    LAND_AND_TAXES = "land_and_taxes"            # קרקע ומיסוי
    INDIRECT_COSTS = "indirect_costs"            # הוצאות עקיפות (כלליות)
    DIRECT_CONSTRUCTION = "direct_construction"  # בניה ישירה
    EXTRAORDINARY = "extraordinary"              # הוצאות חריגות


class BudgetCategory(Base):
    """Top-level budget category (e.g., קרקע והוצאות דיירים, כלליות, הקמה)."""
    __tablename__ = "budget_categories"
    __table_args__ = (
        Index("ix_budget_cat_project", "project_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    category_type: Mapped[CategoryType] = mapped_column(SAEnum(CategoryType))
    display_order: Mapped[int] = mapped_column(default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="budget_categories")
    line_items = relationship("BudgetLineItem", back_populates="category", order_by="BudgetLineItem.line_number")


class BudgetLineItem(Base):
    """Individual budget line item within a category."""
    __tablename__ = "budget_line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("budget_categories.id"), index=True)
    line_number: Mapped[int] = mapped_column(default=0)
    description: Mapped[str] = mapped_column(String(300))
    source: Mapped[str | None] = mapped_column(String(100))  # ע"פ הסכם / אומדן / שובר
    cost_no_vat: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    # Pre-project equity investment recognized for this specific line by an
    # appraiser. Reduces the line's "remaining" by this amount and rolls up
    # into the financing-tab pre-project investments total.
    equity_investment: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    is_index_linked: Mapped[bool] = mapped_column(Boolean, default=True)
    vat_exempt: Mapped[bool] = mapped_column(Boolean, default=False)
    supplier_name: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("BudgetCategory", back_populates="line_items")
