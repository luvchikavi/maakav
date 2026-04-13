"""Shared constants - Israeli banks, categories, etc."""

ISRAELI_BANKS = {
    "leumi": "בנק לאומי",
    "hapoalim": "בנק הפועלים",
    "discount": "בנק דיסקונט",
    "mizrahi": "בנק מזרחי טפחות",
    "international": "הבנק הבינלאומי",
    "jerusalem": "בנק ירושלים",
    "yahav": "בנק יהב",
    "otsar": "בנק אוצר החיל",
    "massad": "בנק מסד",
    "other": "אחר",
}

TRANSACTION_CATEGORY_LABELS = {
    "tenant_expenses": "הוצאות דיירים",
    "land_and_taxes": "קרקע ומיסוי",
    "indirect_costs": "הוצאות עקיפות",
    "direct_construction": "בניה ישירה",
    "deposit_to_savings": "הפקדה לפקדון",
    "other_expense": "הוצאה אחרת",
    "sale_income": "הכנסה ממכירה",
    "tax_refunds": "החזרי מיסים",
    "vat_refunds": 'החזרי מע"מ',
    "equity_deposit": "הפקדת הון עצמי",
    "upgrades_income": "הכנסה משידרוגים",
    "loan_received": "הכנסה מהלוואה",
    "other_income": "הכנסה אחרת",
    "loan_repayment": "החזר הלוואה",
    "interest_and_fees": "ריביות ועמלות",
}

BUDGET_CATEGORY_LABELS = {
    "tenant_expenses": "קרקע והוצאות דיירים",
    "land_and_taxes": "קרקע ומיסוי",
    "indirect_costs": "כלליות",
    "direct_construction": "הקמה (בניה ישירה)",
    "extraordinary": "הוצאות חריגות",
}

MONTH_NAMES_HE = [
    "", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
]
