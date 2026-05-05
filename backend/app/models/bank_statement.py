"""Bank statement and transaction models."""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, Boolean, ForeignKey, Numeric, JSON, Text, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
import enum


class ParsingStatus(str, enum.Enum):
    PENDING = "pending"
    PARSED = "parsed"
    REVIEWED = "reviewed"
    ERROR = "error"


class TransactionType(str, enum.Enum):
    CREDIT = "credit"  # זכות
    DEBIT = "debit"    # חובה


class TransactionCategory(str, enum.Enum):
    # הוצאות (6)
    TENANT_EXPENSES = "tenant_expenses"        # הוצאות דיירים
    LAND_AND_TAXES = "land_and_taxes"          # קרקע ומיסוי
    INDIRECT_COSTS = "indirect_costs"          # הוצאות עקיפות
    DIRECT_CONSTRUCTION = "direct_construction"  # בניה ישירה
    DEPOSIT_TO_SAVINGS = "deposit_to_savings"  # הפקדה לפקדון
    OTHER_EXPENSE = "other_expense"            # הוצאה אחרת
    # הכנסות (7)
    SALE_INCOME = "sale_income"                # הכנסה ממכירה
    TAX_REFUNDS = "tax_refunds"                # החזרי מיסים
    VAT_REFUNDS = "vat_refunds"                # החזרי מע"מ
    EQUITY_DEPOSIT = "equity_deposit"          # הפקדת הון עצמי
    UPGRADES_INCOME = "upgrades_income"        # הכנסה משידרוגים
    LOAN_RECEIVED = "loan_received"            # הכנסה מהלוואה
    OTHER_INCOME = "other_income"              # הכנסה אחרת
    # הלוואות (2)
    LOAN_REPAYMENT = "loan_repayment"          # החזר הלוואה
    # ריביות/עמלות (1)
    INTEREST_AND_FEES = "interest_and_fees"    # ריביות ועמלות


class BankStatement(Base):
    __tablename__ = "bank_statements"

    id: Mapped[int] = mapped_column(primary_key=True)
    monthly_report_id: Mapped[int] = mapped_column(ForeignKey("monthly_reports.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    account_type: Mapped[str] = mapped_column(String(20), default="project")  # project / escrow
    original_filename: Mapped[str | None] = mapped_column(String(300))
    file_url: Mapped[str | None] = mapped_column(String(500))
    bank_name: Mapped[str | None] = mapped_column(String(100))
    account_number: Mapped[str | None] = mapped_column(String(50))
    statement_start_date: Mapped[date | None] = mapped_column(Date)
    statement_end_date: Mapped[date | None] = mapped_column(Date)
    opening_balance: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    closing_balance: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    ai_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ai_warnings: Mapped[list | None] = mapped_column(JSON, default=list)
    parsing_status: Mapped[ParsingStatus] = mapped_column(SAEnum(ParsingStatus), default=ParsingStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    monthly_report = relationship("MonthlyReport", back_populates="bank_statements")
    transactions = relationship("BankTransaction", back_populates="bank_statement", order_by="BankTransaction.transaction_date")


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    __table_args__ = (
        Index("ix_tx_report", "monthly_report_id"),
        Index("ix_tx_project_date", "project_id", "transaction_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_statement_id: Mapped[int] = mapped_column(ForeignKey("bank_statements.id"))
    monthly_report_id: Mapped[int] = mapped_column(ForeignKey("monthly_reports.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    transaction_date: Mapped[date] = mapped_column(Date)
    value_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(500))
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))  # Always positive
    balance: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    transaction_type: Mapped[TransactionType] = mapped_column(SAEnum(TransactionType))
    category: Mapped[TransactionCategory | None] = mapped_column(SAEnum(TransactionCategory))
    # Two-level classification (item A in the QA list):
    # - category_primary: broad bucket (Hebrew label rendered from
    #   transaction_taxonomy.PRIMARY_LABELS). Stored as the English key.
    # - subcategory: the specific sub-item within the primary, either a
    #   key from PRIMARY_SECONDARIES or a budget-line id rendered as a
    #   string (for the four budget-line primaries).
    category_primary: Mapped[str | None] = mapped_column(String(60))
    subcategory: Mapped[str | None] = mapped_column(String(120))
    ai_suggested_category: Mapped[str | None] = mapped_column(String(50))
    ai_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    is_manually_classified: Mapped[bool] = mapped_column(Boolean, default=False)
    linked_apartment_id: Mapped[int | None] = mapped_column(ForeignKey("apartments.id"))
    reference_number: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bank_statement = relationship("BankStatement", back_populates="transactions")
