"""Bank statement upload, parsing, and transaction classification endpoints."""

import logging
from decimal import Decimal

logger = logging.getLogger(__name__)
from datetime import date as date_type, datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ....database import get_db
from ....models.user import User
from ....models.project import Project
from ....models.monthly_report import MonthlyReport
from ....models.bank_statement import BankStatement, BankTransaction, ParsingStatus, TransactionType, TransactionCategory
from ....schemas.monthly import BankStatementResponse, BankTransactionResponse, TransactionClassifyRequest
from ....core.dependencies import get_current_user
from ....services.bank_parser_service import BankStatementAIParser
from ....services.transaction_classifier import transaction_classifier

router = APIRouter(tags=["bank-statements"])

parser = BankStatementAIParser()


@router.post("/projects/{project_id}/monthly-reports/{report_id}/bank-statements/upload")
async def upload_bank_statement(
    project_id: int,
    report_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a bank statement PDF. AI parses transactions automatically."""
    project = await _verify_project(project_id, user.firm_id, db)
    report = await _get_report(report_id, project_id, db)

    # Read file content
    content = await file.read()
    content_type = file.content_type or ""
    filename = file.filename or ""

    # Determine content type from extension if needed
    if filename.lower().endswith(".pdf"):
        content_type = "application/pdf"
    elif filename.lower().endswith((".xlsx", ".xls")):
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # Parse with AI
    try:
        result = parser.parse_bank_statement(content, content_type, filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"שגיאה בפרסור הקובץ: {str(e)}")

    if not result or "error" in result:
        raise HTTPException(status_code=400, detail=result.get("error", "לא ניתן לפרסר את הקובץ"))

    # Create bank statement record
    statement = BankStatement(
        monthly_report_id=report_id,
        project_id=project_id,
        original_filename=file.filename,
        bank_name=result.get("bank_display") or result.get("bank_name") or result.get("bank"),
        account_number=result.get("account_number"),
        statement_start_date=_to_date(result.get("statement_start_date") or result.get("start_date")),
        statement_end_date=_to_date(result.get("statement_end_date") or result.get("end_date")),
        opening_balance=Decimal(str(result["opening_balance"])) if result.get("opening_balance") else None,
        closing_balance=Decimal(str(result["closing_balance"])) if result.get("closing_balance") else None,
        ai_confidence=Decimal(str(result.get("confidence", 0))),
        ai_warnings=result.get("warnings", []),
        parsing_status=ParsingStatus.PARSED,
    )
    db.add(statement)
    await db.flush()  # Get statement.id

    # Create transaction records
    transactions = result.get("transactions", [])
    for tx in transactions:
        amount = abs(float(tx.get("amount", 0)))
        if amount == 0:
            continue

        raw_type = str(tx.get("type", "")).upper()
        if raw_type == "CREDIT":
            tx_type = TransactionType.CREDIT
        elif raw_type == "DEBIT":
            tx_type = TransactionType.DEBIT
        else:
            tx_type = TransactionType.CREDIT if float(tx.get("amount", 0)) > 0 else TransactionType.DEBIT

        bank_tx = BankTransaction(
            bank_statement_id=statement.id,
            monthly_report_id=report_id,
            project_id=project_id,
            transaction_date=_to_date(tx.get("date")),
            description=tx.get("description", ""),
            amount=Decimal(str(amount)),
            balance=Decimal(str(tx["balance"])) if tx.get("balance") else None,
            transaction_type=tx_type,
            reference_number=tx.get("reference"),
        )
        db.add(bank_tx)

    await db.flush()  # Ensure transactions have IDs before auto-classification

    # Update report status
    if report.status == "draft":
        report.status = "data_entry"

    await db.commit()
    await db.refresh(statement)

    # Auto-classify transactions after upload
    auto_classified = 0
    try:
        all_txs = (await db.execute(
            select(BankTransaction).where(
                BankTransaction.bank_statement_id == statement.id,
                BankTransaction.category.is_(None),
            )
        )).scalars().all()

        if all_txs:
            tx_batch = [
                {"id": t.id, "description": t.description, "amount": float(t.amount), "type": t.transaction_type.value}
                for t in all_txs
            ]
            suggestions = transaction_classifier.classify_transactions(tx_batch)
            for s in suggestions:
                if s.get("suggested_category") and s.get("confidence", 0) >= 0.5:
                    tx_obj = next((t for t in all_txs if t.id == s["id"]), None)
                    if tx_obj:
                        tx_obj.ai_suggested_category = s["suggested_category"]
                        tx_obj.ai_confidence = Decimal(str(round(s["confidence"], 2)))
                        # Auto-apply high-confidence suggestions
                        if s["confidence"] >= 0.75:
                            tx_obj.category = TransactionCategory(s["suggested_category"])
                            auto_classified += 1

            await db.commit()
    except Exception as e:
        logger.warning(f"Auto-classification failed: {e}")

    return {
        "id": statement.id,
        "bank_name": statement.bank_name,
        "account_number": statement.account_number,
        "transactions_count": len(transactions),
        "auto_classified": auto_classified,
        "parsing_status": statement.parsing_status.value,
        "warnings": statement.ai_warnings,
    }


@router.get("/projects/{project_id}/monthly-reports/{report_id}/transactions", response_model=list[BankTransactionResponse])
async def list_transactions(
    project_id: int,
    report_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project(project_id, user.firm_id, db)
    result = await db.execute(
        select(BankTransaction)
        .where(BankTransaction.monthly_report_id == report_id, BankTransaction.project_id == project_id)
        .order_by(BankTransaction.id)  # preserve original bank-statement order
    )
    return result.scalars().all()


@router.patch("/projects/{project_id}/monthly-reports/{report_id}/transactions/{tx_id}")
async def classify_transaction(
    project_id: int,
    report_id: int,
    tx_id: int,
    body: TransactionClassifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually classify a transaction."""
    await _verify_project(project_id, user.firm_id, db)
    result = await db.execute(
        select(BankTransaction).where(BankTransaction.id == tx_id, BankTransaction.monthly_report_id == report_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="התנועה לא נמצאה")

    tx.category = TransactionCategory(body.category)
    tx.is_manually_classified = True
    if body.notes:
        tx.notes = body.notes
    if body.linked_apartment_id:
        tx.linked_apartment_id = body.linked_apartment_id

    await db.commit()
    return {"ok": True}


@router.post("/projects/{project_id}/monthly-reports/{report_id}/transactions/bulk-classify")
async def bulk_classify(
    project_id: int,
    report_id: int,
    classifications: list[dict],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk classify multiple transactions. Body: [{id, category}]"""
    await _verify_project(project_id, user.firm_id, db)

    updated = 0
    for item in classifications:
        tx_id = item.get("id")
        category = item.get("category")
        if not tx_id or not category:
            continue

        result = await db.execute(
            select(BankTransaction).where(BankTransaction.id == tx_id, BankTransaction.monthly_report_id == report_id)
        )
        tx = result.scalar_one_or_none()
        if tx:
            tx.category = TransactionCategory(category)
            tx.is_manually_classified = True
            updated += 1

    await db.commit()
    return {"updated": updated}


@router.delete("/projects/{project_id}/monthly-reports/{report_id}/transactions/{tx_id}")
async def delete_transaction(
    project_id: int,
    report_id: int,
    tx_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single transaction (e.g., duplicate from overlapping statement dates)."""
    await _verify_project(project_id, user.firm_id, db)
    tx = (await db.execute(
        select(BankTransaction).where(BankTransaction.id == tx_id, BankTransaction.monthly_report_id == report_id)
    )).scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="התנועה לא נמצאה")
    await db.delete(tx)
    await db.commit()
    return {"ok": True}


@router.get("/projects/{project_id}/monthly-reports/{report_id}/bank-summary")
async def get_bank_summary(
    project_id: int,
    report_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get bank statement summary: opening/closing balance, totals."""
    await _verify_project(project_id, user.firm_id, db)
    statements = (await db.execute(
        select(BankStatement).where(
            BankStatement.monthly_report_id == report_id,
            BankStatement.project_id == project_id,
        )
    )).scalars().all()

    if not statements:
        # No statement but maybe transactions exist (demo data) — calculate from transactions
        txs = (await db.execute(
            select(BankTransaction).where(
                BankTransaction.monthly_report_id == report_id,
                BankTransaction.project_id == project_id,
            ).order_by(BankTransaction.id)  # preserve original bank-statement order
        )).scalars().all()

        if not txs:
            return {"opening_balance": None, "closing_balance": None, "bank_name": None}

        # Calculate from first/last transaction balances
        first_balance = float(txs[0].balance) if txs[0].balance else None
        last_balance = float(txs[-1].balance) if txs[-1].balance else None
        total_credits = sum(float(t.amount) for t in txs if t.transaction_type == TransactionType.CREDIT)
        total_debits = sum(float(t.amount) for t in txs if t.transaction_type == TransactionType.DEBIT)

        return {
            "opening_balance": first_balance,
            "closing_balance": last_balance,
            "bank_name": None,
            "account_number": None,
            "statement_start_date": str(txs[0].transaction_date),
            "statement_end_date": str(txs[-1].transaction_date),
            "total_credits": round(total_credits),
            "total_debits": round(total_debits),
        }

    stmt = statements[0]

    # Also compute totals from transactions
    total_credits = (await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.transaction_type == TransactionType.CREDIT,
        )
    )).scalar() or 0
    total_debits = (await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.transaction_type == TransactionType.DEBIT,
        )
    )).scalar() or 0

    return {
        "opening_balance": float(stmt.opening_balance) if stmt.opening_balance else None,
        "closing_balance": float(stmt.closing_balance) if stmt.closing_balance else None,
        "bank_name": stmt.bank_name,
        "account_number": stmt.account_number,
        "statement_start_date": str(stmt.statement_start_date) if stmt.statement_start_date else None,
        "statement_end_date": str(stmt.statement_end_date) if stmt.statement_end_date else None,
        "total_credits": round(float(total_credits)),
        "total_debits": round(float(total_debits)),
    }


@router.post("/projects/{project_id}/monthly-reports/{report_id}/transactions/auto-classify")
async def auto_classify_transactions(
    project_id: int,
    report_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run AI auto-classification on unclassified transactions."""
    await _verify_project(project_id, user.firm_id, db)

    unclassified = (await db.execute(
        select(BankTransaction).where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.project_id == project_id,
            BankTransaction.category.is_(None),
        )
    )).scalars().all()

    if not unclassified:
        return {"classified": 0, "total_unclassified": 0}

    tx_batch = [
        {"id": t.id, "description": t.description, "amount": float(t.amount), "type": t.transaction_type.value}
        for t in unclassified
    ]
    suggestions = transaction_classifier.classify_transactions(tx_batch)

    classified = 0
    for s in suggestions:
        if s.get("suggested_category") and s.get("confidence", 0) >= 0.5:
            tx_obj = next((t for t in unclassified if t.id == s["id"]), None)
            if tx_obj:
                tx_obj.ai_suggested_category = s["suggested_category"]
                tx_obj.ai_confidence = Decimal(str(round(s["confidence"], 2)))
                if s["confidence"] >= 0.75:
                    tx_obj.category = TransactionCategory(s["suggested_category"])
                    classified += 1

    await db.commit()
    return {"classified": classified, "total_unclassified": len(unclassified)}


def _to_date(val) -> date_type | None:
    """Convert string/datetime to date object for DB."""
    if val is None:
        return None
    if isinstance(val, date_type):
        return val
    if isinstance(val, datetime):
        return val.date()
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


async def _verify_project(project_id: int, firm_id: int, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id, Project.firm_id == firm_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="הפרויקט לא נמצא")
    return project


async def _get_report(report_id: int, project_id: int, db: AsyncSession) -> MonthlyReport:
    result = await db.execute(
        select(MonthlyReport).where(MonthlyReport.id == report_id, MonthlyReport.project_id == project_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="הדוח לא נמצא")
    return report
