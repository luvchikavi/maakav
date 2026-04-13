"""
Profitability Calculator Service (רווחיות).

Compares income vs costs, current vs Report 0.
"""

from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..models.project import Project
from ..models.monthly_report import MonthlyReport
from ..models.apartment import Apartment, Ownership
from ..models.sales import SalesContract
from ..models.budget import BudgetCategory
from ..models.budget_tracking import BudgetTrackingSnapshot, BudgetTrackingLine
from ..models.profitability import ProfitabilitySnapshot


async def calculate_profitability(
    project_id: int,
    report_id: int,
    db: AsyncSession,
) -> ProfitabilitySnapshot:
    """Calculate profitability snapshot for a monthly report."""

    # Report 0 values
    # Income from Report 0: sum of all developer apartment list prices
    report_0_income = (await db.execute(
        select(func.sum(Apartment.list_price_no_vat)).where(
            Apartment.project_id == project_id,
            Apartment.ownership == Ownership.DEVELOPER,
        )
    )).scalar() or Decimal("0")

    # Costs from Report 0: sum of all budget categories
    report_0_cost = (await db.execute(
        select(func.sum(BudgetCategory.total_amount)).where(
            BudgetCategory.project_id == project_id,
        )
    )).scalar() or Decimal("0")

    report_0_profit = report_0_income - report_0_cost
    report_0_percent = Decimal("0")
    if report_0_cost > 0:
        report_0_percent = (report_0_profit / report_0_cost * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    # Current values
    # Current income: sales receipts + unsold inventory value
    sales_value = (await db.execute(
        select(func.sum(SalesContract.final_price_no_vat)).where(
            SalesContract.project_id == project_id,
        )
    )).scalar() or Decimal("0")

    # Unsold inventory at list price
    sold_apt_ids = (await db.execute(
        select(SalesContract.apartment_id).where(SalesContract.project_id == project_id)
    )).scalars().all()

    unsold_value = (await db.execute(
        select(func.sum(Apartment.list_price_no_vat)).where(
            Apartment.project_id == project_id,
            Apartment.ownership == Ownership.DEVELOPER,
            ~Apartment.id.in_(sold_apt_ids) if sold_apt_ids else True,
        )
    )).scalar() or Decimal("0")

    current_income = sales_value + unsold_value

    # Current costs: from budget tracking (cumulative actual paid)
    snapshot = (await db.execute(
        select(BudgetTrackingSnapshot).where(
            BudgetTrackingSnapshot.monthly_report_id == report_id
        )
    )).scalar_one_or_none()

    current_cost = snapshot.total_cumulative_paid if snapshot else report_0_cost

    current_profit = current_income - current_cost
    current_percent = Decimal("0")
    if current_cost > 0:
        current_percent = (current_profit / current_cost * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    # Upsert
    existing = (await db.execute(
        select(ProfitabilitySnapshot).where(ProfitabilitySnapshot.monthly_report_id == report_id)
    )).scalar_one_or_none()

    if existing:
        existing.income_report_0 = report_0_income
        existing.cost_report_0 = report_0_cost
        existing.profit_report_0 = report_0_profit
        existing.profit_percent_report_0 = report_0_percent
        existing.income_current = current_income
        existing.cost_current = current_cost
        existing.profit_current = current_profit
        existing.profit_percent_current = current_percent
        prof = existing
    else:
        prof = ProfitabilitySnapshot(
            monthly_report_id=report_id,
            project_id=project_id,
            income_report_0=report_0_income,
            cost_report_0=report_0_cost,
            profit_report_0=report_0_profit,
            profit_percent_report_0=report_0_percent,
            income_current=current_income,
            cost_current=current_cost,
            profit_current=current_profit,
            profit_percent_current=current_percent,
        )
        db.add(prof)

    await db.commit()
    await db.refresh(prof)
    return prof
