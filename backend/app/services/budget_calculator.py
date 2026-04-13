"""
Budget Calculator Service - generates the 15-column budget tracking table (נספח א').

Wires together:
- T1 (original budget) from BudgetLineItem
- T2 (budget transfers) - manual adjustments
- K (monthly paid) from classified bank transactions
- F, J (previous cumulative) from previous month's snapshot
- Index values from MonthlyReport + Project

Then calls BudgetTrackingLine.calculate_all() to compute all derived columns.
"""

from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..models.project import Project
from ..models.monthly_report import MonthlyReport
from ..models.budget import BudgetCategory, BudgetLineItem, CategoryType
from ..models.budget_tracking import BudgetTrackingSnapshot, BudgetTrackingLine
from ..models.bank_statement import BankTransaction, TransactionCategory

# Map bank transaction categories → budget tracking categories
TX_TO_BUDGET_MAP = {
    TransactionCategory.TENANT_EXPENSES: "tenant_expenses",
    TransactionCategory.LAND_AND_TAXES: "land_and_taxes",
    TransactionCategory.INDIRECT_COSTS: "indirect_costs",
    TransactionCategory.DIRECT_CONSTRUCTION: "direct_construction",
    TransactionCategory.DEPOSIT_TO_SAVINGS: "indirect_costs",
    TransactionCategory.OTHER_EXPENSE: "indirect_costs",
    TransactionCategory.INTEREST_AND_FEES: "indirect_costs",
    TransactionCategory.LOAN_REPAYMENT: "indirect_costs",
}

BUDGET_CATEGORIES_ORDER = [
    "tenant_expenses",
    "land_and_taxes",
    "indirect_costs",
    "direct_construction",
    "extraordinary",
]


async def calculate_budget_tracking(
    project_id: int,
    report_id: int,
    db: AsyncSession,
) -> BudgetTrackingSnapshot:
    """
    Generate or update the budget tracking snapshot for a monthly report.
    Returns the snapshot with all calculated lines.
    """
    # Load report and project
    report = (await db.execute(
        select(MonthlyReport).where(MonthlyReport.id == report_id)
    )).scalar_one()

    project = (await db.execute(
        select(Project).where(Project.id == project_id)
    )).scalar_one()

    base_index = project.base_index or Decimal("100")
    current_index = report.current_index or base_index

    # Get previous month's snapshot for carry-forward
    prev_snapshot = None
    if report.report_number > 1:
        prev_report = (await db.execute(
            select(MonthlyReport).where(
                MonthlyReport.project_id == project_id,
                MonthlyReport.report_number == report.report_number - 1,
            )
        )).scalar_one_or_none()

        if prev_report:
            prev_snapshot = (await db.execute(
                select(BudgetTrackingSnapshot).where(
                    BudgetTrackingSnapshot.monthly_report_id == prev_report.id
                )
            )).scalar_one_or_none()

    # Get T1 totals per category from Section 8 budget
    budget_totals = {}
    categories = (await db.execute(
        select(BudgetCategory).where(BudgetCategory.project_id == project_id)
    )).scalars().all()

    for cat in categories:
        budget_totals[cat.category_type.value] = cat.total_amount

    # Get K values (monthly paid) from classified bank transactions
    monthly_paid = {}
    tx_results = await db.execute(
        select(
            BankTransaction.category,
            func.sum(BankTransaction.amount),
        )
        .where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.transaction_type == "debit",
            BankTransaction.category.isnot(None),
        )
        .group_by(BankTransaction.category)
    )

    for tx_category, total in tx_results:
        budget_cat = TX_TO_BUDGET_MAP.get(tx_category)
        if budget_cat:
            monthly_paid[budget_cat] = monthly_paid.get(budget_cat, Decimal("0")) + (total or Decimal("0"))

    # Get previous month's line values for carry-forward
    prev_lines = {}
    if prev_snapshot:
        prev_line_results = (await db.execute(
            select(BudgetTrackingLine).where(
                BudgetTrackingLine.snapshot_id == prev_snapshot.id
            )
        )).scalars().all()

        for pl in prev_line_results:
            prev_lines[pl.category] = pl

    # Delete existing snapshot if any
    existing = (await db.execute(
        select(BudgetTrackingSnapshot).where(
            BudgetTrackingSnapshot.monthly_report_id == report_id
        )
    )).scalar_one_or_none()

    if existing:
        await db.execute(
            select(BudgetTrackingLine).where(BudgetTrackingLine.snapshot_id == existing.id)
        )
        # Delete lines first
        for line in (await db.execute(
            select(BudgetTrackingLine).where(BudgetTrackingLine.snapshot_id == existing.id)
        )).scalars().all():
            await db.delete(line)
        await db.delete(existing)
        await db.flush()

    # Create new snapshot
    snapshot = BudgetTrackingSnapshot(
        monthly_report_id=report_id,
        project_id=project_id,
        base_index=base_index,
        current_index=current_index,
    )
    db.add(snapshot)
    await db.flush()

    # Create line items for each budget category
    total_original = Decimal("0")
    total_monthly = Decimal("0")
    total_cumulative = Decimal("0")
    total_remaining = Decimal("0")

    for i, cat_key in enumerate(BUDGET_CATEGORIES_ORDER):
        t1 = budget_totals.get(cat_key, Decimal("0"))
        k = monthly_paid.get(cat_key, Decimal("0"))

        # Carry-forward from previous month
        prev = prev_lines.get(cat_key)
        f = prev.cumulative_base if prev else Decimal("0")       # Previous cumulative base
        j = prev.cumulative_actual if prev else Decimal("0")     # Previous cumulative actual

        line = BudgetTrackingLine(
            snapshot_id=snapshot.id,
            category=cat_key,
            display_order=i,
            is_index_linked=(cat_key != "extraordinary"),
            original_budget=t1,
            budget_transfer=Decimal("0"),  # TODO: from budget transfers
            cumulative_prev_base=f,
            cumulative_prev_actual=j,
            monthly_paid_actual=k,
        )

        # Calculate all derived columns
        line.calculate_all(base_index, current_index)

        db.add(line)

        total_original += t1
        total_monthly += k
        total_cumulative += line.cumulative_actual
        total_remaining += line.remaining_base

    # Update snapshot totals
    snapshot.total_original_budget = total_original
    snapshot.total_monthly_paid = total_monthly
    snapshot.total_cumulative_paid = total_cumulative
    snapshot.total_remaining = total_remaining

    await db.commit()

    # Reload with lines
    result = await db.execute(
        select(BudgetTrackingSnapshot).where(BudgetTrackingSnapshot.id == snapshot.id)
    )
    return result.scalar_one()
