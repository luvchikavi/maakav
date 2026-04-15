"""Chapter 7 - Sales (הכנסות / מכירות)."""

from ..utils import add_rtl_heading, add_rtl_paragraph, create_rtl_table, format_currency, format_percent


def add_chapter_7(doc, sales_data: dict, guarantees_data: dict | None = None):
    """Add Chapter 7 - Sales summary + full list + guarantees."""
    add_rtl_heading(doc, "פרק 7 - הכנסות", level=1)

    # 7.1 Full sales list
    comparison = sales_data.get("report_0_comparison", [])
    if comparison:
        add_rtl_heading(doc, "7.1 רשימת מכירות מלאה", level=2)
        headers = ["הפרש", 'מחיר דוח 0 ללא מע"מ', 'מחיר מכירה ללא מע"מ', "תאריך", "קונה", "דירה", "בניין", "#"]
        rows = []
        for idx, c in enumerate(comparison, 1):
            rows.append([
                format_currency(c["difference"]),
                format_currency(c["report_0_price_no_vat"]),
                format_currency(c["sale_price_no_vat"]),
                c["contract_date"],
                c["buyer_name"],
                c.get("unit_number", ""),
                c.get("building", ""),
                str(idx),
            ])
        # Totals row
        total_sale = sum(c["sale_price_no_vat"] for c in comparison)
        total_r0 = sum(c["report_0_price_no_vat"] for c in comparison)
        rows.append([
            format_currency(total_sale - total_r0),
            format_currency(total_r0),
            format_currency(total_sale),
            "", "", "", "",
            'סה"כ',
        ])
        create_rtl_table(doc, headers, rows)
        doc.add_paragraph()

    # 7.2 Quarterly pace
    quarterly = sales_data.get("quarterly_pace", [])
    if quarterly:
        add_rtl_heading(doc, "7.2 קצב מכירת הדירות", level=2)
        q_headers = ['סה"כ לרבעון', "מכירות", "רבעון"]
        q_rows = [[str(q["net"]), str(q["sold"]), q["quarter"]] for q in quarterly]
        create_rtl_table(doc, q_headers, q_rows)
        doc.add_paragraph()

    # 7.3 Sales summary
    add_rtl_heading(doc, "7.3 ריכוז נתוני מכירות", level=2)

    headers = ["אחוז", "כמות", "פרט"]
    rows = [
        [
            "100%",
            str(sales_data.get("total_developer_units", 0)),
            'מס\' יח"ד יזם',
        ],
        [
            format_percent(sales_data.get("sold_percent", 0)),
            str(sales_data.get("total_sold", 0)),
            'חוזים חתומים במצטבר',
        ],
        [
            format_percent(sales_data.get("recognized_percent", 0)),
            str(sales_data.get("recognized_by_bank", 0)),
            'מכירות מוכרות (תקבולים >15%)',
        ],
        [
            "",
            str(sales_data.get("unsold", 0)),
            "יתרה למכירה",
        ],
    ]
    create_rtl_table(doc, headers, rows)

    doc.add_paragraph()

    # 7.5 Arrears
    arrears = sales_data.get("arrears", [])
    if arrears:
        add_rtl_heading(doc, "7.5 פיגורי רוכשים", level=2)
        a_headers = ['סכום פיגור ללא מע"מ', "שם הרוכש"]
        a_rows = [[format_currency(a["overdue_amount"]), a["buyer_name"]] for a in arrears]
        a_rows.append([format_currency(sales_data.get("arrears_total", 0)), 'סה"כ'])
        create_rtl_table(doc, a_headers, a_rows)
        doc.add_paragraph()

    # 7.6 Guarantees
    if guarantees_data and guarantees_data.get("items"):
        add_rtl_heading(doc, "7.6 מצב ערבויות", level=2)
        g_headers = ["יתרה צמודה", "סכום מקורי", "תוקף", "דירה", "סוג", "מוטב"]
        type_labels = {
            "sale_law": "חוק מכר", "performance": "ביצוע",
            "financial": "כספית", "bank": "בנקאית", "other": "אחר",
        }
        g_rows = []
        for item in guarantees_data["items"]:
            g_rows.append([
                format_currency(item.get("indexed_balance", 0)),
                format_currency(item.get("original_amount", 0)),
                item.get("expiry_date", "") or "—",
                item.get("apartment_number", "") or "—",
                type_labels.get(item.get("guarantee_type", ""), item.get("guarantee_type", "")),
                item.get("buyer_name", ""),
            ])
        g_rows.append([
            format_currency(guarantees_data.get("total_balance", 0)),
            "", "", "", "",
            'סה"כ ערבויות',
        ])
        create_rtl_table(doc, g_headers, g_rows)
        doc.add_paragraph()

    # 7.7 Non-linear
    if sales_data.get("non_linear_count", 0) > 0:
        add_rtl_heading(doc, "7.7 מכירות לא ליניאריות", level=2)
        add_rtl_paragraph(
            doc,
            f'קיימות {sales_data["non_linear_count"]} מכירות בהן התקבול האחרון עולה על 40% מסך התמורה.'
        )
