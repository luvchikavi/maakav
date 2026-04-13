"""Chapter 5 - Construction Progress (התקדמות פיזית)."""

from ..utils import add_rtl_heading, add_rtl_paragraph, create_rtl_table, format_currency, format_percent


def add_chapter_5(doc, construction_data: dict, budget_data: dict | None = None):
    """Add Chapter 5 - Construction progress."""
    add_rtl_heading(doc, "פרק 5 - התקדמות פיזית", level=1)

    # 5.1 Physical vs financial execution
    add_rtl_heading(doc, "5.1 אחוזי הביצוע הפיזי אל מול הכספי", level=2)

    physical_pct = construction_data.get("overall_percent", "0")

    # Financial execution from budget (direct construction category)
    financial_pct = "0"
    financial_value = "0"
    if budget_data and "lines" in budget_data:
        for line in budget_data["lines"]:
            if line["category"] == "direct_construction":
                financial_pct = line["execution_percent"]
                financial_value = line["cumulative_actual"]
                break

    headers = ["ערך", "פרט"]
    rows = [
        [format_percent(float(physical_pct)), "אומדן אחוז הביצוע הפיזי"],
        [format_percent(float(financial_pct)), "אחוז ביצוע כספי"],
        [format_currency(float(financial_value)), "שווי ביצוע כספי"],
    ]
    create_rtl_table(doc, headers, rows)

    doc.add_paragraph()

    # 5.2 Description
    add_rtl_heading(doc, "5.2 תיאור עבודות שבוצעו", level=2)
    description = construction_data.get("description_text", "")
    if description:
        add_rtl_paragraph(doc, description)
    else:
        add_rtl_paragraph(doc, "לא הוזן תיאור עבודות")
