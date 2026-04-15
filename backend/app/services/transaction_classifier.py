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


def classify_by_patterns(description: str, tx_type: str) -> Optional[str]:
    """Fast rule-based classification using keyword matching."""
    desc_lower = description.lower().strip()
    categories = CATEGORY_TAXONOMY.get(tx_type, {})

    best_match = None
    best_score = 0

    for cat_key, cat_info in categories.items():
        for pattern in cat_info["patterns"]:
            if pattern in desc_lower:
                score = len(pattern)
                if score > best_score:
                    best_score = score
                    best_match = cat_key

    return best_match


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
            [{id, suggested_category, confidence}]
        """
        if not transactions:
            return []

        results = []

        # Phase 1: Rule-based classification
        unclassified = []
        for tx in transactions:
            pattern_match = classify_by_patterns(tx["description"], tx["type"])
            if pattern_match:
                results.append({
                    "id": tx["id"],
                    "suggested_category": pattern_match,
                    "confidence": 0.75,
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
        try:
            client = self._get_client()
        except ValueError:
            # No API key — return empty suggestions
            return [{"id": tx["id"], "suggested_category": None, "confidence": 0} for tx in transactions]

        # Build category reference
        cat_ref = []
        for tx_type, cats in CATEGORY_TAXONOMY.items():
            for key, info in cats.items():
                cat_ref.append(f"- {key} ({info['label']}) — for {tx_type} transactions")

        tx_list = []
        for tx in transactions[:50]:  # Limit batch size
            tx_list.append(f"ID:{tx['id']} | {tx['type']} | {tx['amount']} | {tx['description']}")

        prompt = f"""אתה מסווג תנועות בנק של פרויקט נדל"ן (בנייה למגורים בישראל).
{f"הקשר הפרויקט: {project_context}" if project_context else ""}

קטגוריות אפשריות:
{chr(10).join(cat_ref)}

סווג כל תנועה. החזר JSON בלבד:
[{{"id": 123, "category": "direct_construction", "confidence": 0.85}}]

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
            return [
                {
                    "id": r["id"],
                    "suggested_category": r.get("category"),
                    "confidence": r.get("confidence", 0.6),
                }
                for r in ai_results
            ]
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return [{"id": tx["id"], "suggested_category": None, "confidence": 0} for tx in transactions]


transaction_classifier = TransactionClassifierService()
