"""Chapter 4 - Budget Tracking (תקציב הפרויקט / נספח א')."""

from ..utils import add_rtl_heading, add_rtl_paragraph, create_rtl_table, format_currency, format_percent

CATEGORY_LABELS = {
    "tenant_expenses": "קרקע והוצאות דיירים",
    "land_and_taxes": "קרקע ומיסוי",
    "indirect_costs": "כלליות",
    "direct_construction": "הקמה",
    "extraordinary": "הוצאות חריגות",
}


def add_chapter_4(doc, budget_data: dict, report_data: dict):
    """Add Chapter 4 - Budget tracking table."""
    add_rtl_heading(doc, "פרק 4 - תקציב הפרויקט", level=1)

    # 4.1 Index data
    add_rtl_heading(doc, "4.1 נתוני מדדים", level=2)
    index_headers = ["מדד תשומות בנייה", "חודש", "מדד בסיס/קובע"]
    index_rows = [
        [str(budget_data.get("base_index", "")), "דו\"ח אפס", "מדד בסיס (דו\"ח אפס)"],
        [str(budget_data.get("current_index", "")), str(report_data.get("report_month", "")), "מדד דו\"ח נוכחי"],
    ]
    create_rtl_table(doc, index_headers, index_rows)

    doc.add_paragraph()

    # 4.2 Expense summary table
    add_rtl_heading(doc, 'פירוט הוצאות (בש"ח, ללא מע"מ) .4.2', level=2)

    headers = [
        "אחוז תשלום",
        'סה"כ תקציב',
        "יתרה משוערכת",
        "שולם מצטבר נוכחי",
        'שולם חודש הדו"ח',
        'מצטבר עד הדו"ח',
        "סעיף",
    ]

    rows = []
    lines = budget_data.get("lines", [])
    for line in lines:
        cat_label = CATEGORY_LABELS.get(line["category"], line["category"])
        rows.append([
            format_percent(float(line["execution_percent"])),
            format_currency(float(line["total_indexed"])),
            format_currency(float(line["remaining_indexed"])),
            format_currency(float(line["cumulative_actual"])),
            format_currency(float(line["monthly_paid_actual"])),
            format_currency(float(line.get("cumulative_actual", 0)) - float(line.get("monthly_paid_actual", 0))),
            cat_label,
        ])

    # Total row
    total_cum = sum(float(l["cumulative_actual"]) for l in lines)
    total_monthly = sum(float(l["monthly_paid_actual"]) for l in lines)
    total_remaining = sum(float(l["remaining_indexed"]) for l in lines)
    total_budget = sum(float(l["total_indexed"]) for l in lines)
    total_pct = (total_cum / total_budget * 100) if total_budget > 0 else 0

    rows.append([
        format_percent(total_pct),
        format_currency(total_budget),
        format_currency(total_remaining),
        format_currency(total_cum),
        format_currency(total_monthly),
        format_currency(total_cum - total_monthly),
        'סה"כ בפרויקט',
    ])

    create_rtl_table(doc, headers, rows)
