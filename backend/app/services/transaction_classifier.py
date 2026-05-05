"""
AI Transaction Classifier - auto-suggests categories for bank transactions
using Claude API with project context and category taxonomy.

Called after bank statement upload to pre-classify transactions,
reducing manual work from ~100% to review-only.
"""

import os
import json
import logging
from typing import Dict, List, Optional
import anthropic

logger = logging.getLogger(__name__)

# Category taxonomy with Hebrew labels and common description patterns
CATEGORY_TAXONOMY = {
    "debit": {
        "tenant_expenses": {
            "label": "הוצאות דיירים",
            "patterns": ["דיירים", "בעלים", "פינוי", "שוכרים", "דמי שכירות"],
        },
        "land_and_taxes": {
            "label": "קרקע ומיסוי",
            "patterns": ["מס שבח", "מס רכישה", "היטל השבחה", "ארנונה", "מינהל", "קרקע", "רשות מקרקעין"],
        },
        "indirect_costs": {
            "label": "הוצאות עקיפות",
            "patterns": ["שמאי", "עורך דין", "יועץ", "ניהול", "שיווק", "פרסום", "ביטוח", "רואה חשבון", "אדריכל", "מהנדס", "פיקוח"],
        },
        "direct_construction": {
            "label": "בניה ישירה",
            "patterns": ["קבלן", "בנייה", "בטון", "ברזל", "אלומיניום", "חשמל", "אינסטלציה", "צנרת", "ריצוף", "טיח", "צבע", "גבס", "עבודות"],
        },
        "deposit_to_savings": {
            "label": "הפקדה לפקדון",
            "patterns": ["פקדון", "ערבון", "פיקדון"],
        },
        "loan_repayment": {
            "label": "החזר הלוואה",
            "patterns": ["החזר הלוואה", "החזר משכנתא", "פירעון"],
        },
        "interest_and_fees": {
            "label": "ריביות ועמלות",
            "patterns": ["ריבית", "עמלה", "עמלת", "דמי ניהול חשבון"],
        },
        "other_expense": {
            "label": "הוצאה אחרת",
            "patterns": [],
        },
    },
    "credit": {
        "sale_income": {
            "label": "הכנסה ממכירה",
            "patterns": ["תקבול", "רוכש", "קונה", "מכירה", "דירה", "תשלום רוכש"],
        },
        "tax_refunds": {
            "label": "החזרי מיסים",
            "patterns": ["החזר מס", "מס הכנסה"],
        },
        "vat_refunds": {
            "label": 'החזרי מע"מ',
            "patterns": ["מע\"מ", "מעמ", "החזר מע"],
        },
        "equity_deposit": {
            "label": "הפקדת הון עצמי",
            "patterns": ["הון עצמי", "הפקדת בעלים", "הפקדה מ"],
        },
        "loan_received": {
            "label": "הכנסה מהלוואה",
            "patterns": ["הלוואה", "אשראי", "ליווי"],
        },
        "upgrades_income": {
            "label": "הכנסה משידרוגים",
            "patterns": ["שידרוג", "תוספת", "שינוי דיירים"],
        },
        "other_income": {
            "label": "הכנסה אחרת",
            "patterns": [],
        },
    },
}


# Hebrew bank-statement description patterns sourced from real-world data
# (Maakav user's classification screenshots, May 2026). Each entry maps a
# pattern to (legacy_or_None, primary, secondary). Checked BEFORE the
# coarser legacy CATEGORY_TAXONOMY because these encode both levels at once
# and cover taxonomy items that have no flat legacy equivalent (e.g.
# פירעון פק"מ → deposits / deposit_withdrawal).
EXTENDED_PATTERNS: dict[str, list[tuple[str, str | None, str, str | None]]] = {
    # tx_type → list of (pattern, legacy_category_or_None, primary, secondary)
    "credit": [
        # Buyer payments → receipts
        ("שוברי תשלום", "sale_income", "receipts", "buyer_receipt"),
        ("זיכוי שובר", "sale_income", "receipts", "buyer_receipt"),
        ("זיכוי בגין", "sale_income", "receipts", "buyer_receipt"),
        ("תקבול מרוכש", "sale_income", "receipts", "buyer_receipt"),
        # Loan disbursements → deposits
        ("פתיחת הלוואה", "loan_received", "deposits", "loan_disbursement_senior"),
        ("העמדת הלוואה", "loan_received", "deposits", "loan_disbursement_senior"),
        # Deposit withdrawal (פק"מ) → deposits / deposit_withdrawal
        # Legacy is None because the flat enum has no good fit; we just store
        # the two-level fields. Endpoint code tolerates None legacy.
        ("פירעון פק", None, "deposits", "deposit_withdrawal"),
        ("פירעון פקדון", None, "deposits", "deposit_withdrawal"),
        ("פירעון פיקדון", None, "deposits", "deposit_withdrawal"),
        # VAT refunds → deposits / vat_refund
        ('החזר מע"מ', "vat_refunds", "deposits", "vat_refund"),
        ("החזר מעמ", "vat_refunds", "deposits", "vat_refund"),
        # Equity deposits → deposits / equity_deposit
        ("הפקדת הון עצמי", "equity_deposit", "deposits", "equity_deposit"),
        ("הפקדת בעלים", "equity_deposit", "deposits", "equity_deposit"),
    ],
    "debit": [
        # Interest charges → interest_fees_guarantees / interest_and_fees
        ('ריבית עו"ש', "interest_and_fees", "interest_fees_guarantees", "interest_and_fees"),
        ("ריבית חובה", "interest_and_fees", "interest_fees_guarantees", "interest_and_fees"),
        ("ריבית ", "interest_and_fees", "interest_fees_guarantees", "interest_and_fees"),
        # Guarantee-related fees → interest_fees_guarantees / guarantees
        ("עמלת הארכת ערבות", "interest_and_fees", "interest_fees_guarantees", "guarantees"),
        ("עמלת ערבות חדשה", "interest_and_fees", "interest_fees_guarantees", "guarantees"),
        ("עמלת ערבות", "interest_and_fees", "interest_fees_guarantees", "guarantees"),
        # Generic fees → interest_fees_guarantees / fees
        ("עמלת פעולה", "interest_and_fees", "interest_fees_guarantees", "fees"),
        ("עמלת מנהובים", "interest_and_fees", "interest_fees_guarantees", "fees"),
        ("עמלה ", "interest_and_fees", "interest_fees_guarantees", "fees"),
        ("דמי ניהול חשבון", "interest_and_fees", "interest_fees_guarantees", "fees"),
        ("דמי ניהול קבועים", "interest_and_fees", "interest_fees_guarantees", "fees"),
        ("דמי מינוי לפעולות", "interest_and_fees", "interest_fees_guarantees", "fees"),
        ("דמי קבועים", "interest_and_fees", "interest_fees_guarantees", "fees"),
        ("דמי שינוי", "interest_and_fees", "interest_fees_guarantees", "fees"),
        ("דמי השלמ", "interest_and_fees", "interest_fees_guarantees", "fees"),
        ("השלמת דמי ניהול", "interest_and_fees", "interest_fees_guarantees", "fees"),
        ("rtgs", "interest_and_fees", "interest_fees_guarantees", "fees"),
        # Deposit-to-savings → withdrawals / deposit_to_savings
        ('הוראת הפקדה בפק"מ', "deposit_to_savings", "withdrawals", "deposit_to_savings"),
        ("הוראת הפקדה", "deposit_to_savings", "withdrawals", "deposit_to_savings"),
        ("הפקדה לפקדון", "deposit_to_savings", "withdrawals", "deposit_to_savings"),
        ("הפקדה לפיקדון", "deposit_to_savings", "withdrawals", "deposit_to_savings"),
        # Loan repayment → withdrawals / loan_repayment_*
        ("פירעון הלוואה", "loan_repayment", "withdrawals", "loan_repayment_senior"),
        ("החזר הלוואה", "loan_repayment", "withdrawals", "loan_repayment_senior"),
        ("פרעון הלוואה", "loan_repayment", "withdrawals", "loan_repayment_senior"),
        # VAT payment → withdrawals / vat_payment
        ('תשלום מע"מ', None, "withdrawals", "vat_payment"),
        ("תשלום מעמ", None, "withdrawals", "vat_payment"),
    ],
}


def classify_by_patterns(description: str, tx_type: str) -> Optional[str]:
    """Fast rule-based classification (legacy flat label only).

    Kept for backwards compatibility with callers that still want a single
    label. Prefer :func:`classify_by_patterns_rich` for new code — it
    returns both levels of the new taxonomy.
    """
    rich = classify_by_patterns_rich(description, tx_type)
    return rich.get("legacy") if rich else None


def classify_by_patterns_rich(description: str, tx_type: str) -> Optional[dict]:
    """Returns ``{legacy, primary, secondary}`` for the longest matching pattern,
    consulting ``EXTENDED_PATTERNS`` first (richer mapping) and falling back
    to ``CATEGORY_TAXONOMY`` (coarse, legacy-only).
    """
    desc_lower = description.lower().strip()

    # Phase 1: extended patterns — both levels in one shot.
    best_score = 0
    best: Optional[dict] = None
    for pattern, legacy, primary, secondary in EXTENDED_PATTERNS.get(tx_type, []):
        if pattern.lower() in desc_lower:
            score = len(pattern)
            if score > best_score:
                best_score = score
                best = {"legacy": legacy, "primary": primary, "secondary": secondary}

    if best:
        return best

    # Phase 2: legacy taxonomy fallback. Only legacy is returned; primary
    # is derived later via LEGACY_CATEGORY_TO_PRIMARY in the caller.
    categories = CATEGORY_TAXONOMY.get(tx_type, {})
    for cat_key, cat_info in categories.items():
        for pattern in cat_info["patterns"]:
            if pattern.lower() in desc_lower:
                score = len(pattern)
                if score > best_score:
                    best_score = score
                    best = {"legacy": cat_key, "primary": None, "secondary": None}
    return best


class TransactionClassifierService:
    """AI-powered transaction classifier using Claude API."""

    def __init__(self):
        self._client = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            api_key = os.environ.get('ANTHROPIC_API_KEY', '')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY לא מוגדר")
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def classify_transactions(
        self,
        transactions: List[Dict],
        project_context: str = "",
    ) -> List[Dict]:
        """
        Classify a batch of transactions using AI.

        Args:
            transactions: [{id, description, amount, type}]
            project_context: Optional project info for better classification

        Returns:
            [{id, suggested_category, suggested_primary, suggested_secondary,
              confidence}] — suggested_category is the legacy flat label
            (kept for budget aggregation backwards compat); suggested_primary
            and suggested_secondary feed item A's two-level UI.
        """
        from .transaction_taxonomy import LEGACY_CATEGORY_TO_PRIMARY

        if not transactions:
            return []

        results = []

        # Phase 1: Rule-based classification. Extended patterns return
        # primary+secondary in one shot; legacy fallback returns just the
        # flat key, with primary derived via LEGACY_CATEGORY_TO_PRIMARY.
        unclassified = []
        for tx in transactions:
            rich = classify_by_patterns_rich(tx["description"], tx["type"])
            if rich:
                primary = rich.get("primary") or LEGACY_CATEGORY_TO_PRIMARY.get(rich.get("legacy") or "")
                results.append({
                    "id": tx["id"],
                    "suggested_category": rich.get("legacy"),
                    "suggested_primary": primary,
                    "suggested_secondary": rich.get("secondary"),
                    "confidence": 0.85 if rich.get("primary") else 0.75,
                })
            else:
                unclassified.append(tx)

        # Phase 2: AI classification for remaining
        if unclassified:
            ai_results = self._classify_with_ai(unclassified, project_context)
            results.extend(ai_results)

        return results

    def _classify_with_ai(self, transactions: List[Dict], project_context: str) -> List[Dict]:
        """Use Claude to classify transactions that rules couldn't handle."""
        from .transaction_taxonomy import (
            LEGACY_CATEGORY_TO_PRIMARY,
            PRIMARY_LABELS,
            PRIMARY_SECONDARIES,
        )

        empty = lambda tx: {  # noqa: E731
            "id": tx["id"], "suggested_category": None,
            "suggested_primary": None, "suggested_secondary": None, "confidence": 0,
        }

        try:
            client = self._get_client()
        except ValueError:
            return [empty(tx) for tx in transactions]

        # Build the two-level reference Claude will use.
        primary_lines = []
        for primary_key, primary_label in PRIMARY_LABELS.items():
            secs = PRIMARY_SECONDARIES.get(primary_key) or []
            if secs:
                sec_text = ", ".join(f'{s["key"]} ({s["label"]})' for s in secs)
                primary_lines.append(f"- {primary_key} ({primary_label}) → {sec_text}")
            else:
                primary_lines.append(
                    f"- {primary_key} ({primary_label}) → אין תת-סיווג קבוע "
                    "(סעיף תקציב נבחר ידנית)"
                )

        tx_list = []
        for tx in transactions[:50]:
            tx_list.append(f"ID:{tx['id']} | {tx['type']} | {tx['amount']} | {tx['description']}")

        prompt = f"""אתה מסווג תנועות בנק של פרויקט נדל"ן (בנייה למגורים בישראל).
{f"הקשר הפרויקט: {project_context}" if project_context else ""}

לכל תנועה בחר primary (קטגוריה ראשית) ובמידת האפשר secondary (סעיף משני בתוך הראשית).

קטגוריות ראשיות אפשריות:
- חיוב (debit): tenant_expenses, land_and_taxes, indirect_costs, direct_construction, interest_fees_guarantees, withdrawals
- זכות (credit): receipts, deposits

עבור primary שיש לו תת-סיווגים, החזר את ה-secondary המתאים. עבור 4 הקטגוריות הראשיות של תקציב (tenant_expenses, land_and_taxes, indirect_costs, direct_construction) השאר secondary כ-null — סעיף התקציב נבחר ידנית.

מיפוי:
{chr(10).join(primary_lines)}

החזר JSON בלבד:
[{{"id": 123, "primary": "withdrawals", "secondary": "loan_repayment_senior", "confidence": 0.85}}]

תנועות לסיווג:
{chr(10).join(tx_list)}

החזר JSON בלבד, ללא טקסט נוסף."""

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = response.content[0].text.strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[1]
                if raw.endswith('```'):
                    raw = raw.rsplit('```', 1)[0]

            ai_results = json.loads(raw)

            # Build a reverse map secondary->legacy_category so we can also
            # set the flat 'category' field where it has a 1:1 correspondent.
            primary_to_legacy_default: dict[str, str] = {
                "tenant_expenses": "tenant_expenses",
                "land_and_taxes": "land_and_taxes",
                "indirect_costs": "indirect_costs",
                "direct_construction": "direct_construction",
            }
            secondary_to_legacy: dict[str, str] = {
                "loan_repayment_senior": "loan_repayment",
                "loan_repayment_subordinated": "loan_repayment",
                "deposit_to_savings": "deposit_to_savings",
                "interest_and_fees": "interest_and_fees",
                "fees": "interest_and_fees",
                "guarantees": "interest_and_fees",
                "buyer_receipt": "sale_income",
                "upgrade_receipt": "upgrades_income",
                "non_residential_receipt": "sale_income",
                "other_receipt": "other_income",
                "equity_deposit": "equity_deposit",
                "vat_refund": "vat_refunds",
                "loan_disbursement_senior": "loan_received",
                "loan_disbursement_subordinated": "loan_received",
            }

            out = []
            for r in ai_results:
                primary = r.get("primary")
                secondary = r.get("secondary")
                # Reconcile back to a flat legacy category where possible —
                # falls through to None when the new taxonomy has no flat
                # equivalent (the row will then only carry primary+secondary).
                legacy = (
                    secondary_to_legacy.get(secondary)
                    if secondary
                    else primary_to_legacy_default.get(primary)
                )
                out.append({
                    "id": r["id"],
                    "suggested_category": legacy,
                    "suggested_primary": primary,
                    "suggested_secondary": secondary,
                    "confidence": r.get("confidence", 0.6),
                })
                # Sanity check primary against allowed keys
                if primary and primary not in LEGACY_CATEGORY_TO_PRIMARY.values():
                    logger.warning(f"AI returned unknown primary: {primary}")
            return out
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return [empty(tx) for tx in transactions]


transaction_classifier = TransactionClassifierService()
