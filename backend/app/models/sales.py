"""Sales contracts and payment schedule models."""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, ForeignKey, Numeric, Text, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
import enum


class PaymentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"


class SalesContract(Base):
    __tablename__ = "sales_contracts"
    __table_args__ = (
        Index("ix_sales_project", "project_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    apartment_id: Mapped[int] = mapped_column(ForeignKey("apartments.id"), unique=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    buyer_name: Mapped[str] = mapped_column(String(200))
    buyer_id_number: Mapped[str | None] = mapped_column(String(20))
    contract_date: Mapped[date] = mapped_column(Date)
    original_price_with_vat: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    final_price_with_vat: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    final_price_no_vat: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    # Snapshot of the VAT rate at sale time. Lets the no-VAT side of past
    # sales stay correct after a project-level rate change.
    vat_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    is_recognized_by_bank: Mapped[bool] = mapped_column(default=False)  # תקבולים >15%
    is_non_linear: Mapped[bool] = mapped_column(default=False)  # תקבול אחרון >40%
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    apartment = relationship("Apartment", back_populates="sales_contract")
    payment_schedule = relationship("PaymentScheduleItem", back_populates="contract", order_by="PaymentScheduleItem.scheduled_date")


class PaymentScheduleItem(Base):
    __tablename__ = "payment_schedule"
    __table_args__ = (
        Index("ix_payment_contract", "contract_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("sales_contracts.id"))
    payment_number: Mapped[int] = mapped_column(default=1)
    description: Mapped[str | None] = mapped_column(String(200))
    scheduled_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    scheduled_date: Mapped[date] = mapped_column(Date)
    actual_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    actual_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), default=PaymentStatus.SCHEDULED)
    reference_number: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contract = relationship("SalesContract", back_populates="payment_schedule")
