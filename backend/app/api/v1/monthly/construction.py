"""Construction progress entry endpoints."""

from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ....database import get_db
from ....models.user import User
from ....models.project import Project
from ....models.monthly_report import MonthlyReport
from ....models.construction import ConstructionProgress
from ....schemas.monthly import ConstructionProgressUpdate, ConstructionProgressResponse
from ....core.dependencies import get_current_user

router = APIRouter(tags=["construction"])


@router.get("/projects/{project_id}/monthly-reports/{report_id}/construction", response_model=ConstructionProgressResponse | None)
async def get_construction(project_id: int, report_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify(project_id, user.firm_id, db)
    result = await db.execute(
        select(ConstructionProgress).where(ConstructionProgress.monthly_report_id == report_id)
    )
    return result.scalar_one_or_none()


@router.put("/projects/{project_id}/monthly-reports/{report_id}/construction", response_model=ConstructionProgressResponse)
async def save_construction(
    project_id: int, report_id: int,
    body: ConstructionProgressUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify(project_id, user.firm_id, db)

    # Get previous report's progress for delta calculation
    report = (await db.execute(select(MonthlyReport).where(MonthlyReport.id == report_id))).scalar_one()
    prev_percent = Decimal("0")
    if report.report_number > 1:
        prev_report = (await db.execute(
            select(MonthlyReport).where(
                MonthlyReport.project_id == project_id,
                MonthlyReport.report_number == report.report_number - 1,
            )
        )).scalar_one_or_none()
        if prev_report:
            prev_progress = (await db.execute(
                select(ConstructionProgress).where(ConstructionProgress.monthly_report_id == prev_report.id)
            )).scalar_one_or_none()
            if prev_progress:
                prev_percent = prev_progress.overall_percent

    result = await db.execute(
        select(ConstructionProgress).where(ConstructionProgress.monthly_report_id == report_id)
    )
    progress = result.scalar_one_or_none()

    delta = body.overall_percent - prev_percent

    if progress:
        progress.overall_percent = body.overall_percent
        progress.monthly_delta_percent = delta
        progress.description_text = body.description_text
        progress.visit_date = body.visit_date
        progress.visitor_name = body.visitor_name
    else:
        progress = ConstructionProgress(
            monthly_report_id=report_id,
            project_id=project_id,
            overall_percent=body.overall_percent,
            monthly_delta_percent=delta,
            description_text=body.description_text,
            visit_date=body.visit_date,
            visitor_name=body.visitor_name,
        )
        db.add(progress)

    await db.commit()
    await db.refresh(progress)
    return progress


async def _verify(project_id: int, firm_id: int, db: AsyncSession):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.firm_id == firm_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="הפרויקט לא נמצא")
