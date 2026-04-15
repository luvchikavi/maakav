"""Report generation endpoint - produces Word/PDF document for download."""

import io
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ....database import get_db
from ....models.user import User
from ....models.project import Project, Milestone
from ....models.monthly_report import MonthlyReport
from ....models.guarantee import GuaranteeSnapshot
from ....models.equity import EquityTracking
from ....core.dependencies import get_current_user
from ....services.budget_calculator import calculate_budget_tracking
from ....services.sales_calculator import calculate_sales
from ....services.vat_calculator import calculate_vat
from ....services.equity_calculator import calculate_equity
from ....services.profitability_calculator import calculate_profitability
from ....services.sources_uses_calculator import calculate_sources_uses
from ....services.pdf_converter import convert_docx_to_pdf, is_pdf_available
from ....models.construction import ConstructionProgress
from ....models.budget_tracking import BudgetTrackingSnapshot, BudgetTrackingLine
from ....report_templates.tracking_report import generate_tracking_report

router = APIRouter(tags=["generation"])


@router.get("/reports/pdf-available")
async def check_pdf_available():
    """Check if PDF conversion is available on this server."""
    return {"available": is_pdf_available()}


@router.post("/projects/{project_id}/monthly-reports/{report_id}/generate")
async def generate_report(
    project_id: int,
    report_id: int,
    format: str = Query("docx", description="Output format: docx or pdf"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate Word or PDF document for a monthly tracking report."""
    project = await _verify_project(project_id, user.firm_id, db)

    report = (await db.execute(
        select(MonthlyReport).where(MonthlyReport.id == report_id, MonthlyReport.project_id == project_id)
    )).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="הדוח לא נמצא")

    # Run all calculations
    calc_results = {}

    try:
        # Budget
        snapshot = await calculate_budget_tracking(project_id, report_id, db)
        lines = (await db.execute(
            select(BudgetTrackingLine).where(BudgetTrackingLine.snapshot_id == snapshot.id).order_by(BudgetTrackingLine.display_order)
        )).scalars().all()
        calc_results["budget_tracking"] = {
            "base_index": str(snapshot.base_index),
            "current_index": str(snapshot.current_index),
            "lines": [
                {
                    "category": l.category,
                    "original_budget": str(l.original_budget),
                    "budget_transfer": str(l.budget_transfer),
                    "adjusted_indexed": str(l.adjusted_indexed),
                    "monthly_paid_actual": str(l.monthly_paid_actual),
                    "cumulative_actual": str(l.cumulative_actual),
                    "remaining_base": str(l.remaining_base),
                    "remaining_indexed": str(l.remaining_indexed),
                    "total_indexed": str(l.total_indexed),
                    "execution_percent": str(l.execution_percent),
                }
                for l in lines
            ],
        }

        # Sales
        calc_results["sales"] = await calculate_sales(project_id, report.report_month, db)

        # VAT
        vat = await calculate_vat(project_id, report_id, db)
        calc_results["vat"] = {k: str(v) for k, v in {
            "transactions_total": vat.transactions_total, "output_vat": vat.output_vat,
            "inputs_total": vat.inputs_total, "input_vat": vat.input_vat,
            "vat_balance": vat.vat_balance, "cumulative_vat_balance": vat.cumulative_vat_balance,
        }.items()}

        # Equity
        eq = await calculate_equity(project_id, report_id, db)
        calc_results["equity"] = {k: str(v) for k, v in {
            "required_amount": eq.required_amount, "total_deposits": eq.total_deposits,
            "total_withdrawals": eq.total_withdrawals, "current_balance": eq.current_balance, "gap": eq.gap,
        }.items()}

        # Equity history
        equity_history = (await db.execute(
            select(EquityTracking, MonthlyReport.report_number)
            .join(MonthlyReport, MonthlyReport.id == EquityTracking.monthly_report_id)
            .where(EquityTracking.project_id == project_id)
            .order_by(MonthlyReport.report_number)
        )).all()
        if equity_history:
            calc_results["equity"]["history"] = [
                {
                    "report_number": row.report_number,
                    "deposits": str(row.EquityTracking.total_deposits),
                    "withdrawals": str(row.EquityTracking.total_withdrawals),
                    "balance": str(row.EquityTracking.current_balance),
                }
                for row in equity_history
            ]

        # Profitability
        prof = await calculate_profitability(project_id, report_id, db)
        calc_results["profitability"] = {k: str(v) for k, v in {
            "income_report_0": prof.income_report_0, "cost_report_0": prof.cost_report_0,
            "profit_report_0": prof.profit_report_0, "profit_percent_report_0": prof.profit_percent_report_0,
            "income_current": prof.income_current, "cost_current": prof.cost_current,
            "profit_current": prof.profit_current, "profit_percent_current": prof.profit_percent_current,
        }.items()}

        # Sources & Uses
        su = await calculate_sources_uses(project_id, report_id, db)
        calc_results["sources_uses"] = {k: str(v) for k, v in {
            "source_equity": su.source_equity, "source_sales_receipts": su.source_sales_receipts,
            "source_bank_credit": su.source_bank_credit, "source_vat_refunds": su.source_vat_refunds,
            "total_sources": su.total_sources, "use_payments": su.use_payments,
            "use_surplus_release": su.use_surplus_release, "total_uses": su.total_uses, "balance": su.balance,
        }.items()}

        # Construction
        construction = (await db.execute(
            select(ConstructionProgress).where(ConstructionProgress.monthly_report_id == report_id)
        )).scalar_one_or_none()
        if construction:
            calc_results["construction"] = {
                "overall_percent": str(construction.overall_percent),
                "monthly_delta_percent": str(construction.monthly_delta_percent),
                "description_text": construction.description_text or "",
            }

        # Milestones
        milestones = (await db.execute(
            select(Milestone).where(Milestone.project_id == project_id).order_by(Milestone.display_order)
        )).scalars().all()
        if milestones:
            calc_results["milestones"] = [
                {
                    "name": m.name,
                    "planned_date": str(m.planned_date) if m.planned_date else None,
                    "actual_date": str(m.actual_date) if m.actual_date else None,
                    "is_completed": m.actual_date is not None,
                }
                for m in milestones
            ]

        # Guarantees
        guarantee = (await db.execute(
            select(GuaranteeSnapshot).where(GuaranteeSnapshot.monthly_report_id == report_id)
        )).scalar_one_or_none()
        if guarantee:
            calc_results["guarantees"] = {
                "items": guarantee.items or [],
                "total_balance": float(guarantee.total_balance),
                "total_receipts": float(guarantee.total_receipts),
                "gap": float(guarantee.gap),
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בחישוב: {str(e)}")

    # Generate Word document
    project_data = {
        "project_name": project.project_name,
        "address": project.address,
        "city": project.city,
        "developer_name": project.developer_name,
        "bank": project.bank.value if project.bank else "",
    }
    report_data_dict = {
        "report_number": report.report_number,
        "report_month": str(report.report_month),
    }

    try:
        word_buffer = generate_tracking_report(project_data, report_data_dict, calc_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בהפקת דוח: {str(e)}")

    # Update report status
    report.status = "approved"
    await db.commit()

    # PDF conversion if requested
    if format == "pdf":
        docx_bytes = word_buffer.read()
        pdf_bytes = convert_docx_to_pdf(docx_bytes)
        if pdf_bytes is None:
            raise HTTPException(
                status_code=503,
                detail="המרה ל-PDF לא זמינה — LibreOffice לא מותקן. הורד כ-Word במקום.",
            )
        filename = f"tracking_report_{report.report_number}_{project.project_name}.pdf"
        encoded = quote(filename)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
        )

    # Default: Word
    filename = f"tracking_report_{report.report_number}_{project.project_name}.docx"
    encoded = quote(filename)
    return StreamingResponse(
        word_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


async def _verify_project(project_id: int, firm_id: int, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id, Project.firm_id == firm_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="הפרויקט לא נמצא")
    return project
