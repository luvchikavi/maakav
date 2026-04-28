"""Financing, contractor, and milestones setup endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ....database import get_db
from ....models.user import User
from ....models.project import Project, ProjectFinancing, ContractorAgreement, Milestone
from ....schemas.setup import (
    FinancingUpdate, FinancingResponse,
    ContractorUpdate, ContractorResponse,
    MilestoneCreate, MilestoneUpdate, MilestoneResponse,
    SetupStatus,
)
from ....core.dependencies import get_current_user

router = APIRouter(tags=["setup"])


# === Financing ===

@router.get("/projects/{project_id}/setup/financing", response_model=FinancingResponse | None)
async def get_financing(project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify(project_id, user.firm_id, db)
    result = await db.execute(select(ProjectFinancing).where(ProjectFinancing.project_id == project_id))
    return result.scalar_one_or_none()


@router.put("/projects/{project_id}/setup/financing", response_model=FinancingResponse)
async def save_financing(project_id: int, body: FinancingUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify(project_id, user.firm_id, db)
    payload = body.model_dump(exclude_unset=True, mode="json")

    # Mirror the sum of guarantee_frameworks into credit_limit_guarantees so
    # downstream calculators that read the single number stay correct.
    if "guarantee_frameworks" in payload:
        items = payload.get("guarantee_frameworks") or []
        total = sum((float(it.get("amount") or 0) for it in items), 0.0)
        payload["credit_limit_guarantees"] = total

    result = await db.execute(select(ProjectFinancing).where(ProjectFinancing.project_id == project_id))
    fin = result.scalar_one_or_none()
    if fin:
        for field, value in payload.items():
            setattr(fin, field, value)
    else:
        fin = ProjectFinancing(project_id=project_id, **payload)
        db.add(fin)
    await db.commit()
    await db.refresh(fin)
    return fin


# === Contractor ===

@router.get("/projects/{project_id}/setup/contractor", response_model=ContractorResponse | None)
async def get_contractor(project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify(project_id, user.firm_id, db)
    result = await db.execute(select(ContractorAgreement).where(ContractorAgreement.project_id == project_id))
    return result.scalar_one_or_none()


@router.put("/projects/{project_id}/setup/contractor", response_model=ContractorResponse)
async def save_contractor(project_id: int, body: ContractorUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify(project_id, user.firm_id, db)
    result = await db.execute(select(ContractorAgreement).where(ContractorAgreement.project_id == project_id))
    con = result.scalar_one_or_none()
    if con:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(con, field, value)
    else:
        con = ContractorAgreement(project_id=project_id, **body.model_dump(exclude_unset=True))
        db.add(con)
    await db.commit()
    await db.refresh(con)
    return con


# === Milestones ===

@router.get("/projects/{project_id}/setup/milestones", response_model=list[MilestoneResponse])
async def list_milestones(project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify(project_id, user.firm_id, db)
    result = await db.execute(
        select(Milestone).where(Milestone.project_id == project_id).order_by(Milestone.display_order)
    )
    return result.scalars().all()


@router.post("/projects/{project_id}/setup/milestones", response_model=MilestoneResponse)
async def create_milestone(project_id: int, body: MilestoneCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify(project_id, user.firm_id, db)
    ms = Milestone(project_id=project_id, **body.model_dump())
    db.add(ms)
    await db.commit()
    await db.refresh(ms)
    return ms


@router.patch("/projects/{project_id}/setup/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(project_id: int, milestone_id: int, body: MilestoneUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify(project_id, user.firm_id, db)
    result = await db.execute(select(Milestone).where(Milestone.id == milestone_id, Milestone.project_id == project_id))
    ms = result.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="אבן הדרך לא נמצאה")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(ms, field, value)
    await db.commit()
    await db.refresh(ms)
    return ms


@router.delete("/projects/{project_id}/setup/milestones/{milestone_id}")
async def delete_milestone(project_id: int, milestone_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify(project_id, user.firm_id, db)
    result = await db.execute(select(Milestone).where(Milestone.id == milestone_id, Milestone.project_id == project_id))
    ms = result.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="אבן הדרך לא נמצאה")
    await db.delete(ms)
    await db.commit()
    return {"ok": True}


# === Setup Status ===

@router.get("/projects/{project_id}/setup/status", response_model=SetupStatus)
async def get_setup_status(project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify(project_id, user.firm_id, db)

    from ....models.budget import BudgetCategory, BudgetLineItem
    from ....models.apartment import Apartment
    from sqlalchemy import func

    budget_count = (await db.execute(
        select(func.count()).select_from(BudgetLineItem).join(BudgetCategory).where(BudgetCategory.project_id == project_id)
    )).scalar() or 0

    budget_total = (await db.execute(
        select(func.sum(BudgetCategory.total_amount)).where(BudgetCategory.project_id == project_id)
    )).scalar() or 0

    apt_count = (await db.execute(
        select(func.count()).select_from(Apartment).where(Apartment.project_id == project_id)
    )).scalar() or 0

    has_financing = (await db.execute(
        select(func.count()).select_from(ProjectFinancing).where(ProjectFinancing.project_id == project_id)
    )).scalar() or 0

    has_contractor = (await db.execute(
        select(func.count()).select_from(ContractorAgreement).where(ContractorAgreement.project_id == project_id)
    )).scalar() or 0

    has_milestones = (await db.execute(
        select(func.count()).select_from(Milestone).where(Milestone.project_id == project_id)
    )).scalar() or 0

    return SetupStatus(
        budget=budget_count > 0,
        apartments=apt_count > 0,
        financing=has_financing > 0,
        contractor=has_contractor > 0,
        milestones=has_milestones > 0,
        budget_items_count=budget_count,
        apartments_count=apt_count,
        total_budget=float(budget_total),
    )


async def _verify(project_id: int, firm_id: int, db: AsyncSession):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.firm_id == firm_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="הפרויקט לא נמצא")
