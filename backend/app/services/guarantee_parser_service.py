"""
Guarantee Statement Parser - Uses Claude Vision to extract guarantee items from bank guarantee documents.

Supports:
- PDF guarantee statements (converted to images)
- Excel guarantee reports

Extracts per item:
- Buyer/beneficiary name
- Guarantee type (חוק מכר, ביצוע, כספית, בנקאית)
- Original amount
- Indexed balance
- Expiry/end date
- Apartment number (if applicable)
"""
import os
import base64
import json
import logging
import tempfile
from typing import Dict, List, Any
from datetime import datetime
from decimal import Decimal
import anthropic

logger = logging.getLogger(__name__)

GUARANTEE_TYPE_MAP = {
    'ערבות חוק מכר': 'sale_law',
    'חוק מכר': 'sale_law',
    'ערבות ביצוע': 'performance',
    'ביצוע': 'performance',
    'ערבות כספית': 'financial',
    'כספית': 'financial',
    'ערבות בנקאית': 'bank',
    'בנקאית': 'bank',
}

GUARANTEE_TYPE_LABELS = {
    'sale_law': 'חוק מכר',
    'performance': 'ביצוע',
    'financial': 'כספית',
    'bank': 'בנקאית',
    'other': 'אחר',
}


class GuaranteeParserService:
    """AI-powered guarantee document parser using Claude Vision."""

    def __init__(self):
        self._client = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            api_key = os.environ.get('ANTHROPIC_API_KEY', '')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY לא מוגדר")
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def parse_guarantee_file(
        self, file_content: bytes, file_type: str, filename: str,
    ) -> Dict[str, Any]:
        """
        Parse a guarantee statement and return structured items.

        Returns:
            {
                "items": [
                    {
                        "buyer_name": "ישראל ישראלי",
                        "guarantee_type": "sale_law",
                        "original_amount": 500000,
                        "indexed_balance": 520000,
                        "expiry_date": "2026-12-31",
                        "apartment_number": "12",
                        "notes": ""
                    }, ...
                ],
                "total_balance": 2600000,
                "warnings": []
            }
        """
        if file_type in [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ]:
            return self._parse_excel(file_content, filename)
        elif file_type == 'application/pdf':
            return self._parse_pdf(file_content, filename)
        else:
            raise ValueError(f"סוג קובץ לא נתמך: {file_type}")

    def _parse_excel(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Parse Excel guarantee report."""
        import openpyxl
        import io

        wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
        ws = wb.active

        # Try to find header row by scanning first 10 rows
        header_row = None
        header_map: Dict[str, int] = {}
        keywords = ['מוטב', 'שם', 'סוג', 'סכום', 'יתרה', 'תאריך', 'דירה', 'ערבות']

        for row_idx in range(1, min(ws.max_row + 1, 15)):
            cells = [str(ws.cell(row=row_idx, column=c).value or '').strip() for c in range(1, ws.max_column + 1)]
            matches = sum(1 for cell in cells for kw in keywords if kw in cell)
            if matches >= 2:
                header_row = row_idx
                for col_idx, cell_val in enumerate(cells):
                    header_map[cell_val.lower()] = col_idx
                break

        if header_row is None:
            # Fall back to AI parsing
            return self._parse_with_ai(file_content, filename, 'excel')

        # Map columns
        def find_col(*terms: str):
            for h, idx in header_map.items():
                for t in terms:
                    if t in h:
                        return idx
            return None

        buyer_col = find_col('מוטב', 'שם', 'רוכש', 'לקוח')
        type_col = find_col('סוג', 'ערבות')
        amount_col = find_col('סכום', 'קרן', 'מקור')
        balance_col = find_col('יתרה', 'צמוד')
        date_col = find_col('תוקף', 'תאריך סיום', 'פקיעה')
        apt_col = find_col('דירה', 'יחידה', 'נכס')

        items = []
        warnings = []
        total = Decimal('0')

        for row_idx in range(header_row + 1, ws.max_row + 1):
            row = [ws.cell(row=row_idx, column=c).value for c in range(1, ws.max_column + 1)]
            if all(v is None for v in row):
                continue

            buyer = str(row[buyer_col]).strip() if buyer_col is not None and row[buyer_col] else ''
            if not buyer or buyer == 'None':
                continue

            raw_type = str(row[type_col]).strip() if type_col is not None and row[type_col] else ''
            g_type = 'other'
            for key, val in GUARANTEE_TYPE_MAP.items():
                if key in raw_type:
                    g_type = val
                    break

            orig = self._to_decimal(row[amount_col] if amount_col is not None else None)
            bal = self._to_decimal(row[balance_col] if balance_col is not None else None) or orig
            total += bal

            expiry = None
            if date_col is not None and row[date_col]:
                expiry = self._parse_date(row[date_col])

            apt_num = str(row[apt_col]).strip() if apt_col is not None and row[apt_col] else ''
            if apt_num == 'None':
                apt_num = ''

            items.append({
                'buyer_name': buyer,
                'guarantee_type': g_type,
                'original_amount': float(orig),
                'indexed_balance': float(bal),
                'expiry_date': expiry,
                'apartment_number': apt_num,
                'notes': '',
            })

        return {'items': items, 'total_balance': float(total), 'warnings': warnings}

    def _parse_pdf(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Parse PDF guarantee via Claude Vision."""
        return self._parse_with_ai(file_content, filename, 'pdf')

    def _parse_with_ai(self, file_content: bytes, filename: str, source: str) -> Dict[str, Any]:
        """Use Claude Vision to parse guarantee document."""
        client = self._get_client()

        if source == 'pdf':
            content_block = {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.standard_b64encode(file_content).decode("utf-8"),
                },
            }
        else:
            # For Excel, convert to text representation
            import openpyxl
            import io
            wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
            ws = wb.active
            rows_text = []
            for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 100), values_only=True):
                rows_text.append(' | '.join(str(c or '') for c in row))
            content_block = {
                "type": "text",
                "text": f"Excel file contents:\n" + '\n'.join(rows_text),
            }

        prompt = """אתה מנתח תדפיס ערבויות בנקאיות של פרויקט נדל"ן.

חלץ את כל הערבויות מהמסמך בפורמט JSON הבא:
{
    "items": [
        {
            "buyer_name": "שם המוטב/רוכש",
            "guarantee_type": "sale_law|performance|financial|bank|other",
            "original_amount": 500000,
            "indexed_balance": 520000,
            "expiry_date": "2026-12-31",
            "apartment_number": "12",
            "notes": ""
        }
    ],
    "total_balance": 2600000,
    "warnings": ["אזהרה כלשהי"]
}

סוגי ערבויות:
- sale_law = ערבות חוק מכר
- performance = ערבות ביצוע
- financial = ערבות כספית
- bank = ערבות בנקאית
- other = אחר

החזר JSON בלבד, ללא טקסט נוסף."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [content_block, {"type": "text", "text": prompt}],
            }],
        )

        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1]
            if raw.endswith('```'):
                raw = raw.rsplit('```', 1)[0]

        try:
            result = json.loads(raw)
            return {
                'items': result.get('items', []),
                'total_balance': result.get('total_balance', 0),
                'warnings': result.get('warnings', []),
            }
        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI response: {raw[:200]}")
            return {'items': [], 'total_balance': 0, 'warnings': ['שגיאה בפענוח תגובת AI']}

    @staticmethod
    def _to_decimal(val) -> Decimal:
        if val is None:
            return Decimal('0')
        try:
            cleaned = str(val).replace(',', '').replace('₪', '').strip()
            return Decimal(cleaned)
        except Exception:
            return Decimal('0')

    @staticmethod
    def _parse_date(val) -> str | None:
        if val is None:
            return None
        if isinstance(val, datetime):
            return val.strftime('%Y-%m-%d')
        if hasattr(val, 'strftime'):
            return val.strftime('%Y-%m-%d')
        s = str(val).strip()
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d.%m.%Y', '%d-%m-%Y'):
            try:
                return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        return None


guarantee_parser = GuaranteeParserService()
