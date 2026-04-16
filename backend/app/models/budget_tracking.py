"""Monthly budget tracking snapshot - the 15-column table (נספח א')."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import DateTime, ForeignKey, Numeric, Boolean, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class BudgetTrackingSnapshot(Base):
    """Monthly snapshot of budget tracking for a project."""
    __tablename__ = "budget_tracking_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    monthly_report_id: Mapped[int] = mapped_column(ForeignKey("monthly_reports.id"), unique=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    base_index: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    current_index: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    # Summary totals
    total_original_budget: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_budget_transfer: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_adjusted_indexed: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_monthly_paid: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_cumulative_paid: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_remaining: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    monthly_report = relationship("MonthlyReport", back_populates="budget_tracking")
    lines = relationship("BudgetTrackingLine", back_populates="snapshot", order_by="BudgetTrackingLine.display_order")


class BudgetTrackingLine(Base):
    """
    Individual line in the budget tracking table.
    Maps to the 15-column Excel structure:

    INPUT columns:
      C (T1)  = original_budget         - from Section 8, static
      D (T2)  = budget_transfer         - manual adjustments
      F       = cumulative_prev_base    - from previous month snapshot
      J       = cumulative_prev_actual  - from previous month snapshot
      K       = monthly_paid_actual     - from bank transactions (auto)

    CALCULATED columns:
      E       = adjusted_indexed        = (C+D) × index_ratio
      G       = monthly_paid_base       = K × inverse_ratio
      H       = cumulative_base         = F + G
      I       = remaining_base          = (C+D) - H
      L       = cumulative_actual       = J + K
      N       = remaining_indexed       = I × index_ratio
      O       = total_indexed           = N + L
      M       = execution_percent       = L / O × 100
    """
    __tablename__ = "budget_tracking_lines"
    __table_args__ = (
        Index("ix_btl_snapshot", "snapshot_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("budget_tracking_snapshots.id"))
    category: Mapped[str] = mapped_column(String(50))
    display_order: Mapped[int] = mapped_column(default=0)
    is_index_linked: Mapped[bool] = mapped_column(Boolean, default=True)

    # INPUT columns
    original_budget: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)          # C / T1
    budget_transfer: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)          # D / T2
    cumulative_prev_base: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)     # F
    cumulative_prev_actual: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)   # J
    monthly_paid_actual: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)      # K

    # CALCULATED columns
    adjusted_indexed: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)         # E
    monthly_paid_base: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)        # G
    cumulative_base: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)          # H
    remaining_base: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)           # I
    cumulative_actual: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)        # L
    remaining_indexed: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)        # N
    total_indexed: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)            # O
    execution_percent: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0)         # M

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    snapshot = relationship("BudgetTrackingSnapshot", back_populates="lines")

    def calculate_all(self, base_index: Decimal, current_index: Decimal):
        """
        Calculate all derived columns. Ported from Nectra's BudgetTrackingLineItem.calculate_all().
        Source: Nectra/backend/apps/budget/models/monthly_budget_tracking.py:413-469
        """
        if self.is_index_linked and base_index and current_index and base_index != 0:
            index_ratio = current_index / base_index
            inverse_ratio = base_index / current_index
        else:
            index_ratio = Decimal("1.0")
            inverse_ratio = Decimal("1.0")

        total_budget_base = self.original_budget + self.budget_transfer

        # E: Adjusted budget indexed = (C+D) × index_ratio
        self.adjusted_indexed = (total_budget_base * index_ratio).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        # G: Monthly paid in base values = K × inverse_ratio
        self.monthly_paid_base = (self.monthly_paid_actual * inverse_ratio).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        # H: Cumulative paid base = F + G
        self.cumulative_base = self.cumulative_prev_base + self.monthly_paid_base
        # I: Remaining budget base = (C+D) - H
        self.remaining_base = total_budget_base - self.cumulative_base
        # L: Cumulative paid actual = J + K
        self.cumulative_actual = self.cumulative_prev_actual + self.monthly_paid_actual
        # N: Remaining budget indexed = I × index_ratio
        self.remaining_indexed = (self.remaining_base * index_ratio).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        # O: Total budget indexed = N + L
        self.total_indexed = self.remaining_indexed + self.cumulative_actual
        # M: Execution percent = L / O × 100
        if self.total_indexed and self.total_indexed != 0:
            self.execution_percent = (
                (self.cumulative_actual / self.total_indexed) * 100
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            self.execution_percent = Decimal("0")
