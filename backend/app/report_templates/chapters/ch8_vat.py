"""Chapter 8 - VAT Tracking (מעקב מע"מ)."""

from ..utils import add_rtl_heading, create_rtl_table, format_currency


def add_chapter_8(doc, vat_data: dict):
    """Add Chapter 8 - VAT tracking."""
    add_rtl_heading(doc, 'פרק 8 - מעקב מע"מ', level=1)

    headers = ["סכום", "פרט"]
    rows = [
        [format_currency(float(vat_data.get("transactions_total", 0))), "עסקאות (הכנסות)"],
        [format_currency(float(vat_data.get("output_vat", 0))), 'מע"מ עסקאות'],
        [format_currency(float(vat_data.get("inputs_total", 0))), "תשומות (הוצאות)"],
        [format_currency(float(vat_data.get("input_vat", 0))), 'מע"מ תשומות'],
        [format_currency(float(vat_data.get("vat_balance", 0))), "יתרה חודשית (לקבל / לשלם)"],
        [format_currency(float(vat_data.get("cumulative_vat_balance", 0))), "יתרה מצטברת"],
    ]
    create_rtl_table(doc, headers, rows)
