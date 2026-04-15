"""Analytics endpoints - exposure report + cashflow forecast."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ....database import get_db
from ....models.user import User
from ....models.project import Project
from ....models.monthly_report import MonthlyReport
from ....core.dependencies import get_current_user
from ....services.exposure_calculator import calculate_exposure
from ....services.cashflow_calculator import calculate_cashflow

router = APIRouter(tags=["analytics"])


@router.get("/projects/{project_id}/monthly-reports/{report_id}/exposure")
async def get_exposure(
    project_id: int,
    report_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get bank exposure report for a monthly report."""
    await _verify(project_id, report_id, user.firm_id, db)
    return await calculate_exposure(project_id, report_id, db)


@router.get("/projects/{project_id}/monthly-reports/{report_id}/cashflow")
async def get_cashflow(
    project_id: int,
    report_id: int,
    months: int = Query(6, ge=1, le=24),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get projected cashflow forecast for the next N months."""
    await _verify(project_id, report_id, user.firm_id, db)
    return await calculate_cashflow(project_id, report_id, months, db)


async def _verify(project_id: int, report_id: int, firm_id: int, db: AsyncSession):
    project = (await db.execute(
        select(Project).where(Project.id == project_id, Project.firm_id == firm_id)
    )).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="הפרויקט לא נמצא")

    report = (await db.execute(
        select(MonthlyReport).where(MonthlyReport.id == report_id, MonthlyReport.project_id == project_id)
    )).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="הדוח לא נמצא")
