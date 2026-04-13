"""Bank statement upload, parsing, and transaction classification endpoints."""

import tempfile
from decimal import Decimal
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

    # Save file temporarily
    content = await file.read()
    suffix = ".pdf" if file.filename and file.filename.lower().endswith(".pdf") else ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    # Parse with AI
    try:
        result = parser.parse(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"שגיאה בפרסור הקובץ: {str(e)}")

    if not result or "error" in result:
        raise HTTPException(status_code=400, detail=result.get("error", "לא ניתן לפרסר את הקובץ"))

    # Create bank statement record
    statement = BankStatement(
        monthly_report_id=report_id,
        project_id=project_id,
        original_filename=file.filename,
        bank_name=result.get("bank_name"),
        account_number=result.get("account_number"),
        statement_start_date=result.get("start_date"),
        statement_end_date=result.get("end_date"),
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

        tx_type = TransactionType.CREDIT if float(tx.get("amount", 0)) > 0 else TransactionType.DEBIT

        bank_tx = BankTransaction(
            bank_statement_id=statement.id,
            monthly_report_id=report_id,
            project_id=project_id,
            transaction_date=tx.get("date"),
            description=tx.get("description", ""),
            amount=Decimal(str(amount)),
            balance=Decimal(str(tx["balance"])) if tx.get("balance") else None,
            transaction_type=tx_type,
            reference_number=tx.get("reference"),
        )
        db.add(bank_tx)

    # Update report status
    if report.status == "draft":
        report.status = "data_entry"

    await db.commit()
    await db.refresh(statement)

    return {
        "id": statement.id,
        "bank_name": statement.bank_name,
        "account_number": statement.account_number,
        "transactions_count": len(transactions),
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
        .order_by(BankTransaction.transaction_date)
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
        raise HTTPException(status_code=404, detail="Transaction not found")

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


async def _verify_project(project_id: int, firm_id: int, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id, Project.firm_id == firm_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_report(report_id: int, project_id: int, db: AsyncSession) -> MonthlyReport:
    result = await db.execute(
        select(MonthlyReport).where(MonthlyReport.id == report_id, MonthlyReport.project_id == project_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
