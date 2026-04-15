"""Bulk upload endpoints — preview and confirm unified Excel import."""

import json
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ....database import get_db
from ....models.user import User
from ....models.project import Project
from ....models.apartment import Apartment, Ownership, UnitStatus, UnitType
from ....models.budget import BudgetCategory, BudgetLineItem, CategoryType
from ....models.guarantee import GuaranteeSnapshot
from ....core.dependencies import get_current_user
from ....services.bulk_upload_service import parse_bulk_upload

router = APIRouter(tags=["bulk-upload"])


@router.post("/projects/{project_id}/setup/bulk-upload/preview")
async def preview_bulk_upload(
    project_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload Excel file and return a preview of what will be imported."""
    await _verify(project_id, user.firm_id, db)

    content = await file.read()
    try:
        result = parse_bulk_upload(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"שגיאה בפרסור הקובץ: {str(e)}")

    return result


@router.post("/projects/{project_id}/setup/bulk-upload/confirm")
async def confirm_bulk_upload(
    project_id: int,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm and save the parsed data.
    Body should contain the parsed result from preview (or a modified version).
    Replaces existing data for the project.
    """
    await _verify(project_id, user.firm_id, db)

    saved = {
        "apartments": 0,
        "budget_lines": 0,
        "guarantees": 0,
        "financing_updated": False,
    }

    # ── 1. Apartments — delete existing and re-insert ────────

    # Check if any apartments have sales contracts
    from ....models.sales import SalesContract
    existing_sales = (await db.execute(
        select(SalesContract).where(SalesContract.project_id == project_id)
    )).scalars().all()

    if existing_sales:
        # Don't delete apartments that have sales — only add new ones
        existing_apt_ids = {s.apartment_id for s in existing_sales}
        existing_apts = (await db.execute(
            select(Apartment).where(Apartment.project_id == project_id)
        )).scalars().all()
        # Delete only apartments without sales
        for apt in existing_apts:
            if apt.id not in existing_apt_ids:
                await db.delete(apt)
    else:
        await db.execute(delete(Apartment).where(Apartment.project_id == project_id))

    # Insert all apartment lists
    for key in [
        "apartments_developer_residential",
        "apartments_developer_commercial",
        "apartments_resident_residential",
        "apartments_resident_commercial",
    ]:
        for apt_data in body.get(key, []):
            ownership = Ownership.DEVELOPER if apt_data.get("ownership") == "developer" else Ownership.RESIDENT

            # Map unit_type
            raw_type = apt_data.get("unit_type", "apartment")
            try:
                unit_type = UnitType(raw_type)
            except ValueError:
                unit_type = UnitType.OTHER

            # Map status
            raw_status = apt_data.get("unit_status", "for_sale")
            try:
                unit_status = UnitStatus(raw_status)
            except ValueError:
                unit_status = UnitStatus.FOR_SALE

            apt = Apartment(
                project_id=project_id,
                building_number=apt_data.get("building_number", "A"),
                floor=apt_data.get("floor"),
                unit_number=apt_data.get("unit_number"),
                plan_number=apt_data.get("plan_number"),
                direction=apt_data.get("direction"),
                unit_type=unit_type,
                ownership=ownership,
                unit_status=unit_status,
                room_count=_to_dec(apt_data.get("room_count")),
                net_area_sqm=_to_dec(apt_data.get("net_area_sqm")),
                balcony_area_sqm=_to_dec(apt_data.get("balcony_area_sqm")),
                terrace_area_sqm=_to_dec(apt_data.get("terrace_area_sqm")),
                yard_area_sqm=_to_dec(apt_data.get("yard_area_sqm")),
                parking_count=int(apt_data.get("parking_count", 0) or 0),
                storage_count=int(apt_data.get("storage_count", 0) or 0),
                list_price_with_vat=_to_dec(apt_data.get("list_price_with_vat")),
                list_price_no_vat=_to_dec(apt_data.get("list_price_no_vat")),
                price_per_sqm=_to_dec(apt_data.get("price_per_sqm")),
                gross_area_sqm=_to_dec(apt_data.get("gross_area_sqm")),
                gallery_area_sqm=_to_dec(apt_data.get("gallery_area_sqm")),
                secondary_type=apt_data.get("secondary_type"),
                owner_name=apt_data.get("owner_name"),
            )
            db.add(apt)
            saved["apartments"] += 1

    # ── 2. Budget — delete existing and re-insert ────────────

    budget_data = body.get("budget_categories", {})
    if budget_data:
        # Delete existing budget
        existing_cats = (await db.execute(
            select(BudgetCategory).where(BudgetCategory.project_id == project_id)
        )).scalars().all()
        for cat in existing_cats:
            await db.execute(delete(BudgetLineItem).where(BudgetLineItem.category_id == cat.id))
            await db.delete(cat)

        # Insert new
        order = 0
        for cat_key, items in budget_data.items():
            try:
                cat_type = CategoryType(cat_key)
            except ValueError:
                continue

            total = sum(float(item.get("cost_no_vat") or 0) for item in items)
            cat = BudgetCategory(
                project_id=project_id,
                category_type=cat_type,
                display_order=order,
                total_amount=Decimal(str(round(total, 2))),
            )
            db.add(cat)
            await db.flush()
            order += 1

            for i, item in enumerate(items, 1):
                db.add(BudgetLineItem(
                    category_id=cat.id,
                    line_number=i,
                    description=item.get("description", ""),
                    supplier_name=item.get("supplier_name"),
                    cost_no_vat=_to_dec(item.get("cost_no_vat")) or Decimal("0"),
                    notes=item.get("notes"),
                ))
                saved["budget_lines"] += 1

    # ── 3. Guarantees — save as latest snapshot ──────────────

    guarantees = body.get("guarantees", [])
    if guarantees:
        # Find or create a monthly report to attach to (use latest)
        from ....models.monthly_report import MonthlyReport
        latest_report = (await db.execute(
            select(MonthlyReport)
            .where(MonthlyReport.project_id == project_id)
            .order_by(MonthlyReport.report_number.desc())
            .limit(1)
        )).scalar_one_or_none()

        if latest_report:
            # Upsert guarantee snapshot
            existing_g = (await db.execute(
                select(GuaranteeSnapshot).where(GuaranteeSnapshot.monthly_report_id == latest_report.id)
            )).scalar_one_or_none()

            total_balance = sum(g.get("indexed_balance", 0) for g in guarantees)

            if existing_g:
                existing_g.items = guarantees
                existing_g.total_balance = Decimal(str(round(total_balance, 2)))
            else:
                db.add(GuaranteeSnapshot(
                    monthly_report_id=latest_report.id,
                    project_id=project_id,
                    items=guarantees,
                    total_balance=Decimal(str(round(total_balance, 2))),
                ))
            saved["guarantees"] = len(guarantees)

    # ── 4. Financing — update project financing ──────────────

    financing = body.get("financing")
    if financing and financing.get("account_number"):
        project = (await db.execute(
            select(Project).where(Project.id == project_id)
        )).scalar_one()

        if financing.get("account_number"):
            project.project_account_number = str(financing["account_number"])
        if financing.get("branch"):
            project.bank_branch = str(financing["branch"])

        saved["financing_updated"] = True

    await db.commit()

    return {
        "ok": True,
        "saved": saved,
        "message": f'הועלו {saved["apartments"]} נכסים, {saved["budget_lines"]} סעיפי תקציב, {saved["guarantees"]} ערבויות.',
    }


def _to_dec(val) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


async def _verify(project_id: int, firm_id: int, db: AsyncSession):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.firm_id == firm_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="הפרויקט לא נמצא")
