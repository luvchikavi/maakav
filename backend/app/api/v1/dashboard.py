"""Dashboard API - KPIs across all projects for a firm."""

from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from ...database import get_db
from ...models.user import User
from ...models.project import Project
from ...models.apartment import Apartment, Ownership, UnitStatus
from ...models.sales import SalesContract
from ...models.monthly_report import MonthlyReport
from ...models.budget_tracking import BudgetTrackingSnapshot
from ...models.construction import ConstructionProgress
from ...core.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/kpis")
async def get_dashboard_kpis(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get KPIs across all projects for the firm."""

    # All active projects
    projects = (await db.execute(
        select(Project).where(Project.firm_id == user.firm_id, Project.is_active == True)
    )).scalars().all()

    project_ids = [p.id for p in projects]
    if not project_ids:
        return {"projects": [], "totals": _empty_totals()}

    # Per-project KPIs
    project_kpis = []
    total_units = 0
    total_sold = 0
    total_recognized = 0
    total_budget = Decimal("0")
    total_spent = Decimal("0")
    total_physical_sum = Decimal("0")
    projects_with_progress = 0

    for project in projects:
        # Latest report
        latest_report = (await db.execute(
            select(MonthlyReport)
            .where(MonthlyReport.project_id == project.id)
            .order_by(MonthlyReport.report_number.desc())
            .limit(1)
        )).scalar_one_or_none()

        # Developer units
        dev_units = (await db.execute(
            select(func.count()).select_from(Apartment).where(
                Apartment.project_id == project.id,
                Apartment.ownership == Ownership.DEVELOPER,
            )
        )).scalar() or 0

        # Sold
        sold = (await db.execute(
            select(func.count()).select_from(SalesContract).where(
                SalesContract.project_id == project.id,
            )
        )).scalar() or 0

        # Recognized (>15%)
        recognized = (await db.execute(
            select(func.count()).select_from(SalesContract).where(
                SalesContract.project_id == project.id,
                SalesContract.is_recognized_by_bank == True,
            )
        )).scalar() or 0

        # Budget tracking
        budget_pct = 0
        if latest_report:
            snapshot = (await db.execute(
                select(BudgetTrackingSnapshot).where(
                    BudgetTrackingSnapshot.monthly_report_id == latest_report.id
                )
            )).scalar_one_or_none()

            if snapshot:
                total_budget += snapshot.total_original_budget
                total_spent += snapshot.total_cumulative_paid
                if snapshot.total_original_budget > 0:
                    budget_pct = float(snapshot.total_cumulative_paid / snapshot.total_original_budget * 100)

        # Construction progress
        construction_pct = 0
        if latest_report:
            progress = (await db.execute(
                select(ConstructionProgress).where(
                    ConstructionProgress.monthly_report_id == latest_report.id
                )
            )).scalar_one_or_none()

            if progress:
                construction_pct = float(progress.overall_percent)
                total_physical_sum += progress.overall_percent
                projects_with_progress += 1

        sold_pct = round(sold / dev_units * 100, 1) if dev_units > 0 else 0
        recognized_pct = round(recognized / dev_units * 100, 1) if dev_units > 0 else 0

        total_units += dev_units
        total_sold += sold
        total_recognized += recognized

        project_kpis.append({
            "id": project.id,
            "name": project.project_name,
            "city": project.city,
            "phase": project.phase.value,
            "current_report": project.current_report_number,
            "units": dev_units,
            "sold": sold,
            "sold_percent": sold_pct,
            "recognized": recognized,
            "recognized_percent": recognized_pct,
            "budget_percent": round(budget_pct, 1),
            "construction_percent": round(construction_pct, 1),
        })

    avg_physical = float(total_physical_sum / projects_with_progress) if projects_with_progress > 0 else 0
    avg_budget = float(total_spent / total_budget * 100) if total_budget > 0 else 0

    return {
        "projects": project_kpis,
        "totals": {
            "active_projects": len(projects),
            "total_units": total_units,
            "total_sold": total_sold,
            "sold_percent": round(total_sold / total_units * 100, 1) if total_units > 0 else 0,
            "total_recognized": total_recognized,
            "recognized_percent": round(total_recognized / total_units * 100, 1) if total_units > 0 else 0,
            "avg_budget_percent": round(avg_budget, 1),
            "avg_construction_percent": round(avg_physical, 1),
        },
    }


def _empty_totals():
    return {
        "active_projects": 0, "total_units": 0, "total_sold": 0,
        "sold_percent": 0, "total_recognized": 0, "recognized_percent": 0,
        "avg_budget_percent": 0, "avg_construction_percent": 0,
    }
