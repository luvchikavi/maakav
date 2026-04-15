"""
Cashflow Forecast Calculator (תזרים מזומנים).

Projects future income and expenses based on:
- Scheduled payment receipts from sales
- Remaining budget items to pay
- Known fixed costs (interest, fees)
"""

from decimal import Decimal
from datetime import date, timedelta
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..models.project import Project, ProjectFinancing
from ..models.sales import SalesContract, PaymentScheduleItem, PaymentStatus
from ..models.budget import BudgetCategory, BudgetLineItem
from ..models.budget_tracking import BudgetTrackingSnapshot, BudgetTrackingLine
from ..models.monthly_report import MonthlyReport
from ..models.bank_statement import BankTransaction, TransactionCategory, TransactionType


async def calculate_cashflow(
    project_id: int,
    report_id: int,
    months_ahead: int = 6,
    db: AsyncSession = None,
) -> dict:
    """
    Calculate projected cashflow for the next N months.

    Returns:
        {
            "months": [
                {
                    "month": "2026-05",
                    "projected_income": 500000,
                    "projected_expenses": 300000,
                    "net_flow": 200000,
                    "cumulative_balance": 200000,
                    "income_breakdown": { "sale_receipts": 400000, "other": 100000 },
                    "expense_breakdown": { "construction": 200000, "indirect": 100000 },
                }
            ],
            "summary": {
                "total_projected_income": 3000000,
                "total_projected_expenses": 1800000,
                "total_net_flow": 1200000,
            }
        }
    """
    report = (await db.execute(
        select(MonthlyReport).where(MonthlyReport.id == report_id)
    )).scalar_one()

    base_month = report.report_month

    # Scheduled future payments from sales
    future_payments = (await db.execute(
        select(PaymentScheduleItem)
        .join(SalesContract, SalesContract.id == PaymentScheduleItem.contract_id)
        .where(
            SalesContract.project_id == project_id,
            PaymentScheduleItem.status.in_([PaymentStatus.SCHEDULED, PaymentStatus.PARTIAL]),
            PaymentScheduleItem.scheduled_date >= base_month,
        )
        .order_by(PaymentScheduleItem.scheduled_date)
    )).scalars().all()

    # Current budget remaining (from latest snapshot)
    latest_snapshot = (await db.execute(
        select(BudgetTrackingSnapshot)
        .where(BudgetTrackingSnapshot.monthly_report_id == report_id)
    )).scalar_one_or_none()

    remaining_budget = Decimal("0")
    if latest_snapshot:
        remaining_budget = latest_snapshot.total_remaining or Decimal("0")

    # Financing info for interest projection
    financing = (await db.execute(
        select(ProjectFinancing).where(ProjectFinancing.project_id == project_id)
    )).scalar_one_or_none()

    monthly_interest = Decimal("0")
    if financing and financing.interest_rate and financing.credit_limit_total:
        # Rough monthly interest estimate
        monthly_interest = (financing.credit_limit_total * financing.interest_rate / 100) / 12

    # Current bank balance (closing balance from latest statement)
    current_balance = Decimal("0")
    latest_closing = (await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.project_id == project_id,
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.transaction_type == TransactionType.CREDIT,
        )
    )).scalar()
    latest_debits = (await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.project_id == project_id,
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.transaction_type == TransactionType.DEBIT,
        )
    )).scalar()
    current_balance = (latest_closing or Decimal("0")) - (latest_debits or Decimal("0"))

    # Build monthly projections
    months_data = []
    cumulative = float(current_balance)
    # Spread remaining budget evenly over projection period
    monthly_construction = float(remaining_budget) / months_ahead if months_ahead > 0 else 0

    # Group scheduled payments by month
    payments_by_month: dict[str, float] = defaultdict(float)
    for p in future_payments:
        key = p.scheduled_date.strftime("%Y-%m")
        remaining = float(p.scheduled_amount) - float(p.actual_amount or 0)
        if remaining > 0:
            payments_by_month[key] += remaining

    for i in range(months_ahead):
        # Calculate month date
        month_offset = base_month.month + i
        year = base_month.year + (month_offset - 1) // 12
        month = ((month_offset - 1) % 12) + 1
        month_key = f"{year}-{month:02d}"

        # Income: scheduled receipts
        sale_receipts = payments_by_month.get(month_key, 0)
        projected_income = sale_receipts

        # Expenses: construction + interest
        projected_expenses = monthly_construction + float(monthly_interest)

        net_flow = projected_income - projected_expenses
        cumulative += net_flow

        months_data.append({
            "month": month_key,
            "projected_income": round(projected_income),
            "projected_expenses": round(projected_expenses),
            "net_flow": round(net_flow),
            "cumulative_balance": round(cumulative),
            "income_breakdown": {
                "sale_receipts": round(sale_receipts),
            },
            "expense_breakdown": {
                "construction": round(monthly_construction),
                "interest": round(float(monthly_interest)),
            },
        })

    total_income = sum(m["projected_income"] for m in months_data)
    total_expenses = sum(m["projected_expenses"] for m in months_data)

    return {
        "months": months_data,
        "current_balance": round(float(current_balance)),
        "months_ahead": months_ahead,
        "summary": {
            "total_projected_income": total_income,
            "total_projected_expenses": total_expenses,
            "total_net_flow": total_income - total_expenses,
        },
    }
