"""Guarantee upload and management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ....database import get_db
from ....models.user import User
from ....models.project import Project
from ....models.monthly_report import MonthlyReport
from ....models.guarantee import GuaranteeSnapshot
from ....services.guarantee_parser_service import guarantee_parser
from ....core.dependencies import get_current_user

router = APIRouter(tags=["guarantees"])


@router.post("/projects/{project_id}/monthly-reports/{report_id}/guarantees/upload")
async def upload_guarantees(
    project_id: int,
    report_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload and parse a guarantee statement (PDF/Excel)."""
    await _verify(project_id, report_id, user.firm_id, db)

    content = await file.read()
    content_type = file.content_type or ""

    # Map common types
    if file.filename and file.filename.endswith('.xlsx'):
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif file.filename and file.filename.endswith('.xls'):
        content_type = 'application/vnd.ms-excel'
    elif file.filename and file.filename.endswith('.pdf'):
        content_type = 'application/pdf'

    result = guarantee_parser.parse_guarantee_file(content, content_type, file.filename or "")

    # Upsert guarantee snapshot
    existing = (await db.execute(
        select(GuaranteeSnapshot).where(GuaranteeSnapshot.monthly_report_id == report_id)
    )).scalar_one_or_none()

    if existing:
        existing.items = result["items"]
        existing.total_balance = result["total_balance"]
        existing.notes = "; ".join(result.get("warnings", []))
    else:
        snapshot = GuaranteeSnapshot(
            monthly_report_id=report_id,
            project_id=project_id,
            items=result["items"],
            total_balance=result["total_balance"],
            notes="; ".join(result.get("warnings", [])),
        )
        db.add(snapshot)

    await db.commit()

    return {
        "items_count": len(result["items"]),
        "total_balance": result["total_balance"],
        "items": result["items"],
        "warnings": result.get("warnings", []),
    }


@router.get("/projects/{project_id}/monthly-reports/{report_id}/guarantees")
async def get_guarantees(
    project_id: int,
    report_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get guarantee snapshot for a monthly report."""
    await _verify(project_id, report_id, user.firm_id, db)

    snapshot = (await db.execute(
        select(GuaranteeSnapshot).where(GuaranteeSnapshot.monthly_report_id == report_id)
    )).scalar_one_or_none()

    if not snapshot:
        return {"items": [], "total_balance": 0, "notes": None}

    return {
        "id": snapshot.id,
        "items": snapshot.items or [],
        "total_balance": float(snapshot.total_balance),
        "total_receipts": float(snapshot.total_receipts),
        "gap": float(snapshot.gap),
        "notes": snapshot.notes,
    }


@router.put("/projects/{project_id}/monthly-reports/{report_id}/guarantees/items")
async def update_guarantee_items(
    project_id: int,
    report_id: int,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update guarantee items (after manual editing)."""
    await _verify(project_id, report_id, user.firm_id, db)

    snapshot = (await db.execute(
        select(GuaranteeSnapshot).where(GuaranteeSnapshot.monthly_report_id == report_id)
    )).scalar_one_or_none()

    if not snapshot:
        raise HTTPException(status_code=404, detail="לא נמצא תדפיס ערבויות")

    items = body.get("items", [])
    snapshot.items = items
    snapshot.total_balance = sum(float(i.get("indexed_balance", 0) or 0) for i in items)

    await db.commit()
    return {"ok": True, "items_count": len(items), "total_balance": snapshot.total_balance}


@router.get("/projects/{project_id}/monthly-reports/{report_id}/guarantees/validate")
async def validate_guarantees(
    project_id: int,
    report_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cross-validate guarantees vs sales and receipts."""
    await _verify(project_id, report_id, user.firm_id, db)

    from ....models.sales import SalesContract
    from ....models.apartment import Apartment, UnitStatus
    from ....models.bank_statement import BankTransaction, TransactionCategory, TransactionType

    alerts = []

    # Get guarantee snapshot
    snapshot = (await db.execute(
        select(GuaranteeSnapshot).where(GuaranteeSnapshot.monthly_report_id == report_id)
    )).scalar_one_or_none()

    if not snapshot or not snapshot.items:
        # Check if there are sold apartments that should have guarantees
        sold_count = (await db.execute(
            select(func.count()).where(
                Apartment.project_id == project_id,
                Apartment.unit_status == UnitStatus.SOLD,
            )
        )).scalar() or 0
        if sold_count > 0:
            alerts.append({
                "type": "missing_snapshot",
                "severity": "warning",
                "message": f"קיימות {sold_count} דירות שנמכרו אך לא הועלה תדפיס ערבויות",
            })
        return {"alerts": alerts, "summary": {"total_guarantees": 0, "total_receipts": 0}}

    # Get sale law guarantees
    sale_law_items = [i for i in snapshot.items if i.get("guarantee_type") == "sale_law"]
    guaranteed_apts = {str(i.get("apartment_number", "")) for i in sale_law_items if i.get("apartment_number")}

    # Get sold apartments
    sales = (await db.execute(
        select(SalesContract).where(SalesContract.project_id == project_id)
    )).scalars().all()

    # Get receipts from bank
    total_receipts = (await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.project_id == project_id,
            BankTransaction.category == TransactionCategory.SALE_INCOME,
            BankTransaction.transaction_type == TransactionType.CREDIT,
        )
    )).scalar() or 0

    # Check 1: Sold apartments should have sale_law guarantee
    for sale in sales:
        apt_num = str(sale.apartment_id)
        if apt_num not in guaranteed_apts:
            alerts.append({
                "type": "sale_no_guarantee",
                "severity": "error",
                "apartment_id": sale.apartment_id,
                "message": f"דירה {apt_num} ({sale.buyer_name}) נמכרה אך אין ערבות חוק מכר",
            })

    # Check 2: Compare guarantee total vs receipts
    guarantee_total = sum(i.get("indexed_balance", 0) for i in sale_law_items)
    gap = guarantee_total - float(total_receipts)

    if gap < -10000:  # Significant negative gap
        alerts.append({
            "type": "receipts_exceed_guarantees",
            "severity": "warning",
            "message": f'תקבולים ({format_ils(total_receipts)}) עולים על סה"כ ערבויות חוק מכר ({format_ils(guarantee_total)})',
        })

    return {
        "alerts": alerts,
        "summary": {
            "total_guarantees": len(sale_law_items),
            "total_guarantee_amount": round(guarantee_total),
            "total_receipts": round(float(total_receipts)),
            "gap": round(gap),
            "sold_apartments": len(sales),
            "apartments_with_guarantee": len(guaranteed_apts),
        },
    }


def format_ils(amount) -> str:
    try:
        return f"{int(float(amount)):,} ₪"
    except (ValueError, TypeError):
        return str(amount)


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
