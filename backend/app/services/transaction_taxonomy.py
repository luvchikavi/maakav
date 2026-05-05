"""Two-level transaction classification taxonomy.

Per the QA list: every bank-statement row needs a PRIMARY classification
(broad bucket like "הוצאות דיירים" or "תקבולים") plus a SECONDARY pick
within that primary.

The existing flat ``TransactionCategory`` enum maps roughly to the new
secondary level for income/withdrawal-style rows; for budget-line
expenses, the existing values ARE the primary, and the user later picks
a secondary item from the project's budget. To keep the data model
backwards-compatible we store both:

- ``category`` (existing, flat) — still the primary signal that all
  budget aggregation reads. Untouched.
- ``category_primary`` — new, optional. The Hebrew-named primary group
  the user picked. Derived automatically from ``category`` for legacy
  rows via :func:`primary_for_category`.

The frontend uses :data:`PRIMARY_GROUPS` to render two dropdowns. The
second is filtered by the chosen first.
"""

from __future__ import annotations

from typing import TypedDict

# Stable keys (English) so DB values stay tidy. Labels (Hebrew) in
# PRIMARY_LABELS are for UI rendering only.

# ── Expenses ────────────────────────────────────────────────
PRIMARY_TENANT_EXPENSES = "tenant_expenses"
PRIMARY_LAND_AND_TAXES = "land_and_taxes"
PRIMARY_INDIRECT_COSTS = "indirect_costs"
PRIMARY_DIRECT_CONSTRUCTION = "direct_construction"
PRIMARY_INTEREST_FEES_GUARANTEES = "interest_fees_guarantees"
PRIMARY_WITHDRAWALS = "withdrawals"

# ── Income ──────────────────────────────────────────────────
PRIMARY_RECEIPTS = "receipts"
PRIMARY_DEPOSITS = "deposits"


class SecondaryItem(TypedDict):
    key: str
    label: str


PRIMARY_LABELS: dict[str, str] = {
    PRIMARY_TENANT_EXPENSES: "הוצאות דיירים",
    PRIMARY_LAND_AND_TAXES: "קרקע ומיסוי",
    PRIMARY_INDIRECT_COSTS: "הוצאות עקיפות",
    PRIMARY_DIRECT_CONSTRUCTION: "בניה ישירה",
    PRIMARY_INTEREST_FEES_GUARANTEES: "ריביות, עמלות וערבויות",
    PRIMARY_WITHDRAWALS: "משיכות",
    PRIMARY_RECEIPTS: "תקבולים",
    PRIMARY_DEPOSITS: "הפקדות",
}


# Secondary lists. For the four budget-line primaries (tenant_expenses,
# land_and_taxes, indirect_costs, direct_construction) the secondary item
# is whatever budget line the user picks within that category — handled
# at runtime from the project's budget. For the rest, the secondaries are
# fixed.
PRIMARY_SECONDARIES: dict[str, list[SecondaryItem]] = {
    PRIMARY_INTEREST_FEES_GUARANTEES: [
        {"key": "interest_and_fees", "label": "ריביות"},
        {"key": "fees", "label": "עמלות"},
        {"key": "guarantees", "label": "ערבויות"},
        {"key": "other_expense", "label": "אחר"},
    ],
    PRIMARY_WITHDRAWALS: [
        {"key": "equity_withdrawal", "label": "משיכות הון עצמי / עודפים"},
        {"key": "deposit_to_savings", "label": "הפקדה לפיקדון"},
        {"key": "loan_repayment_senior", "label": "פירעון הלוואה (בכיר)"},
        {"key": "loan_repayment_subordinated", "label": "פירעון הלוואה (נחות/מזנין)"},
        {"key": "vat_payment", "label": 'תשלומי מע"מ'},
        {"key": "purchase_cancellation_refund", "label": "החזר כספים (ביטולי רכישות)"},
        {"key": "other_withdrawal", "label": "אחר"},
    ],
    PRIMARY_RECEIPTS: [
        {"key": "buyer_receipt", "label": "תקבולים מרוכשים"},
        {"key": "upgrade_receipt", "label": "תקבולים משדרוגים"},
        {"key": "non_residential_receipt", "label": "תקבולים מרוכשים שאינם מגורים"},
        {"key": "other_receipt", "label": "אחר"},
    ],
    PRIMARY_DEPOSITS: [
        {"key": "equity_deposit", "label": "הפקדות הון עצמי"},
        {"key": "deposit_withdrawal", "label": "משיכה מפיקדון"},
        {"key": "loan_disbursement_senior", "label": "העמדת הלוואה (בכיר)"},
        {"key": "loan_disbursement_subordinated", "label": "העמדת הלוואה (נחות/מזנין)"},
        {"key": "vat_refund", "label": 'החזרי מע"מ'},
        {"key": "other_deposit", "label": "אחר"},
    ],
    # Budget-line primaries: secondary picked from project budget at runtime.
    PRIMARY_TENANT_EXPENSES: [],
    PRIMARY_LAND_AND_TAXES: [],
    PRIMARY_INDIRECT_COSTS: [],
    PRIMARY_DIRECT_CONSTRUCTION: [],
}


# Map the legacy flat TransactionCategory value to the new primary key
# so existing classified rows surface the right primary in the UI.
LEGACY_CATEGORY_TO_PRIMARY: dict[str, str] = {
    "tenant_expenses": PRIMARY_TENANT_EXPENSES,
    "land_and_taxes": PRIMARY_LAND_AND_TAXES,
    "indirect_costs": PRIMARY_INDIRECT_COSTS,
    "direct_construction": PRIMARY_DIRECT_CONSTRUCTION,
    "deposit_to_savings": PRIMARY_WITHDRAWALS,
    "loan_repayment": PRIMARY_WITHDRAWALS,
    "interest_and_fees": PRIMARY_INTEREST_FEES_GUARANTEES,
    "other_expense": PRIMARY_INTEREST_FEES_GUARANTEES,
    "sale_income": PRIMARY_RECEIPTS,
    "upgrades_income": PRIMARY_RECEIPTS,
    "other_income": PRIMARY_RECEIPTS,
    "tax_refunds": PRIMARY_DEPOSITS,
    "vat_refunds": PRIMARY_DEPOSITS,
    "equity_deposit": PRIMARY_DEPOSITS,
    "loan_received": PRIMARY_DEPOSITS,
}


def primary_for_category(category: str | None) -> str | None:
    if not category:
        return None
    return LEGACY_CATEGORY_TO_PRIMARY.get(category)


def taxonomy_payload() -> dict:
    """Shape served by GET /api/v1/transactions/taxonomy."""
    return {
        "primaries": [
            {"key": k, "label": v} for k, v in PRIMARY_LABELS.items()
        ],
        "secondaries": PRIMARY_SECONDARIES,
        "legacy_to_primary": LEGACY_CATEGORY_TO_PRIMARY,
    }
