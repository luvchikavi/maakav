"""Chapter 9 - Equity (הון עצמי)."""

from ..utils import add_rtl_heading, create_rtl_table, format_currency


def add_chapter_9(doc, equity_data: dict):
    """Add Chapter 9 - Equity balance + detail history."""
    add_rtl_heading(doc, "פרק 9 - הון עצמי מצטבר", level=1)

    # 9.1 Summary
    add_rtl_heading(doc, "9.1 סיכום הון עצמי", level=2)
    headers = ["סכום", "פרט"]
    rows = [
        [format_currency(float(equity_data.get("required_amount", 0))), "הון עצמי נדרש"],
        [format_currency(float(equity_data.get("total_deposits", 0))), "הפקדות מצטבר"],
        [format_currency(float(equity_data.get("total_withdrawals", 0))), "משיכות מצטבר"],
        [format_currency(float(equity_data.get("current_balance", 0))), "הון עצמי נוכחי"],
        [format_currency(float(equity_data.get("gap", 0))), "עודף / (חסר)"],
    ]
    create_rtl_table(doc, headers, rows)

    # 9.2 Per-report detail
    history = equity_data.get("history", [])
    if history:
        doc.add_paragraph()
        add_rtl_heading(doc, "9.2 פירוט הפקדות/משיכות לפי דוח", level=2)
        h_headers = ["יתרה מצטברת", "משיכות", "הפקדות", "מספר דוח"]
        h_rows = []
        for h in history:
            h_rows.append([
                format_currency(float(h.get("balance", 0))),
                format_currency(float(h.get("withdrawals", 0))),
                format_currency(float(h.get("deposits", 0))),
                str(h.get("report_number", "")),
            ])
        create_rtl_table(doc, h_headers, h_rows)
