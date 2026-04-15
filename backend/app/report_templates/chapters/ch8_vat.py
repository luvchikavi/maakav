"""Chapter 8 - VAT Tracking (מעקב מע"מ)."""

from ..utils import add_rtl_heading, add_rtl_paragraph, create_rtl_table, format_currency


def add_chapter_8(doc, vat_data: dict, vat_history: list | None = None):
    """Add Chapter 8 - VAT tracking with optional monthly history."""
    add_rtl_heading(doc, 'פרק 8 - מעקב מע"מ', level=1)

    # 8.1 Current month summary
    add_rtl_heading(doc, "8.1 סיכום חודש נוכחי", level=2)
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

    # 8.2 Monthly VAT history
    if vat_history and len(vat_history) > 1:
        doc.add_paragraph()
        add_rtl_heading(doc, 'מעקב מע"מ חודשי .8.2', level=2)
        h_headers = [
            "יתרה מצטברת",
            "יתרה חודשית",
            'מע"מ תשומות',
            "תשומות",
            'מע"מ עסקאות',
            "עסקאות",
            "חודש",
        ]
        h_rows = []
        for v in vat_history:
            month_str = v.get("month", "")
            # Format month as MM/YYYY
            if len(month_str) >= 7:
                month_str = f"{month_str[5:7]}/{month_str[:4]}"
            h_rows.append([
                format_currency(float(v.get("cumulative_vat_balance", 0))),
                format_currency(float(v.get("vat_balance", 0))),
                format_currency(float(v.get("input_vat", 0))),
                format_currency(float(v.get("inputs_total", 0))),
                format_currency(float(v.get("output_vat", 0))),
                format_currency(float(v.get("transactions_total", 0))),
                month_str,
            ])
        create_rtl_table(doc, h_headers, h_rows)
