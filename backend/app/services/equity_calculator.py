"""
Equity Calculator Service (הון עצמי).

Extracts equity deposits/withdrawals from bank transactions,
calculates cumulative balance, compares to required amount.
"""

from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..models.project import Project, ProjectFinancing
from ..models.monthly_report import MonthlyReport
from ..models.bank_statement import BankTransaction, TransactionCategory, TransactionType
from ..models.equity import EquityTracking


async def calculate_equity(
    project_id: int,
    report_id: int,
    db: AsyncSession,
) -> EquityTracking:
    """Calculate equity tracking for a monthly report."""

    report = (await db.execute(
        select(MonthlyReport).where(MonthlyReport.id == report_id)
    )).scalar_one()

    # Get required equity from financing terms
    financing = (await db.execute(
        select(ProjectFinancing).where(ProjectFinancing.project_id == project_id)
    )).scalar_one_or_none()

    required = financing.equity_required_amount if financing else Decimal("0")

    # Get equity deposits (credit transactions classified as equity)
    deposits = (await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.category == TransactionCategory.EQUITY_DEPOSIT,
            BankTransaction.transaction_type == TransactionType.CREDIT,
        )
    )).scalar() or Decimal("0")

    # Get equity withdrawals (debit transactions classified as equity - rare but happens)
    withdrawals = (await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.category == TransactionCategory.EQUITY_DEPOSIT,
            BankTransaction.transaction_type == TransactionType.DEBIT,
        )
    )).scalar() or Decimal("0")

    # Get previous cumulative
    prev_balance = Decimal("0")
    if report.report_number > 1:
        prev_report = (await db.execute(
            select(MonthlyReport).where(
                MonthlyReport.project_id == project_id,
                MonthlyReport.report_number == report.report_number - 1,
            )
        )).scalar_one_or_none()

        if prev_report:
            prev_equity = (await db.execute(
                select(EquityTracking).where(EquityTracking.monthly_report_id == prev_report.id)
            )).scalar_one_or_none()
            if prev_equity:
                prev_balance = prev_equity.current_balance

    current_balance = prev_balance + deposits - withdrawals
    gap = current_balance - required

    # Upsert
    existing = (await db.execute(
        select(EquityTracking).where(EquityTracking.monthly_report_id == report_id)
    )).scalar_one_or_none()

    if existing:
        existing.required_amount = required
        existing.total_deposits = prev_balance + deposits
        existing.total_withdrawals = withdrawals
        existing.current_balance = current_balance
        existing.gap = gap
        equity = existing
    else:
        equity = EquityTracking(
            monthly_report_id=report_id,
            project_id=project_id,
            required_amount=required,
            total_deposits=prev_balance + deposits,
            total_withdrawals=withdrawals,
            current_balance=current_balance,
            gap=gap,
        )
        db.add(equity)

    await db.commit()
    await db.refresh(equity)
    return equity
