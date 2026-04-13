"""
Sales Calculator Service - computes all sales metrics for the tracking report.

Calculates:
- Total sold / % sold
- Recognized sales (תקבולים >15% ממחיר)
- Quarterly sales pace
- Non-linear sales (תקבול אחרון >40%)
- Payment arrears (פיגורי רוכשים)
- Sales vs Report 0 comparison
"""

from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from ..models.apartment import Apartment, Ownership, UnitStatus
from ..models.sales import SalesContract, PaymentScheduleItem, PaymentStatus
from ..models.bank_statement import BankTransaction, TransactionCategory


async def calculate_sales(project_id: int, report_date: date, db: AsyncSession) -> dict:
    """Calculate all sales metrics for a project as of report_date."""

    # All developer apartments
    dev_apts = (await db.execute(
        select(Apartment).where(
            Apartment.project_id == project_id,
            Apartment.ownership == Ownership.DEVELOPER,
        )
    )).scalars().all()

    total_developer_units = len(dev_apts)

    # All sales contracts
    sales = (await db.execute(
        select(SalesContract)
        .options(selectinload(SalesContract.payment_schedule))
        .where(SalesContract.project_id == project_id)
    )).scalars().all()

    total_sold = len(sales)
    total_sales_value = sum(float(s.final_price_no_vat) for s in sales)

    # Recognized by bank: cumulative payments >= 15% of price
    recognized = 0
    non_linear = 0
    arrears = []

    for sale in sales:
        paid_payments = [p for p in sale.payment_schedule if p.status == PaymentStatus.PAID]
        total_paid = sum(float(p.actual_amount or 0) for p in paid_payments)
        price = float(sale.final_price_no_vat)

        # Recognized: >15% paid
        if price > 0 and total_paid / price >= 0.15:
            recognized += 1
            sale.is_recognized_by_bank = True

        # Non-linear: last payment >40% of total
        if paid_payments:
            last_payment = max(paid_payments, key=lambda p: p.actual_date or date.min)
            if price > 0 and float(last_payment.actual_amount or 0) / price > 0.40:
                non_linear += 1
                sale.is_non_linear = True

        # Arrears: overdue payments
        overdue = [p for p in sale.payment_schedule
                   if p.status in (PaymentStatus.SCHEDULED, PaymentStatus.PARTIAL)
                   and p.scheduled_date and p.scheduled_date < report_date]
        if overdue:
            overdue_amount = sum(
                float(p.scheduled_amount) - float(p.actual_amount or 0) for p in overdue
            )
            if overdue_amount > 0:
                arrears.append({
                    "buyer_name": sale.buyer_name,
                    "apartment_id": sale.apartment_id,
                    "overdue_amount": overdue_amount,
                    "overdue_count": len(overdue),
                })

    # Quarterly pace
    quarterly_pace = _calculate_quarterly_pace(sales)

    # Sales vs Report 0
    report_0_comparison = []
    for sale in sales:
        apt = next((a for a in dev_apts if a.id == sale.apartment_id), None)
        if apt and apt.report_0_price_no_vat:
            diff = float(sale.final_price_no_vat) - float(apt.report_0_price_no_vat)
            report_0_comparison.append({
                "apartment_id": apt.id,
                "unit_number": apt.unit_number,
                "building": apt.building_number,
                "buyer_name": sale.buyer_name,
                "contract_date": str(sale.contract_date),
                "sale_price_no_vat": float(sale.final_price_no_vat),
                "report_0_price_no_vat": float(apt.report_0_price_no_vat),
                "difference": diff,
            })

    await db.commit()

    return {
        "total_developer_units": total_developer_units,
        "total_sold": total_sold,
        "sold_percent": round(total_sold / total_developer_units * 100, 1) if total_developer_units > 0 else 0,
        "total_sales_value_no_vat": total_sales_value,
        "recognized_by_bank": recognized,
        "recognized_percent": round(recognized / total_developer_units * 100, 1) if total_developer_units > 0 else 0,
        "unsold": total_developer_units - total_sold,
        "non_linear_count": non_linear,
        "quarterly_pace": quarterly_pace,
        "arrears": arrears,
        "arrears_total": sum(a["overdue_amount"] for a in arrears),
        "report_0_comparison": report_0_comparison,
    }


def _calculate_quarterly_pace(sales: list[SalesContract]) -> list[dict]:
    """Calculate sales by quarter."""
    quarters: dict[str, dict] = {}

    for sale in sales:
        d = sale.contract_date
        q = (d.month - 1) // 3 + 1
        key = f"{d.year}-Q{q}"

        if key not in quarters:
            quarters[key] = {"quarter": key, "sold": 0, "cancelled": 0, "net": 0}

        quarters[key]["sold"] += 1
        quarters[key]["net"] += 1

    return sorted(quarters.values(), key=lambda x: x["quarter"])
