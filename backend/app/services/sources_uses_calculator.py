"""
Sources & Uses Calculator (מקורות ושימושים).

Builds the balance sheet: all money in vs all money out.
"""

from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..models.monthly_report import MonthlyReport
from ..models.bank_statement import BankTransaction, TransactionType, TransactionCategory
from ..models.equity import EquityTracking
from ..models.sources_uses import SourcesUses


async def calculate_sources_uses(
    project_id: int,
    report_id: int,
    db: AsyncSession,
) -> SourcesUses:
    """Calculate sources & uses balance for a monthly report."""

    # Helper: sum transactions by categories
    async def sum_tx(categories: list, tx_type: str) -> Decimal:
        result = await db.execute(
            select(func.sum(BankTransaction.amount)).where(
                BankTransaction.project_id == project_id,
                BankTransaction.transaction_type == tx_type,
                BankTransaction.category.in_(categories),
            )
        )
        return result.scalar() or Decimal("0")

    # SOURCES (all cumulative - across all reports)
    # Equity
    equity = (await db.execute(
        select(EquityTracking).where(EquityTracking.monthly_report_id == report_id)
    )).scalar_one_or_none()
    source_equity = equity.current_balance if equity else Decimal("0")

    # Sales receipts (cumulative across all reports)
    source_sales = await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.project_id == project_id,
            BankTransaction.transaction_type == TransactionType.CREDIT,
            BankTransaction.category == TransactionCategory.SALE_INCOME,
        )
    )
    source_sales_val = source_sales.scalar() or Decimal("0")

    # Bank credit (loans received)
    source_credit = await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.project_id == project_id,
            BankTransaction.transaction_type == TransactionType.CREDIT,
            BankTransaction.category == TransactionCategory.LOAN_RECEIVED,
        )
    )
    source_credit_val = source_credit.scalar() or Decimal("0")

    # VAT refunds
    source_vat = await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.project_id == project_id,
            BankTransaction.transaction_type == TransactionType.CREDIT,
            BankTransaction.category == TransactionCategory.VAT_REFUNDS,
        )
    )
    source_vat_val = source_vat.scalar() or Decimal("0")

    total_sources = source_equity + source_sales_val + source_credit_val + source_vat_val

    # USES (all cumulative)
    # Payments (all expense categories)
    expense_cats = [
        TransactionCategory.TENANT_EXPENSES, TransactionCategory.LAND_AND_TAXES,
        TransactionCategory.INDIRECT_COSTS, TransactionCategory.DIRECT_CONSTRUCTION,
        TransactionCategory.DEPOSIT_TO_SAVINGS, TransactionCategory.OTHER_EXPENSE,
        TransactionCategory.INTEREST_AND_FEES,
    ]
    use_payments = await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.project_id == project_id,
            BankTransaction.transaction_type == TransactionType.DEBIT,
            BankTransaction.category.in_(expense_cats),
        )
    )
    use_payments_val = use_payments.scalar() or Decimal("0")

    # Loan repayments
    use_loan = await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.project_id == project_id,
            BankTransaction.transaction_type == TransactionType.DEBIT,
            BankTransaction.category == TransactionCategory.LOAN_REPAYMENT,
        )
    )
    use_loan_val = use_loan.scalar() or Decimal("0")

    total_uses = use_payments_val + use_loan_val
    balance = total_sources - total_uses

    # Upsert
    existing = (await db.execute(
        select(SourcesUses).where(SourcesUses.monthly_report_id == report_id)
    )).scalar_one_or_none()

    if existing:
        existing.source_equity = source_equity
        existing.source_sales_receipts = source_sales_val
        existing.source_bank_credit = source_credit_val
        existing.source_vat_refunds = source_vat_val
        existing.total_sources = total_sources
        existing.use_payments = use_payments_val
        existing.use_surplus_release = use_loan_val
        existing.total_uses = total_uses
        existing.balance = balance
        su = existing
    else:
        su = SourcesUses(
            monthly_report_id=report_id,
            project_id=project_id,
            source_equity=source_equity,
            source_sales_receipts=source_sales_val,
            source_bank_credit=source_credit_val,
            source_vat_refunds=source_vat_val,
            total_sources=total_sources,
            use_payments=use_payments_val,
            use_surplus_release=use_loan_val,
            total_uses=total_uses,
            balance=balance,
        )
        db.add(su)

    await db.commit()
    await db.refresh(su)
    return su
