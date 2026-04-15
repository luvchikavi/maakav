"""
Exposure Calculator Service (דוח חשיפה).

Calculates the bank's exposure to the project:
- % apartments sold
- % construction progress
- Credit used vs limit
- Net exposure = credit used - (receipts + equity)
"""

from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..models.project import Project, ProjectFinancing
from ..models.apartment import Apartment, Ownership, UnitStatus
from ..models.monthly_report import MonthlyReport
from ..models.construction import ConstructionProgress
from ..models.bank_statement import BankTransaction, TransactionCategory, TransactionType
from ..models.equity import EquityTracking


async def calculate_exposure(
    project_id: int,
    report_id: int,
    db: AsyncSession,
) -> dict:
    """Calculate bank exposure metrics for a monthly report."""

    report = (await db.execute(
        select(MonthlyReport).where(MonthlyReport.id == report_id)
    )).scalar_one()

    # Financing terms
    financing = (await db.execute(
        select(ProjectFinancing).where(ProjectFinancing.project_id == project_id)
    )).scalar_one_or_none()

    credit_limit = float(financing.credit_limit_total) if financing and financing.credit_limit_total else 0

    # Credit used = total loan received - total loan repayments (from all reports up to this one)
    loan_received = float((await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.project_id == project_id,
            BankTransaction.category == TransactionCategory.LOAN_RECEIVED,
            BankTransaction.transaction_type == TransactionType.CREDIT,
        )
    )).scalar() or 0)

    loan_repaid = float((await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.project_id == project_id,
            BankTransaction.category == TransactionCategory.LOAN_REPAYMENT,
            BankTransaction.transaction_type == TransactionType.DEBIT,
        )
    )).scalar() or 0)

    credit_used = loan_received - loan_repaid

    # Sales %
    dev_count = (await db.execute(
        select(func.count()).where(
            Apartment.project_id == project_id,
            Apartment.ownership == Ownership.DEVELOPER,
        )
    )).scalar() or 0

    sold_count = (await db.execute(
        select(func.count()).where(
            Apartment.project_id == project_id,
            Apartment.ownership == Ownership.DEVELOPER,
            Apartment.unit_status == UnitStatus.SOLD,
        )
    )).scalar() or 0

    sales_pct = round(sold_count / dev_count * 100, 1) if dev_count > 0 else 0

    # Construction %
    construction = (await db.execute(
        select(ConstructionProgress).where(ConstructionProgress.monthly_report_id == report_id)
    )).scalar_one_or_none()
    construction_pct = float(construction.overall_percent) if construction else 0

    # Total receipts (cumulative sale income)
    total_receipts = float((await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.project_id == project_id,
            BankTransaction.category == TransactionCategory.SALE_INCOME,
            BankTransaction.transaction_type == TransactionType.CREDIT,
        )
    )).scalar() or 0)

    # Equity balance
    equity = (await db.execute(
        select(EquityTracking).where(EquityTracking.monthly_report_id == report_id)
    )).scalar_one_or_none()
    equity_balance = float(equity.current_balance) if equity else 0

    # Exposure calculation
    credit_utilization_pct = round(credit_used / credit_limit * 100, 1) if credit_limit > 0 else 0
    net_exposure = credit_used - total_receipts - equity_balance

    return {
        "report_number": report.report_number,
        "report_month": str(report.report_month),
        "sales_percent": sales_pct,
        "sold_count": sold_count,
        "total_developer_units": dev_count,
        "construction_percent": construction_pct,
        "credit_limit": credit_limit,
        "credit_used": credit_used,
        "credit_utilization_percent": credit_utilization_pct,
        "total_receipts": total_receipts,
        "equity_balance": equity_balance,
        "net_exposure": net_exposure,
    }
