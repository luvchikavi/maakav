"""Chapter 10 - Profitability (רווחיות)."""

from ..utils import add_rtl_heading, create_rtl_table, format_currency, format_percent


def add_chapter_10(doc, prof_data: dict):
    """Add Chapter 10 - Profitability comparison."""
    add_rtl_heading(doc, "פרק 10 - רווחיות הפרויקט", level=1)

    headers = ['דו"ח נוכחי', 'דו"ח אפס', "פרט"]
    rows = [
        [
            format_currency(float(prof_data.get("income_current", 0))),
            format_currency(float(prof_data.get("income_report_0", 0))),
            'הכנסות (ללא מע"מ)',
        ],
        [
            format_currency(float(prof_data.get("cost_current", 0))),
            format_currency(float(prof_data.get("cost_report_0", 0))),
            'עלויות (ללא מע"מ)',
        ],
        [
            format_currency(float(prof_data.get("profit_current", 0))),
            format_currency(float(prof_data.get("profit_report_0", 0))),
            "רווח",
        ],
        [
            format_percent(float(prof_data.get("profit_percent_current", 0))),
            format_percent(float(prof_data.get("profit_percent_report_0", 0))),
            "רווח לעלות (%)",
        ],
    ]
    create_rtl_table(doc, headers, rows)
