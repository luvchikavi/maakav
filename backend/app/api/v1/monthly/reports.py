"""Monthly report lifecycle endpoints."""

from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ....database import get_db
from ....models.user import User
from ....models.project import Project
from ....models.monthly_report import MonthlyReport, ReportStatus
from ....models.bank_statement import BankStatement, BankTransaction
from ....models.construction import ConstructionProgress
from ....schemas.monthly import MonthlyReportCreate, MonthlyReportResponse, DataCompleteness
from ....core.dependencies import get_current_user

router = APIRouter(tags=["monthly-reports"])


@router.get("/projects/{project_id}/monthly-reports", response_model=list[MonthlyReportResponse])
async def list_reports(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project(project_id, user.firm_id, db)
    result = await db.execute(
        select(MonthlyReport)
        .where(MonthlyReport.project_id == project_id)
        .order_by(MonthlyReport.report_number.desc())
    )
    return result.scalars().all()


@router.post("/projects/{project_id}/monthly-reports", response_model=MonthlyReportResponse)
async def create_report(
    project_id: int,
    body: MonthlyReportCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new monthly report. Auto-increments report number."""
    project = await _verify_project(project_id, user.firm_id, db)

    # Check for duplicate month
    existing = await db.execute(
        select(MonthlyReport).where(
            MonthlyReport.project_id == project_id,
            MonthlyReport.report_month == body.report_month,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="דוח לחודש זה כבר קיים")

    # Get next report number
    max_num = await db.execute(
        select(func.max(MonthlyReport.report_number)).where(MonthlyReport.project_id == project_id)
    )
    next_num = (max_num.scalar() or 0) + 1

    report = MonthlyReport(
        project_id=project_id,
        report_month=body.report_month,
        report_number=next_num,
        current_index=body.current_index,
        vat_rate=body.vat_rate,
        status=ReportStatus.DRAFT,
        created_by=user.id,
        data_completeness={},
    )
    db.add(report)

    # Update project's current report number
    project.current_report_number = next_num
    if project.phase == "setup":
        project.phase = "active"

    await db.commit()
    await db.refresh(report)
    return report


@router.get("/projects/{project_id}/monthly-reports/{report_id}", response_model=MonthlyReportResponse)
async def get_report(
    project_id: int,
    report_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project(project_id, user.firm_id, db)
    result = await db.execute(
        select(MonthlyReport).where(MonthlyReport.id == report_id, MonthlyReport.project_id == project_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="הדוח לא נמצא")
    return report


@router.get("/projects/{project_id}/monthly-reports/{report_id}/completeness", response_model=DataCompleteness)
async def check_completeness(
    project_id: int,
    report_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check what data is filled and what's missing for this monthly report."""
    await _verify_project(project_id, user.firm_id, db)

    report = (await db.execute(
        select(MonthlyReport).where(MonthlyReport.id == report_id)
    )).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="הדוח לא נמצא")

    # Check bank statement
    stmt_count = (await db.execute(
        select(func.count()).select_from(BankStatement).where(BankStatement.monthly_report_id == report_id)
    )).scalar() or 0

    # Check all transactions classified
    unclassified = (await db.execute(
        select(func.count()).select_from(BankTransaction).where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.category.is_(None),
        )
    )).scalar() or 0

    # Check construction progress
    has_construction = (await db.execute(
        select(func.count()).select_from(ConstructionProgress).where(ConstructionProgress.monthly_report_id == report_id)
    )).scalar() or 0

    # Check index
    index_updated = report.current_index is not None

    bank_uploaded = stmt_count > 0
    all_classified = bank_uploaded and unclassified == 0
    construction_entered = has_construction > 0

    missing = []
    if not bank_uploaded:
        missing.append("לא הועלה תדפיס בנק")
    if bank_uploaded and not all_classified:
        missing.append(f"{unclassified} תנועות טרם סווגו")
    if not construction_entered:
        missing.append("לא הוזנה התקדמות בנייה")
    if not index_updated:
        missing.append("לא עודכן מדד תשומות")

    ready = bank_uploaded and all_classified and construction_entered and index_updated

    return DataCompleteness(
        bank_statement_uploaded=bank_uploaded,
        all_transactions_classified=all_classified,
        construction_progress_entered=construction_entered,
        index_updated=index_updated,
        ready_to_generate=ready,
        missing_items=missing,
    )


@router.patch("/projects/{project_id}/monthly-reports/{report_id}/index")
async def update_index(
    project_id: int,
    report_id: int,
    current_index: Decimal,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the construction input index for this report."""
    await _verify_project(project_id, user.firm_id, db)
    report = (await db.execute(
        select(MonthlyReport).where(MonthlyReport.id == report_id)
    )).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="הדוח לא נמצא")
    report.current_index = current_index
    await db.commit()
    return {"ok": True, "current_index": str(current_index)}


async def _verify_project(project_id: int, firm_id: int, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.firm_id == firm_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="הפרויקט לא נמצא")
    return project
