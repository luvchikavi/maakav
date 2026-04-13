"""
Tracking Report Generator - produces Word (docx) document
matching the Israeli banking standard monitoring report format.
"""

import io
from docx import Document

from .utils import setup_rtl_document, add_rtl_heading, add_rtl_paragraph
from .chapters.ch4_budget import add_chapter_4
from .chapters.ch5_construction import add_chapter_5
from .chapters.ch7_sales import add_chapter_7
from .chapters.ch8_vat import add_chapter_8
from .chapters.ch9_equity import add_chapter_9
from .chapters.ch10_profitability import add_chapter_10
from .chapters.ch11_sources_uses import add_chapter_11


def generate_tracking_report(
    project_data: dict,
    report_data: dict,
    calc_results: dict,
) -> io.BytesIO:
    """Generate the full tracking report as a Word document."""
    doc = Document()
    setup_rtl_document(doc)

    # Cover page
    doc.add_paragraph()
    add_rtl_heading(doc, f'דו"ח מעקב מס\' {report_data["report_number"]}', level=1)
    add_rtl_paragraph(doc, f'ליום {report_data["report_month"]}', size=14)
    add_rtl_paragraph(doc, f'פרויקט: {project_data["project_name"]}', size=14, bold=True)
    if project_data.get("address"):
        add_rtl_paragraph(doc, f'{project_data["address"]}, {project_data.get("city", "")}', size=12)
    if project_data.get("developer_name"):
        add_rtl_paragraph(doc, f'היזם: {project_data["developer_name"]}', size=12)

    doc.add_page_break()

    if "budget_tracking" in calc_results:
        add_chapter_4(doc, calc_results["budget_tracking"], report_data)
        doc.add_page_break()

    if "construction" in calc_results:
        add_chapter_5(doc, calc_results["construction"], calc_results.get("budget_tracking"))
        doc.add_page_break()

    if "sales" in calc_results:
        add_chapter_7(doc, calc_results["sales"])
        doc.add_page_break()

    if "vat" in calc_results:
        add_chapter_8(doc, calc_results["vat"])

    if "equity" in calc_results:
        add_chapter_9(doc, calc_results["equity"])
        doc.add_page_break()

    if "profitability" in calc_results:
        add_chapter_10(doc, calc_results["profitability"])

    if "sources_uses" in calc_results:
        add_chapter_11(doc, calc_results["sources_uses"])

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
