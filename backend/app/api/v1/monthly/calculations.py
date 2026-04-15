"""
Calculation endpoint - runs all calculators and returns combined results.
This is called from the Review step (step 6) of the monthly wizard.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ....database import get_db
from ....models.user import User
from ....models.project import Project
from ....models.monthly_report import MonthlyReport
from ....models.budget_tracking import BudgetTrackingSnapshot, BudgetTrackingLine
from ....models.construction import ConstructionProgress
from ....models.guarantee import GuaranteeSnapshot
from ....core.dependencies import get_current_user
from decimal import Decimal
from sqlalchemy import func
from ....services.budget_calculator import calculate_budget_tracking
from ....services.sales_calculator import calculate_sales
from ....services.vat_calculator import calculate_vat
from ....services.equity_calculator import calculate_equity
from ....services.profitability_calculator import calculate_profitability
from ....services.sources_uses_calculator import calculate_sources_uses

router = APIRouter(tags=["calculations"])


@router.post("/projects/{project_id}/monthly-reports/{report_id}/calculate")
async def run_calculations(
    project_id: int,
    report_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run all calculations for a monthly report.
    Returns the complete data needed for the review step and report generation.
    """
    await _verify_project(project_id, user.firm_id, db)

    report = (await db.execute(
        select(MonthlyReport).where(MonthlyReport.id == report_id, MonthlyReport.project_id == project_id)
    )).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="הדוח לא נמצא")

    results = {}
    errors = []

    # 1. Budget tracking (נספח א')
    try:
        budget_snapshot = await calculate_budget_tracking(project_id, report_id, db)
        # Reload with lines
        budget_lines = (await db.execute(
            select(BudgetTrackingLine)
            .where(BudgetTrackingLine.snapshot_id == budget_snapshot.id)
            .order_by(BudgetTrackingLine.display_order)
        )).scalars().all()

        results["budget_tracking"] = {
            "base_index": str(budget_snapshot.base_index),
            "current_index": str(budget_snapshot.current_index),
            "total_original_budget": str(budget_snapshot.total_original_budget),
            "total_monthly_paid": str(budget_snapshot.total_monthly_paid),
            "total_cumulative_paid": str(budget_snapshot.total_cumulative_paid),
            "total_remaining": str(budget_snapshot.total_remaining),
            "lines": [
                {
                    "category": line.category,
                    "original_budget": str(line.original_budget),
                    "budget_transfer": str(line.budget_transfer),
                    "adjusted_indexed": str(line.adjusted_indexed),
                    "monthly_paid_actual": str(line.monthly_paid_actual),
                    "cumulative_actual": str(line.cumulative_actual),
                    "remaining_base": str(line.remaining_base),
                    "remaining_indexed": str(line.remaining_indexed),
                    "total_indexed": str(line.total_indexed),
                    "execution_percent": str(line.execution_percent),
                }
                for line in budget_lines
            ],
        }
    except Exception as e:
        errors.append(f"Budget calculation error: {str(e)}")

    # 2. Sales
    try:
        sales_data = await calculate_sales(project_id, report.report_month, db)
        results["sales"] = sales_data
    except Exception as e:
        errors.append(f"Sales calculation error: {str(e)}")

    # 3. VAT
    try:
        vat = await calculate_vat(project_id, report_id, db)
        results["vat"] = {
            "transactions_total": str(vat.transactions_total),
            "output_vat": str(vat.output_vat),
            "inputs_total": str(vat.inputs_total),
            "input_vat": str(vat.input_vat),
            "vat_balance": str(vat.vat_balance),
            "cumulative_vat_balance": str(vat.cumulative_vat_balance),
        }
    except Exception as e:
        errors.append(f"VAT calculation error: {str(e)}")

    # 4. Equity
    try:
        equity = await calculate_equity(project_id, report_id, db)
        results["equity"] = {
            "required_amount": str(equity.required_amount),
            "total_deposits": str(equity.total_deposits),
            "total_withdrawals": str(equity.total_withdrawals),
            "current_balance": str(equity.current_balance),
            "gap": str(equity.gap),
        }
    except Exception as e:
        errors.append(f"Equity calculation error: {str(e)}")

    # 5. Profitability
    try:
        prof = await calculate_profitability(project_id, report_id, db)
        results["profitability"] = {
            "income_report_0": str(prof.income_report_0),
            "cost_report_0": str(prof.cost_report_0),
            "profit_report_0": str(prof.profit_report_0),
            "profit_percent_report_0": str(prof.profit_percent_report_0),
            "income_current": str(prof.income_current),
            "cost_current": str(prof.cost_current),
            "profit_current": str(prof.profit_current),
            "profit_percent_current": str(prof.profit_percent_current),
        }
    except Exception as e:
        errors.append(f"Profitability calculation error: {str(e)}")

    # 6. Sources & Uses
    try:
        su = await calculate_sources_uses(project_id, report_id, db)
        results["sources_uses"] = {
            "source_equity": str(su.source_equity),
            "source_sales_receipts": str(su.source_sales_receipts),
            "source_bank_credit": str(su.source_bank_credit),
            "source_vat_refunds": str(su.source_vat_refunds),
            "total_sources": str(su.total_sources),
            "use_payments": str(su.use_payments),
            "use_surplus_release": str(su.use_surplus_release),
            "total_uses": str(su.total_uses),
            "balance": str(su.balance),
        }
    except Exception as e:
        errors.append(f"Sources & uses calculation error: {str(e)}")

    # 7. Construction progress (already entered, just include)
    try:
        construction = (await db.execute(
            select(ConstructionProgress).where(ConstructionProgress.monthly_report_id == report_id)
        )).scalar_one_or_none()

        if construction:
            results["construction"] = {
                "overall_percent": str(construction.overall_percent),
                "monthly_delta_percent": str(construction.monthly_delta_percent),
                "description_text": construction.description_text,
            }
    except Exception as e:
        errors.append(f"Construction data error: {str(e)}")

    # 8. Milestones
    try:
        from ....models.project import Milestone
        milestones = (await db.execute(
            select(Milestone).where(Milestone.project_id == project_id)
            .order_by(Milestone.display_order)
        )).scalars().all()
        if milestones:
            results["milestones"] = [
                {
                    "name": m.name,
                    "planned_date": str(m.planned_date) if m.planned_date else None,
                    "actual_date": str(m.actual_date) if m.actual_date else None,
                    "is_completed": m.actual_date is not None,
                }
                for m in milestones
            ]
    except Exception as e:
        errors.append(f"Milestones error: {str(e)}")

    # 9. Guarantees
    try:
        guarantee = (await db.execute(
            select(GuaranteeSnapshot).where(GuaranteeSnapshot.monthly_report_id == report_id)
        )).scalar_one_or_none()
        if guarantee:
            results["guarantees"] = {
                "items": guarantee.items or [],
                "total_balance": float(guarantee.total_balance),
                "total_receipts": float(guarantee.total_receipts),
                "gap": float(guarantee.gap),
            }
    except Exception as e:
        errors.append(f"Guarantees error: {str(e)}")

    # 10. Equity detail (per-report history)
    try:
        from ....models.equity import EquityTracking
        equity_history = (await db.execute(
            select(EquityTracking, MonthlyReport.report_number)
            .join(MonthlyReport, MonthlyReport.id == EquityTracking.monthly_report_id)
            .where(EquityTracking.project_id == project_id)
            .order_by(MonthlyReport.report_number)
        )).all()
        if equity_history:
            results.setdefault("equity", {})["history"] = [
                {
                    "report_number": row.report_number,
                    "deposits": str(row.EquityTracking.total_deposits),
                    "withdrawals": str(row.EquityTracking.total_withdrawals),
                    "balance": str(row.EquityTracking.current_balance),
                }
                for row in equity_history
            ]
    except Exception as e:
        errors.append(f"Equity history error: {str(e)}")

    # 11. Form 50 + Surplus release
    results["form_50"] = {
        "form_50_number": report.form_50_number,
        "form_50_valid_until": str(report.form_50_valid_until) if report.form_50_valid_until else None,
        "surplus_release_amount": str(report.surplus_release_amount) if report.surplus_release_amount else None,
    }

    # 12. VAT history (all months)
    try:
        from ....models.vat import VatTracking
        vat_history = (await db.execute(
            select(VatTracking, MonthlyReport.report_month, MonthlyReport.report_number)
            .join(MonthlyReport, MonthlyReport.id == VatTracking.monthly_report_id)
            .where(VatTracking.project_id == project_id)
            .order_by(MonthlyReport.report_month)
        )).all()
        if vat_history:
            results["vat_history"] = [
                {
                    "month": str(row.report_month),
                    "report_number": row.report_number,
                    "transactions_total": str(row.VatTracking.transactions_total),
                    "output_vat": str(row.VatTracking.output_vat),
                    "inputs_total": str(row.VatTracking.inputs_total),
                    "input_vat": str(row.VatTracking.input_vat),
                    "vat_balance": str(row.VatTracking.vat_balance),
                    "cumulative_vat_balance": str(row.VatTracking.cumulative_vat_balance),
                }
                for row in vat_history
            ]
    except Exception as e:
        errors.append(f"VAT history error: {str(e)}")

    # 13. Expense forecast (next month) — pending payments from budget
    try:
        from ....models.sales import PaymentScheduleItem, PaymentStatus, SalesContract
        from datetime import timedelta
        next_month_start = report.report_month.replace(day=1)
        if next_month_start.month == 12:
            next_month_end = next_month_start.replace(year=next_month_start.year + 1, month=1, day=28)
        else:
            next_month_end = next_month_start.replace(month=next_month_start.month + 1, day=28)

        # Get budget remaining from latest snapshot
        budget_remaining = Decimal("0")
        if "budget_tracking" in results:
            budget_remaining = Decimal(str(results["budget_tracking"].get("total_remaining", "0")))

        # Estimate monthly construction spend (remaining / estimated months to completion)
        construction_pct = Decimal("0")
        if "construction" in results:
            construction_pct = Decimal(str(results["construction"].get("overall_percent", "0")))
        remaining_pct = max(Decimal("1"), Decimal("100") - construction_pct)
        # Rough: how much budget per 1% of progress
        est_monthly_construction = (budget_remaining / remaining_pct) * Decimal("3") if remaining_pct > 0 else Decimal("0")

        # Expected receipts next month
        expected_receipts = (await db.execute(
            select(func.sum(PaymentScheduleItem.scheduled_amount))
            .join(SalesContract, SalesContract.id == PaymentScheduleItem.contract_id)
            .where(
                SalesContract.project_id == project_id,
                PaymentScheduleItem.status.in_([PaymentStatus.SCHEDULED, PaymentStatus.PARTIAL]),
                PaymentScheduleItem.scheduled_date >= next_month_start,
                PaymentScheduleItem.scheduled_date <= next_month_end,
            )
        )).scalar() or Decimal("0")

        results["expense_forecast"] = {
            "budget_remaining": str(budget_remaining),
            "estimated_monthly_expense": str(round(est_monthly_construction, 0)),
            "expected_receipts_next_month": str(expected_receipts),
            "construction_percent": str(construction_pct),
        }
    except Exception as e:
        errors.append(f"Expense forecast error: {str(e)}")

    # Update report status
    if not errors:
        report.status = "review"
    await db.commit()

    return {
        "success": len(errors) == 0,
        "report_number": report.report_number,
        "report_month": str(report.report_month),
        "results": results,
        "errors": errors,
    }


async def _verify_project(project_id: int, firm_id: int, db: AsyncSession):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.firm_id == firm_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="הפרויקט לא נמצא")
