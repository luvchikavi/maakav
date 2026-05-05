"""Per-monthly-report snapshot of loans and deposits (הלוואות ופקדונות).

Structure mirrors the example PDF the user provided: every loan and deposit
keeps a principal, a current ("י.ס.") balance/value, and the snapshot is
made `as_of` a specific date so month-over-month diffs work.

Items are stored as JSON arrays so the user can add new loan tranches per
project without a schema change. Totals can be derived; we don't store them.
"""

from datetime import date as date_type, datetime

from sqlalchemy import Date, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class LoansDepositsTracking(Base):
    __tablename__ = "loans_deposits_tracking"

    id: Mapped[int] = mapped_column(primary_key=True)
    monthly_report_id: Mapped[int] = mapped_column(
        ForeignKey("monthly_reports.id"), unique=True
    )
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    as_of: Mapped[date_type | None] = mapped_column(Date)

    # Each item:
    # {label: str, principal: number, current_balance: number,
    #  prev_month: number | null, kind: "senior" | "mezzanine" | "other"}
    loans: Mapped[list | None] = mapped_column(JSON, default=list)
    # Each item:
    # {label: str, principal: number, current_balance: number,
    #  prev_month: number | null, accrued_interest: number | null}
    deposits: Mapped[list | None] = mapped_column(JSON, default=list)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
