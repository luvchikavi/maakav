"""Chapter 7 - Sales (הכנסות / מכירות)."""

from ..tracking_report import add_rtl_heading, add_rtl_paragraph, create_rtl_table, format_currency, format_percent


def add_chapter_7(doc, sales_data: dict):
    """Add Chapter 7 - Sales summary."""
    add_rtl_heading(doc, "פרק 7 - הכנסות", level=1)

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

    # 7.2 Quarterly pace
    quarterly = sales_data.get("quarterly_pace", [])
    if quarterly:
        add_rtl_heading(doc, "7.2 קצב מכירת הדירות", level=2)
        q_headers = ['סה"כ לרבעון', "מכירות", "רבעון"]
        q_rows = [[str(q["net"]), str(q["sold"]), q["quarter"]] for q in quarterly]
        create_rtl_table(doc, q_headers, q_rows)
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

    # Non-linear
    if sales_data.get("non_linear_count", 0) > 0:
        add_rtl_heading(doc, "7.7 מכירות לא ליניאריות", level=2)
        add_rtl_paragraph(
            doc,
            f'קיימות {sales_data["non_linear_count"]} מכירות בהן התקבול האחרון עולה על 40% מסך התמורה.'
        )
