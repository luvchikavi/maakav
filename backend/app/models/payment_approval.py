"""Payment Approval model (אישורי שיקים/העברות)."""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, Boolean, ForeignKey, Numeric, Text, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
import enum


class OperationType(str, enum.Enum):
    CHECK = "check"         # שיק
    TRANSFER = "transfer"   # העברה


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"     # ממתין לאישור
    APPROVED = "approved"   # מאושר
    REJECTED = "rejected"   # נדחה


class PaymentApprovalStatus(str, enum.Enum):
    UNPAID = "unpaid"   # לא שולם
    PAID = "paid"       # שולם


class PaymentApproval(Base):
    __tablename__ = "payment_approvals"
    __table_args__ = (
        Index("ix_pa_project_status", "project_id", "approval_status"),
        Index("ix_pa_project_month", "project_id", "report_month"),
        Index("ix_pa_due_date", "project_id", "due_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    monthly_report_id: Mapped[int | None] = mapped_column(ForeignKey("monthly_reports.id"))
    report_month: Mapped[date] = mapped_column(Date)

    # Operation details
    operation_type: Mapped[OperationType] = mapped_column(SAEnum(OperationType), default=OperationType.TRANSFER)
    serial_number: Mapped[int | None] = mapped_column()  # מס' סידורי
    check_number: Mapped[str | None] = mapped_column(String(50))
    amount_with_vat: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    amount_no_vat: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    vat_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    beneficiary_name: Mapped[str] = mapped_column(String(200))  # שם המוטב
    due_date: Mapped[date | None] = mapped_column(Date)  # תאריך פירעון
    description: Mapped[str | None] = mapped_column(Text)  # פירוט
    budget_category: Mapped[str | None] = mapped_column(String(100))  # סעיף תקציבי
    invoice_number: Mapped[str | None] = mapped_column(String(100))  # חשבונית
    reference: Mapped[str | None] = mapped_column(String(200))  # אסמכתא

    # Approval workflow
    approval_status: Mapped[ApprovalStatus] = mapped_column(SAEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    approved_by: Mapped[str | None] = mapped_column(String(100))
    approved_date: Mapped[datetime | None] = mapped_column(DateTime)
    approval_notes: Mapped[str | None] = mapped_column(Text)

    # Payment tracking
    payment_status: Mapped[PaymentApprovalStatus] = mapped_column(SAEnum(PaymentApprovalStatus), default=PaymentApprovalStatus.UNPAID)
    linked_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("bank_transactions.id"))
    actual_payment_date: Mapped[date | None] = mapped_column(Date)

    # Audit
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project")
    monthly_report = relationship("MonthlyReport")
