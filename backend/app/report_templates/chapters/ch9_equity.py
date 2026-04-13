"""Chapter 9 - Equity (הון עצמי)."""

from ..tracking_report import add_rtl_heading, create_rtl_table, format_currency


def add_chapter_9(doc, equity_data: dict):
    """Add Chapter 9 - Equity balance."""
    add_rtl_heading(doc, "פרק 9 - הון עצמי מצטבר", level=1)

    headers = ["סכום", "פרט"]
    rows = [
        [format_currency(float(equity_data.get("required_amount", 0))), "הון עצמי נדרש"],
        [format_currency(float(equity_data.get("total_deposits", 0))), "הפקדות מצטבר"],
        [format_currency(float(equity_data.get("total_withdrawals", 0))), "משיכות מצטבר"],
        [format_currency(float(equity_data.get("current_balance", 0))), "הון עצמי נוכחי"],
        [format_currency(float(equity_data.get("gap", 0))), "עודף / (חסר)"],
    ]
    create_rtl_table(doc, headers, rows)
