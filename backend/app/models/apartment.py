"""Apartment inventory model."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Numeric, Text, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
import enum


class Ownership(str, enum.Enum):
    DEVELOPER = "developer"  # יזם
    RESIDENT = "resident"    # דיירים / בעלים


class UnitStatus(str, enum.Enum):
    FOR_SALE = "for_sale"        # לשיווק
    SOLD = "sold"                # נמכר
    COMPENSATION = "compensation"  # תמורה (דיירים)
    FOR_RENT = "for_rent"        # להשכרה
    RESERVED = "reserved"        # שמור
    INVENTORY = "inventory"      # מלאי


class UnitType(str, enum.Enum):
    APARTMENT = "apartment"
    PENTHOUSE = "penthouse"
    GARDEN = "garden"
    DUPLEX = "duplex"
    MINI_PENTHOUSE = "mini_penthouse"
    OFFICE = "office"
    RETAIL = "retail"
    STORAGE = "storage"
    PARKING = "parking"
    OTHER = "other"


class Apartment(Base):
    __tablename__ = "apartments"
    __table_args__ = (
        Index("ix_apartments_project", "project_id"),
        Index("ix_apartments_project_building", "project_id", "building_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    building_number: Mapped[str] = mapped_column(String(20), default="A")
    floor: Mapped[str | None] = mapped_column(String(20))
    unit_number: Mapped[str | None] = mapped_column(String(20))
    plan_number: Mapped[str | None] = mapped_column(String(50))
    direction: Mapped[str | None] = mapped_column(String(50))
    unit_type: Mapped[UnitType] = mapped_column(SAEnum(UnitType), default=UnitType.APARTMENT)
    ownership: Mapped[Ownership] = mapped_column(SAEnum(Ownership), default=Ownership.DEVELOPER)
    unit_status: Mapped[UnitStatus] = mapped_column(SAEnum(UnitStatus), default=UnitStatus.FOR_SALE)
    room_count: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    net_area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    balcony_area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    terrace_area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    yard_area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    parking_count: Mapped[int] = mapped_column(default=0)
    storage_count: Mapped[int] = mapped_column(default=0)
    list_price_with_vat: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    list_price_no_vat: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    price_per_sqm: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    report_0_price_no_vat: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # מחיר דוח 0
    include_in_revenue: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="apartments")
    sales_contract = relationship("SalesContract", back_populates="apartment", uselist=False)
