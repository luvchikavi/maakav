"""Loans, deposits, and equity snapshot per monthly report.

Replaces the standalone 'מדד' navbar step. Combines:
- Loans (senior + mezzanine + other) and deposits, snapshotted per month
  with previous-month diffs auto-derived from the prior report's snapshot.
- Equity composition (pre-project, period deposits, mezzanine, withdrawals)
  with required-equity comparison and surplus/deficit gap.

Sources of pre-fill:
- Loans/deposits: project-level initial state from ProjectFinancing
  (senior_loans, subordinated_loans, deposits arrays). Each subsequent
  report pre-fills from the prior report's snapshot.
- Pre-project equity: SUM(BudgetLineItem.equity_investment) +
  ProjectFinancing.pre_project_investments rows.
- Required equity: ProjectFinancing.equity_required_amount, or
  equity_required_after_presale once presale conditions are met.

Per-period bank-derived deposits/withdrawals are not auto-pulled in this
first cut — the user fills them in directly. A follow-up can roll them
up from BankTransaction once the primary+secondary classification (item A)
is in.
"""

from datetime import date as date_type
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_current_user
from ....database import get_db
from ....models.bank_statement import BankTransaction, TransactionType
from ....models.budget import BudgetCategory, BudgetLineItem
from ....models.loans_deposits import LoansDepositsTracking
from ....models.monthly_report import MonthlyReport
from ....models.project import Project, ProjectFinancing
from ....models.user import User

router = APIRouter(tags=["loans-deposits-equity"])


async def _verify(project_id: int, report_id: int, firm_id: int, db: AsyncSession):
    project = (await db.execute(
        select(Project).where(Project.id == project_id, Project.firm_id == firm_id)
    )).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="הפרויקט לא נמצא")
    report = (await db.execute(
        select(MonthlyReport).where(
            MonthlyReport.id == report_id, MonthlyReport.project_id == project_id
        )
    )).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="הדוח לא נמצא")
    return project, report


def _seed_from_financing(financing: ProjectFinancing | None) -> tuple[list, list]:
    """Build initial loans/deposits arrays from the project's setup data."""
    loans: list = []
    deposits: list = []
    if not financing:
        return loans, deposits

    for entry in financing.senior_loans or []:
        loans.append({
            "label": "הלוואת חוב בכיר",
            "kind": "senior",
            "principal": float(entry.get("principal") or 0),
            "current_balance": float(entry.get("balance") or 0),
            "prev_month": None,
        })
    for entry in financing.subordinated_loans or []:
        loans.append({
            "label": "הלוואת מזניין/חוב נחות",
            "kind": "mezzanine",
            "principal": float(entry.get("principal") or 0),
            "current_balance": float(entry.get("balance") or 0),
            "prev_month": None,
        })
    for entry in financing.deposits or []:
        deposits.append({
            "label": 'פיקדון פק"מ',
            "principal": float(entry.get("principal") or 0),
            "current_balance": float(entry.get("balance") or 0),
            "prev_month": None,
            "accrued_interest": None,
        })
    return loans, deposits


@router.get("/projects/{project_id}/monthly-reports/{report_id}/loans-deposits-equity")
async def get_loans_deposits_equity(
    project_id: int, report_id: int,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    project, report = await _verify(project_id, report_id, user.firm_id, db)

    # Existing snapshot for this report — if any.
    snapshot = (await db.execute(
        select(LoansDepositsTracking).where(
            LoansDepositsTracking.monthly_report_id == report_id
        )
    )).scalar_one_or_none()

    financing = (await db.execute(
        select(ProjectFinancing).where(ProjectFinancing.project_id == project_id)
    )).scalar_one_or_none()

    # If no snapshot for this report, seed from prior report (or financing setup).
    if snapshot is None:
        prior = (await db.execute(
            select(LoansDepositsTracking).join(
                MonthlyReport, MonthlyReport.id == LoansDepositsTracking.monthly_report_id
            ).where(
                MonthlyReport.project_id == project_id,
                MonthlyReport.report_number < report.report_number,
            ).order_by(MonthlyReport.report_number.desc()).limit(1)
        )).scalar_one_or_none()

        if prior is not None:
            # Roll the prior month's current_balance into prev_month for diffs.
            loans = [
                {**it, "prev_month": it.get("current_balance")}
                for it in (prior.loans or [])
            ]
            deposits = [
                {**it, "prev_month": it.get("current_balance")}
                for it in (prior.deposits or [])
            ]
        else:
            loans, deposits = _seed_from_financing(financing)
    else:
        loans = list(snapshot.loans or [])
        deposits = list(snapshot.deposits or [])

    # Equity composition.
    budget_equity = (await db.execute(
        select(func.coalesce(func.sum(BudgetLineItem.equity_investment), 0))
        .select_from(BudgetLineItem)
        .join(BudgetCategory, BudgetLineItem.category_id == BudgetCategory.id)
        .where(BudgetCategory.project_id == project_id)
    )).scalar() or 0
    manual_pre_project = sum(
        float(it.get("amount") or 0)
        for it in (financing.pre_project_investments if financing else None) or []
    )
    pre_project_total = float(budget_equity) + manual_pre_project

    mezzanine_total = sum(
        float(it.get("current_balance") or 0)
        for it in loans
        if it.get("kind") == "mezzanine"
    )

    # Item A introduces a `subcategory` on every BankTransaction. Sum
    # equity-related deposits and withdrawals for THIS report so the
    # equity composition lines that used to be manual now feed
    # themselves. Withdrawals are returned as a positive number that the
    # frontend renders with a (parens) negative.
    period_equity_deposits = float((await db.execute(
        select(func.coalesce(func.sum(BankTransaction.amount), 0))
        .where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.transaction_type == TransactionType.CREDIT,
            BankTransaction.subcategory == "equity_deposit",
        )
    )).scalar() or 0)
    period_equity_withdrawals = float((await db.execute(
        select(func.coalesce(func.sum(BankTransaction.amount), 0))
        .where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.transaction_type == TransactionType.DEBIT,
            BankTransaction.subcategory == "equity_withdrawal",
        )
    )).scalar() or 0)

    # Required equity: post-presale value if defined, else the main one.
    required = None
    if financing:
        required = (
            financing.equity_required_after_presale
            or financing.equity_required_amount
        )

    components = [
        {"label": "השקעות הון עצמי (טרם תחילת ליווי)", "amount": pre_project_total, "source": "budget+manual"},
        {"label": "הפקדות הון עצמי בחשבון הליווי", "amount": period_equity_deposits, "source": "bank"},
        {"label": "הלוואות מזנין", "amount": mezzanine_total, "source": "loans"},
        # Stored as positive but subtracted into the total below.
        {"label": "משיכות הון עצמי בחשבון הליווי", "amount": -period_equity_withdrawals, "source": "bank"},
    ]
    current_balance = sum(c["amount"] for c in components)
    required_f = float(required) if required is not None else 0.0
    gap = current_balance - required_f

    return {
        "as_of": snapshot.as_of.isoformat() if snapshot and snapshot.as_of else None,
        "loans": loans,
        "deposits": deposits,
        "equity": {
            "components": components,
            "current_balance": round(current_balance, 2),
            "required_amount": round(required_f, 2),
            "gap": round(gap, 2),
        },
        "notes": snapshot.notes if snapshot else None,
    }


@router.put("/projects/{project_id}/monthly-reports/{report_id}/loans-deposits-equity")
async def save_loans_deposits_equity(
    project_id: int, report_id: int, body: dict,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await _verify(project_id, report_id, user.firm_id, db)

    snapshot = (await db.execute(
        select(LoansDepositsTracking).where(
            LoansDepositsTracking.monthly_report_id == report_id
        )
    )).scalar_one_or_none()

    as_of_str = body.get("as_of")
    as_of = None
    if as_of_str:
        try:
            as_of = date_type.fromisoformat(as_of_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="תאריך לא תקין")

    fields = {
        "loans": body.get("loans") or [],
        "deposits": body.get("deposits") or [],
        "as_of": as_of,
        "notes": body.get("notes"),
    }

    if snapshot:
        for k, v in fields.items():
            setattr(snapshot, k, v)
    else:
        snapshot = LoansDepositsTracking(
            monthly_report_id=report_id, project_id=project_id, **fields,
        )
        db.add(snapshot)

    await db.commit()
    return {"ok": True}
