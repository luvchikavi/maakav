"""Chapter 11 - Sources & Uses (מקורות ושימושים)."""

from ..tracking_report import add_rtl_heading, create_rtl_table, format_currency


def add_chapter_11(doc, su_data: dict):
    """Add Chapter 11 - Sources & uses balance."""
    add_rtl_heading(doc, 'פרק 11 - דו"ח מקורות ושימושים', level=1)

    headers = ["סכום בש\"ח", "שימושים", "סכום בש\"ח", "מקורות"]
    rows = [
        [
            format_currency(float(su_data.get("use_payments", 0))),
            "תשלומים",
            format_currency(float(su_data.get("source_equity", 0))),
            "הון עצמי",
        ],
        [
            format_currency(float(su_data.get("use_surplus_release", 0))),
            "החזר הלוואות / שחרור עודפים",
            format_currency(float(su_data.get("source_sales_receipts", 0))),
            "תקבולים ממכירות",
        ],
        [
            "",
            "",
            format_currency(float(su_data.get("source_bank_credit", 0))),
            "אשראי בנקאי / הלוואות",
        ],
        [
            "",
            "",
            format_currency(float(su_data.get("source_vat_refunds", 0))),
            'מע"מ לקבל',
        ],
        [
            format_currency(float(su_data.get("total_uses", 0))),
            'סה"כ שימושים',
            format_currency(float(su_data.get("total_sources", 0))),
            'סה"כ מקורות',
        ],
    ]
    create_rtl_table(doc, headers, rows)
