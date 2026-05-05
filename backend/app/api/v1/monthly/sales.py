"""Sales entry and payment schedule endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from ....database import get_db
from ....models.user import User
from ....models.project import Project
from ....models.apartment import Apartment, UnitStatus
from ....models.sales import SalesContract, PaymentScheduleItem, PaymentStatus
from ....models.monthly_report import MonthlyReport
from ....schemas.monthly import (
    SalesContractCreate, SalesContractResponse,
    PaymentScheduleItemCreate, PaymentScheduleItemUpdate, PaymentScheduleItemResponse,
)
from ....core.dependencies import get_current_user

router = APIRouter(tags=["sales"])


# ── Sales Contracts ──────────────────────────────────────────


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
        raise HTTPException(status_code=404, detail="הדירה לא נמצאה")

    # Check not already sold
    existing = (await db.execute(
        select(SalesContract).where(SalesContract.apartment_id == body.apartment_id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="דירה זו כבר נמכרה")

    payload = body.model_dump()
    # If the caller didn't pass a vat_rate, snapshot it from the project's
    # most recent monthly report so retroactive rate changes don't distort
    # past sales.
    if payload.get("vat_rate") is None:
        latest_report = (await db.execute(
            select(MonthlyReport)
            .where(MonthlyReport.project_id == project_id)
            .order_by(MonthlyReport.report_number.desc())
            .limit(1)
        )).scalar_one_or_none()
        if latest_report is not None:
            payload["vat_rate"] = latest_report.vat_rate

    contract = SalesContract(project_id=project_id, **payload)
    db.add(contract)

    # Update apartment status
    apt.unit_status = UnitStatus.SOLD

    await db.commit()
    await db.refresh(contract)
    return contract


@router.delete("/projects/{project_id}/sales/{sale_id}")
async def delete_sale(
    project_id: int,
    sale_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify(project_id, user.firm_id, db)
    contract = (await db.execute(
        select(SalesContract).where(SalesContract.id == sale_id, SalesContract.project_id == project_id)
    )).scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="המכירה לא נמצאה")

    # Restore apartment status
    apt = (await db.execute(
        select(Apartment).where(Apartment.id == contract.apartment_id)
    )).scalar_one_or_none()
    if apt:
        apt.unit_status = UnitStatus.FOR_SALE

    # Delete payment schedule items first
    items = (await db.execute(
        select(PaymentScheduleItem).where(PaymentScheduleItem.contract_id == sale_id)
    )).scalars().all()
    for item in items:
        await db.delete(item)

    await db.delete(contract)
    await db.commit()
    return {"ok": True}


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


# ── Unsold Apartments (for dropdown) ──────────────────────────


@router.get("/projects/{project_id}/apartments/unsold")
async def list_unsold_apartments(
    project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """List unsold developer apartments for sale entry dropdown."""
    await _verify(project_id, user.firm_id, db)
    result = await db.execute(
        select(Apartment)
        .where(
            Apartment.project_id == project_id,
            Apartment.unit_status != UnitStatus.SOLD,
            Apartment.unit_status != UnitStatus.COMPENSATION,
        )
        .order_by(Apartment.building_number, Apartment.floor, Apartment.unit_number)
    )
    apts = result.scalars().all()
    return [
        {
            "id": a.id,
            "label": f"בניין {a.building_number} | קומה {a.floor or '-'} | דירה {a.unit_number or '-'}",
            "building_number": a.building_number,
            "floor": a.floor,
            "unit_number": a.unit_number,
            "room_count": float(a.room_count) if a.room_count else None,
            "net_area_sqm": float(a.net_area_sqm) if a.net_area_sqm else None,
            "list_price_with_vat": float(a.list_price_with_vat) if a.list_price_with_vat else None,
            "list_price_no_vat": float(a.list_price_no_vat) if a.list_price_no_vat else None,
        }
        for a in apts
    ]


# ── Payment Schedule ──────────────────────────────────────────


@router.get("/projects/{project_id}/sales/{sale_id}/payments", response_model=list[PaymentScheduleItemResponse])
async def list_payments(
    project_id: int, sale_id: int,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await _verify(project_id, user.firm_id, db)
    await _verify_sale(sale_id, project_id, db)
    result = await db.execute(
        select(PaymentScheduleItem)
        .where(PaymentScheduleItem.contract_id == sale_id)
        .order_by(PaymentScheduleItem.scheduled_date)
    )
    return result.scalars().all()


@router.post("/projects/{project_id}/sales/{sale_id}/payments", response_model=PaymentScheduleItemResponse)
async def create_payment(
    project_id: int, sale_id: int,
    body: PaymentScheduleItemCreate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await _verify(project_id, user.firm_id, db)
    await _verify_sale(sale_id, project_id, db)

    # Auto-increment payment_number
    max_num = (await db.execute(
        select(func.max(PaymentScheduleItem.payment_number))
        .where(PaymentScheduleItem.contract_id == sale_id)
    )).scalar() or 0

    item = PaymentScheduleItem(
        contract_id=sale_id,
        payment_number=max_num + 1,
        **body.model_dump(exclude={"payment_number"}),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/projects/{project_id}/sales/{sale_id}/payments/{payment_id}", response_model=PaymentScheduleItemResponse)
async def update_payment(
    project_id: int, sale_id: int, payment_id: int,
    body: PaymentScheduleItemUpdate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await _verify(project_id, user.firm_id, db)
    item = (await db.execute(
        select(PaymentScheduleItem)
        .where(PaymentScheduleItem.id == payment_id, PaymentScheduleItem.contract_id == sale_id)
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="התשלום לא נמצא")

    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(item, key, val)

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/projects/{project_id}/sales/{sale_id}/payments/{payment_id}")
async def delete_payment(
    project_id: int, sale_id: int, payment_id: int,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await _verify(project_id, user.firm_id, db)
    item = (await db.execute(
        select(PaymentScheduleItem)
        .where(PaymentScheduleItem.id == payment_id, PaymentScheduleItem.contract_id == sale_id)
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="התשלום לא נמצא")
    await db.delete(item)
    await db.commit()
    return {"ok": True}


# ── Helpers ───────────────────────────────────────────────────


async def _verify(project_id: int, firm_id: int, db: AsyncSession):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.firm_id == firm_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="הפרויקט לא נמצא")


async def _verify_sale(sale_id: int, project_id: int, db: AsyncSession):
    result = await db.execute(
        select(SalesContract).where(SalesContract.id == sale_id, SalesContract.project_id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="המכירה לא נמצאה")
