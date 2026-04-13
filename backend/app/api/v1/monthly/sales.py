"""Sales entry and tracking endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ....database import get_db
from ....models.user import User
from ....models.project import Project
from ....models.apartment import Apartment, UnitStatus
from ....models.sales import SalesContract, PaymentScheduleItem
from ....schemas.monthly import SalesContractCreate, SalesContractResponse
from ....core.dependencies import get_current_user

router = APIRouter(tags=["sales"])


@router.get("/projects/{project_id}/sales", response_model=list[SalesContractResponse])
async def list_sales(project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify(project_id, user.firm_id, db)
    result = await db.execute(
        select(SalesContract)
        .where(SalesContract.project_id == project_id)
        .order_by(SalesContract.contract_date.desc())
    )
    return result.scalars().all()


@router.post("/projects/{project_id}/sales", response_model=SalesContractResponse)
async def create_sale(
    project_id: int,
    body: SalesContractCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify(project_id, user.firm_id, db)

    # Verify apartment exists and belongs to project
    apt = (await db.execute(
        select(Apartment).where(Apartment.id == body.apartment_id, Apartment.project_id == project_id)
    )).scalar_one_or_none()
    if not apt:
        raise HTTPException(status_code=404, detail="Apartment not found")

    # Check not already sold
    existing = (await db.execute(
        select(SalesContract).where(SalesContract.apartment_id == body.apartment_id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="דירה זו כבר נמכרה")

    contract = SalesContract(project_id=project_id, **body.model_dump())
    db.add(contract)

    # Update apartment status
    apt.unit_status = UnitStatus.SOLD

    await db.commit()
    await db.refresh(contract)
    return contract


@router.get("/projects/{project_id}/sales/summary")
async def sales_summary(project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get sales summary for dashboard/report."""
    await _verify(project_id, user.firm_id, db)

    # All apartments
    apts = (await db.execute(
        select(Apartment).where(Apartment.project_id == project_id)
    )).scalars().all()

    developer_apts = [a for a in apts if a.ownership.value == "developer"]
    total_developer = len(developer_apts)

    # Sales
    sales = (await db.execute(
        select(SalesContract).where(SalesContract.project_id == project_id)
    )).scalars().all()
    total_sold = len(sales)

    # Total values
    total_sales_value = sum(float(s.final_price_no_vat) for s in sales)
    recognized_count = sum(1 for s in sales if s.is_recognized_by_bank)

    return {
        "total_units_developer": total_developer,
        "total_units_all": len(apts),
        "total_sold": total_sold,
        "sold_percent": round(total_sold / total_developer * 100, 1) if total_developer > 0 else 0,
        "total_sales_value_no_vat": total_sales_value,
        "recognized_by_bank": recognized_count,
        "recognized_percent": round(recognized_count / total_developer * 100, 1) if total_developer > 0 else 0,
        "unsold": total_developer - total_sold,
    }


async def _verify(project_id: int, firm_id: int, db: AsyncSession):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.firm_id == firm_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
