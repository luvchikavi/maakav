"""
Bank Statement AI Parser - Uses Claude Vision to extract transactions from bank statements

Supports:
- PDF bank statements (converted to images)
- Image files (PNG, JPG)
- Excel files (parsed directly)

Extracts:
- Bank name and account number
- Statement date range
- All transactions (date, description, amount, balance, type)
"""
import os
import base64
import json
import logging
import tempfile
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal
import anthropic

logger = logging.getLogger(__name__)


# Israeli bank identifiers
ISRAELI_BANKS = {
    'לאומי': 'LEUMI',
    'leumi': 'LEUMI',
    'הפועלים': 'HAPOALIM',
    'poalim': 'HAPOALIM',
    'דיסקונט': 'DISCOUNT',
    'discount': 'DISCOUNT',
    'מזרחי': 'MIZRAHI',
    'mizrahi': 'MIZRAHI',
    'טפחות': 'MIZRAHI',
    'הבינלאומי': 'INTERNATIONAL',
    'fibi': 'INTERNATIONAL',
    'אוצר החייל': 'OTSAR',
    'otsar': 'OTSAR',
    'מרכנתיל': 'MERCANTILE',
    'mercantile': 'MERCANTILE',
    'יהב': 'YAHAV',
    'yahav': 'YAHAV',
}


class BankStatementAIParser:
    """
    AI-powered bank statement parser using Claude's vision capabilities.
    """

    def __init__(self):
        self._api_key = None
        self._client = None

    @property
    def api_key(self):
        """Lazy-load API key from environment"""
        if self._api_key is None:
            self._api_key = os.environ.get('ANTHROPIC_API_KEY', '')
            if not self._api_key:
                logger.warning("ANTHROPIC_API_KEY not set - Bank Statement AI Parser will not work")
        return self._api_key

    def _get_client(self) -> anthropic.Anthropic:
        """Get or create Anthropic client"""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY לא מוגדר - לא ניתן לנתח דפי חשבון עם AI. "
                    "יש להגדיר את המשתנה ANTHROPIC_API_KEY בסביבה."
                )
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def parse_bank_statement(
        self,
        file_content: bytes,
        file_type: str,
        filename: str
    ) -> Dict[str, Any]:
        """
        Parse a bank statement file and extract all information.

        Args:
            file_content: The raw file content (bytes)
            file_type: MIME type of the file (application/pdf, image/png, etc.)
            filename: Original filename

        Returns:
            Dict with extracted data:
            {
                "bank": "LEUMI",
                "bank_display": "בנק לאומי",
                "account_number": "123456789",
                "statement_start_date": "2025-01-01",
                "statement_end_date": "2025-01-31",
                "transactions": [
                    {
                        "date": "2025-01-05",
                        "description": "העברה מחשבון",
                        "amount": 5000.00,
                        "balance": 15000.00,
                        "type": "CREDIT"  # or "DEBIT"
                    },
                    ...
                ],
                "total_credits": 50000.00,
                "total_debits": 30000.00,
                "opening_balance": 10000.00,
                "closing_balance": 30000.00,
                "confidence": 0.95,
                "warnings": []
            }
        """
        if file_type == 'application/pdf':
            return self._parse_pdf(file_content, filename)
        elif file_type.startswith('image/'):
            return self._parse_image(file_content, file_type)
        elif file_type in ['application/vnd.ms-excel',
                          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
            return self._parse_excel(file_content, filename)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _parse_pdf(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Parse a PDF bank statement — text extraction first, AI vision fallback."""
        import re
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ValueError("PyMuPDF is not installed. pip install pymupdf")

        doc = fitz.open(stream=file_content, filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()

        # If the PDF has meaningful text, parse deterministically (no AI needed)
        if len(full_text.strip()) > 100:
            try:
                result = self._parse_pdf_text(full_text, filename)
                if result and result.get('transactions'):
                    logger.info(f"PDF text parser extracted {len(result['transactions'])} transactions")
                    return self._calculate_totals(result)
            except Exception as e:
                logger.warning(f"PDF text parser failed: {e}")

        # Fallback: scanned PDF → convert to images + Claude Vision
        logger.info("PDF has no extractable text, falling back to AI vision")
        return self._parse_pdf_with_vision(file_content, filename)

    def _parse_pdf_text(self, text: str, filename: str) -> Dict[str, Any]:
        """Deterministic parser for Israeli bank statement PDFs with extractable text."""
        import re

        bank_code, bank_display = self._detect_bank_from_content(text)
        account_number = self._extract_account_number(text, bank_code)
        date_range = self._extract_date_range(text)

        transactions = []

        if bank_code in ('DISCOUNT', 'MERCANTILE'):
            transactions = self._parse_discount_pdf_text(text)
        elif bank_code == 'LEUMI':
            transactions = self._parse_leumi_pdf_text(text)
        elif bank_code == 'JERUSALEM':
            transactions = self._parse_jerusalem_pdf_text(text)
        elif bank_code == 'MIZRAHI':
            transactions = self._parse_mizrahi_pdf_text(text)
        elif bank_code == 'INTERNATIONAL':
            transactions = self._parse_fibi_pdf_text(text)
        else:
            # Generic: try all patterns
            for parser in [
                self._parse_discount_pdf_text,
                self._parse_leumi_pdf_text,
                self._parse_jerusalem_pdf_text,
                self._parse_mizrahi_pdf_text,
                self._parse_fibi_pdf_text,
            ]:
                transactions = parser(text)
                if transactions:
                    break

        start_date = date_range[0] if date_range else None
        end_date = date_range[1] if date_range else None
        if transactions and not start_date:
            dates = [t['date'] for t in transactions if t.get('date')]
            if dates:
                start_date = min(dates)
                end_date = max(dates)

        opening_balance = None
        closing_balance = None
        for t in transactions:
            if t.get('balance') and t['balance'] != 0:
                if opening_balance is None:
                    opening_balance = t['balance']
                closing_balance = t['balance']

        return {
            'bank': bank_code,
            'bank_display': bank_display,
            'account_number': account_number,
            'statement_start_date': start_date,
            'statement_end_date': end_date,
            'opening_balance': opening_balance,
            'closing_balance': closing_balance,
            'transactions': transactions,
            'confidence': 0.90,
            'warnings': ['Parsed from PDF text (no AI)'],
        }

    def _parse_discount_pdf_text(self, text: str) -> List[Dict]:
        """Parse Discount/Mercantile PDF format.
        Pattern: date\\nvalue_date\\ndescription+ref\\namount\\nbalance
        Amount is signed: negative=debit, positive=credit.
        """
        import re
        transactions = []
        # Match: DD/MM/YYYY followed by another date, description, signed amount, balance
        # Discount format has lines like:
        #   11/08/2025\n11/08/2025\n09700992682 דמי טיפול559\n-50.00\n515,841.57
        pattern = re.compile(
            r'(\d{2}/\d{2}/\d{4})\n'           # transaction date
            r'\d{2}/\d{2}/\d{4}\n'              # value date (skip)
            r'(.+?)\n'                          # description
            r'(-?[\d,]+\.?\d*)\n'               # amount (signed)
            r'(-?[\d,]+\.?\d*)',                 # balance
        )
        for m in pattern.finditer(text):
            date_str = self._parse_date_str(m.group(1))
            description = m.group(2).strip()
            amount = float(m.group(3).replace(',', ''))
            balance = float(m.group(4).replace(',', ''))
            tx_type = 'CREDIT' if amount >= 0 else 'DEBIT'
            transactions.append(self._normalize_transaction({
                'date': date_str,
                'description': description,
                'amount': amount,
                'balance': balance,
                'type': tx_type,
            }))
        return transactions

    def _parse_leumi_pdf_text(self, text: str) -> List[Dict]:
        """Parse Leumi PDF format.
        Pattern: DD.MM.YYYYdescription₪ amount\\n₪ balance
        Amounts in חובה column = debit, amounts in זכות column = credit.
        """
        import re
        transactions = []
        # Leumi: "05.10.2025העמדת הלואה₪ 40,800.00\n₪ 32,482.87"
        # Or:    "05.10.2025עמ.גל"י לבנקים₪ 1.73\n₪ 32,481.14"
        pattern = re.compile(
            r'(\d{2}\.\d{2}\.\d{4})'            # date
            r'(.+?)'                             # description
            r'₪\s*([\d,]+\.?\d*)\n'              # amount
            r'₪\s*(-?[\d,]+\.?\d*)',             # balance
        )

        # Detect which column headers appear to determine debit/credit
        # Leumi has "חובה" and "זכות" headers
        has_debit_credit = 'חובה' in text and 'זכות' in text

        for m in pattern.finditer(text):
            date_str = self._parse_date_str(m.group(1))
            description = m.group(2).strip()
            amount = float(m.group(3).replace(',', ''))
            balance = float(m.group(4).replace(',', ''))

            # In Leumi, the amount position determines type
            # But from text extraction, we can't distinguish columns reliably
            # Use balance change to determine: if balance went down, it's debit
            tx_type = 'DEBIT'  # default
            transactions.append(self._normalize_transaction({
                'date': date_str,
                'description': description,
                'amount': -amount,  # Mark as negative initially
                'balance': balance,
                'type': tx_type,
            }))

        # Fix debit/credit using balance changes
        self._fix_types_from_balance(transactions)
        return transactions

    def _parse_jerusalem_pdf_text(self, text: str) -> List[Dict]:
        """Parse Jerusalem bank PDF format.
        Columns (RTL): date, description, reference, debit, credit, balance
        Text extraction gives: balance, credit, debit, [reference lines], description+date
        """
        import re
        transactions = []
        # Jerusalem text has: " 2,487,421.87 \n0.00\n66,338.19\n0510474034אמפא קפיטל29.07.2025"
        # Or with extra ref: " 214,126.21 \n153,521.29\n0.00\n0000000002\n0001070404 פרטי שובר10.08.2025"
        # Pattern: balance\ncredit\ndebit\n[optional ref lines]\ndescription+date
        pattern = re.compile(
            r'\s([\d,]+\.?\d{2})\s*\n'           # balance (with leading space)
            r'([\d,]+\.?\d{2})\n'                # credit
            r'([\d,]+\.?\d{2})\n'                # debit
            r'(?:[\d\s]*\n)*?'                   # optional reference lines (digits/spaces)
            r'(.+?)(\d{2}\.\d{2}\.\d{4})',       # description + date
        )
        for m in pattern.finditer(text):
            balance = float(m.group(1).replace(',', ''))
            credit = float(m.group(2).replace(',', ''))
            debit = float(m.group(3).replace(',', ''))
            description = m.group(4).strip()
            date_str = self._parse_date_str(m.group(5))

            if credit > 0:
                amount = credit
                tx_type = 'CREDIT'
            else:
                amount = debit
                tx_type = 'DEBIT'

            transactions.append(self._normalize_transaction({
                'date': date_str,
                'description': description,
                'amount': amount if tx_type == 'CREDIT' else -amount,
                'balance': balance,
                'type': tx_type,
            }))
        return transactions

    def _parse_mizrahi_pdf_text(self, text: str) -> List[Dict]:
        """Parse Mizrahi-Tefahot PDF format.
        Pattern: DD/MM/YY description signed_amount [ref]\\nbalance
        """
        import re
        transactions = []
        # Mizrahi: "30/10/25העברה לבנק אחר-1,358.00\n430015"
        # Or: "04/11/25החזרי מע\"מ171,605.00\n347,172.77\n15997"
        pattern = re.compile(
            r'(\d{2}/\d{2}/\d{2})'               # date DD/MM/YY
            r'\n?(\d{2}/\d{2}/\d{2}\n)?'          # optional value date
            r'(.+?)'                              # description
            r'(-?[\d,]+\.?\d{2})\n'               # amount
            r'(?:(\d+)\n)?'                        # optional reference
        )
        # More robust: scan line by line
        lines = text.split('\n')
        i = 0
        prev_balance = None
        while i < len(lines):
            line = lines[i].strip()
            # Match date at start: DD/MM/YY
            dm = re.match(r'^(\d{2}/\d{2}/\d{2})(.+?)(-?[\d,]+\.\d{2})$', line)
            if dm:
                raw_date = dm.group(1)
                # Convert YY to YYYY
                parts = raw_date.split('/')
                if len(parts) == 3 and len(parts[2]) == 2:
                    raw_date = f"{parts[0]}/{parts[1]}/20{parts[2]}"
                date_str = self._parse_date_str(raw_date)
                description = dm.group(2).strip()
                amount = float(dm.group(3).replace(',', ''))
                tx_type = 'CREDIT' if amount >= 0 else 'DEBIT'

                # Look ahead for balance
                balance = 0.0
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    bal_m = re.match(r'^(-?[\d,]+\.\d{2})$', next_line)
                    if bal_m:
                        balance = float(bal_m.group(1).replace(',', ''))

                transactions.append(self._normalize_transaction({
                    'date': date_str,
                    'description': description,
                    'amount': amount,
                    'balance': balance,
                    'type': tx_type,
                }))
            i += 1
        return transactions

    def _parse_fibi_pdf_text(self, text: str) -> List[Dict]:
        """Parse FIBI (International) PDF format.
        Complex multi-line format with RTL column ordering.
        """
        import re
        transactions = []
        # FIBI: "03/10/2025בחשבונות קבועים ניהול דמי \nש'עו22.50\n205205\n257"
        # Pattern varies. Use: date, description, amount, reference
        pattern = re.compile(
            r'(\d{2}/\d{2}/\d{4})'              # date
            r'\n\d{2}/\d{2}/\d{4}\n'             # value date
            r'(.+?)'                             # description
            r'([\d,]+\.?\d{2})\n'                # amount
            r'(.+?)\n'                           # reference/extra
            r'(\d+)\n',                          # code
        )
        # Simpler approach: find all amounts near dates
        lines = text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            dm = re.match(r'^(\d{2}/\d{2}/\d{4})(.+)', line)
            if dm:
                date_str = self._parse_date_str(dm.group(1))
                rest = dm.group(2).strip()
                # Extract description and amount from rest or subsequent lines
                amt_m = re.search(r'([\d,]+\.\d{2})', rest)
                if amt_m:
                    description = rest[:amt_m.start()].strip()
                    amount = float(amt_m.group(1).replace(',', ''))
                    # Look for balance: a number with a negative sign on the line containing it
                    balance = 0.0
                    # Check a few lines ahead for a balance-like number
                    for j in range(1, min(5, len(lines) - i)):
                        nxt = lines[i + j].strip()
                        bal_m = re.match(r'^(-?[\d,]+\.\d{2})$', nxt)
                        if bal_m:
                            balance = float(bal_m.group(1).replace(',', ''))
                            break

                    # Determine type from context — FIBI has separate debit column
                    # Without column info, use 'DEBIT' as default for construction accounts
                    tx_type = 'DEBIT'
                    transactions.append(self._normalize_transaction({
                        'date': date_str,
                        'description': description,
                        'amount': -amount,
                        'balance': balance,
                        'type': tx_type,
                    }))
            i += 1

        # Fix types using balance progression
        self._fix_types_from_balance(transactions)
        return transactions

    def _fix_types_from_balance(self, transactions: List[Dict]) -> None:
        """Infer debit/credit from balance changes when column info is lost in text extraction."""
        for i in range(1, len(transactions)):
            prev_bal = transactions[i - 1].get('balance', 0)
            curr_bal = transactions[i].get('balance', 0)
            amount = transactions[i].get('amount', 0)

            if prev_bal == 0 or curr_bal == 0:
                continue

            diff = curr_bal - prev_bal
            # If balance went up, the transaction was a credit
            if diff > 0:
                transactions[i]['type'] = 'CREDIT'
                transactions[i]['amount'] = abs(amount)
            elif diff < 0:
                transactions[i]['type'] = 'DEBIT'
                transactions[i]['amount'] = abs(amount)

    def _parse_pdf_with_vision(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Fallback: parse scanned/image PDF using Claude Vision."""
        try:
            import fitz
            doc = fitz.open(stream=file_content, filetype="pdf")
            all_transactions = []
            bank_info = None

            for page_num in range(min(3, len(doc))):
                page = doc[page_num]
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                page_result = self._analyze_image_with_claude(
                    img_base64, 'image/png',
                    page_num=page_num + 1,
                    is_first_page=(page_num == 0)
                )

                if page_num == 0 and page_result.get('bank'):
                    bank_info = page_result
                if page_result.get('transactions'):
                    all_transactions.extend(page_result['transactions'])

            doc.close()
            result = bank_info or {}
            result['transactions'] = all_transactions
            return self._calculate_totals(result)

        except ImportError:
            raise ValueError(
                "Neither pdf2image nor PyMuPDF is installed. "
                "Please install one of them: pip install pdf2image or pip install pymupdf"
            )

    def _parse_image(self, file_content: bytes, file_type: str) -> Dict[str, Any]:
        """Parse an image bank statement using Claude vision"""
        img_base64 = base64.b64encode(file_content).decode('utf-8')
        result = self._analyze_image_with_claude(img_base64, file_type, page_num=1, is_first_page=True)
        return self._calculate_totals(result)

    def _parse_excel(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Parse an Excel bank statement - tries smart fallback first, then AI"""
        import pandas as pd
        import io
        import re

        # Try to read the file - handle both xlsx and html-disguised-as-xls
        df = None
        is_html = False
        raw_text_for_detection = filename

        try:
            df = pd.read_excel(io.BytesIO(file_content), header=None)
        except Exception:
            pass

        if df is None:
            # Try with xlrd engine for old xls format
            try:
                df = pd.read_excel(io.BytesIO(file_content), header=None, engine='xlrd')
            except Exception:
                pass

        if df is None:
            # Try reading as HTML (Leumi exports .xls as HTML)
            try:
                dfs = pd.read_html(io.BytesIO(file_content))
                if dfs:
                    df = dfs[0]
                    # Reset column names to positional
                    df.columns = range(len(df.columns))
                    is_html = True
            except Exception:
                pass

        if df is None:
            raise ValueError("לא ניתן לקרוא את קובץ האקסל - פורמט לא נתמך")

        # Collect all text from the dataframe for bank detection
        all_text_parts = [filename]
        for i in range(min(10, len(df))):
            for val in df.iloc[i].values:
                if pd.notna(val):
                    all_text_parts.append(str(val))
        raw_text_for_detection = ' '.join(all_text_parts)

        # Try smart fallback parsing first (no AI needed)
        try:
            result = self._smart_excel_parse(df, raw_text_for_detection, is_html)
            if result and result.get('transactions'):
                logger.info(f"Smart Excel parser extracted {len(result['transactions'])} transactions")
                return self._calculate_totals(result)
        except Exception as e:
            logger.warning(f"Smart Excel parser failed: {e}")

        # Fall back to AI parsing
        bank = self._identify_bank_from_text(raw_text_for_detection)
        try:
            result = self._analyze_excel_with_claude(df, bank)
            return self._calculate_totals(result)
        except Exception as e:
            logger.warning(f"AI Excel parser failed: {e}")
            return self._calculate_totals(self._fallback_excel_parse(df, bank))

    # ──────────────────────────────────────────────────────────────
    #  Smart Excel parser — works WITHOUT AI for Israeli banks
    # ──────────────────────────────────────────────────────────────

    def _smart_excel_parse(
        self, df, raw_text: str, is_html: bool
    ) -> Dict[str, Any]:
        """
        Deterministic Excel parser for Israeli bank statements.
        Detects bank format, finds header row, maps columns, extracts transactions.
        """
        import pandas as pd
        import re

        bank_code, bank_display = self._detect_bank_from_content(raw_text)
        account_number = self._extract_account_number(raw_text, bank_code)
        date_range = self._extract_date_range(raw_text)

        # Detect the format and parse accordingly
        if bank_code == 'LEUMI' and is_html:
            transactions, opening_bal, closing_bal = self._parse_leumi_html(df)
        else:
            header_row, col_map = self._find_header_and_columns(df, bank_code)
            if header_row is None:
                raise ValueError("Could not find header row in Excel file")
            transactions, opening_bal, closing_bal = self._extract_transactions_from_mapped(
                df, header_row, col_map, bank_code
            )

        # Determine date range from transactions if not found in metadata
        start_date = date_range[0] if date_range else None
        end_date = date_range[1] if date_range else None
        if transactions and not start_date:
            dates = [t['date'] for t in transactions if t.get('date')]
            if dates:
                start_date = min(dates)
                end_date = max(dates)

        return {
            'bank': bank_code,
            'bank_display': bank_display,
            'account_number': account_number,
            'statement_start_date': start_date,
            'statement_end_date': end_date,
            'opening_balance': opening_bal,
            'closing_balance': closing_bal,
            'transactions': transactions,
            'confidence': 0.85,
            'warnings': ['Parsed using smart Excel fallback (no AI)'],
        }

    def _detect_bank_from_content(self, text: str) -> Tuple[str, str]:
        """Detect Israeli bank from text content. Returns (code, display_name)."""
        text_lower = text.lower()

        # Order matters — check specific patterns first
        bank_patterns = [
            (['בנק לאומי', 'לאומי', 'תאריך הנפקה | בנק'], 'LEUMI', 'בנק לאומי'),
            (['הפועלים', 'פועלים', 'poalim'], 'HAPOALIM', 'בנק הפועלים'),
            (['דיסקונט', 'discount', 'בנקאות מסחרית'], 'DISCOUNT', 'בנק דיסקונט'),
            (['ירושלים'], 'JERUSALEM', 'בנק ירושלים'),
            (['מזרחי', 'טפחות', 'mizrahi', 'יתרה ותנועות בחשבון'], 'MIZRAHI', 'בנק מזרחי טפחות'),
            (['הבינלאומי', 'fibi', 'fibi.co.il'], 'INTERNATIONAL', 'הבנק הבינלאומי'),
            (['אוצר החייל', 'otsar'], 'OTSAR', 'בנק אוצר החייל'),
            (['מרכנתיל', 'mercantile', 'סניף720'], 'MERCANTILE', 'בנק מרכנתיל'),
            (['יהב', 'yahav'], 'YAHAV', 'בנק יהב'),
        ]

        for keywords, code, display in bank_patterns:
            for kw in keywords:
                if kw in text_lower or kw in text:
                    return code, display

        return 'OTHER', 'בנק לא מזוהה'

    def _extract_account_number(self, text: str, bank_code: str) -> Optional[str]:
        """Extract account number from text metadata."""
        import re

        # "מספר חשבון  12-63-8386"  (Hapoalim)
        m = re.search(r'מספר חשבון\s+([\d\-]+)', text)
        if m:
            return m.group(1).strip()

        # "חשבון: 0198175673"  (Discount)
        m = re.search(r'חשבון[:\s]+(\d[\d\-]+)', text)
        if m:
            return m.group(1).strip()

        # "חשבון 051-510474034"  (Jerusalem)
        m = re.search(r'חשבון\s+([\d\-]+)', text)
        if m:
            return m.group(1).strip()

        # Leumi HTML: branch/account in data rows like "767", "226200/46"
        # Try a different pattern for Leumi
        m = re.search(r'(\d{3,})/(\d+)', text)
        if m and bank_code == 'LEUMI':
            return m.group(0)

        return None

    def _extract_date_range(self, text: str) -> Optional[Tuple[str, str]]:
        """Extract statement date range from metadata text."""
        import re

        # "לתקופה:  01.03.2025 - 01.09.2025"
        m = re.search(r'לתקופה[:\s]+([\d.]+)\s*-\s*([\d.]+)', text)
        if m:
            return (self._parse_date_str(m.group(1)), self._parse_date_str(m.group(2)))

        # "תאריך: 31.10.2025 - 01.10.2025" (Leumi — end first, start second)
        m = re.search(r'תאריך[:\s]+([\d.]+)\s*-\s*([\d.]+)', text)
        if m:
            d1 = self._parse_date_str(m.group(1))
            d2 = self._parse_date_str(m.group(2))
            if d1 and d2:
                return (min(d1, d2), max(d1, d2))

        # "מ: 29.07.2025 עד:10.11.2025"
        m = re.search(r'מ[:\s]+([\d.]+)\s*עד[:\s]+([\d.]+)', text)
        if m:
            return (self._parse_date_str(m.group(1)), self._parse_date_str(m.group(2)))

        return None

    def _parse_date_str(self, s: str) -> Optional[str]:
        """Parse a date string in various Israeli formats to YYYY-MM-DD."""
        if not s:
            return None
        s = str(s).strip()
        for fmt in ('%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        return None

    def _find_header_and_columns(
        self, df, bank_code: str
    ) -> Tuple[Optional[int], Dict[str, Optional[int]]]:
        """
        Scan the dataframe to find the header row and map column indices.
        Returns (header_row_index, column_map).

        Column map keys:
          date, description, debit, credit, amount, balance
        """
        import pandas as pd

        # Hebrew keywords for each column type
        date_keywords = ['תאריך']
        desc_keywords = ['תיאור', 'פרטים', 'הפעולה']
        debit_keywords = ['חובה']
        credit_keywords = ['זכות']
        amount_keywords = ['סכום', 'זכות/חובה']
        balance_keywords = ['יתרה']

        def _matches(cell_text, keywords):
            cell_lower = str(cell_text).strip()
            for kw in keywords:
                if kw in cell_lower:
                    return True
            return False

        # Scan first 15 rows for a row with date + (amount or debit/credit) + balance
        for row_idx in range(min(15, len(df))):
            row_vals = [str(v).strip() if pd.notna(v) else '' for v in df.iloc[row_idx].values]

            date_col = None
            desc_col = None
            debit_col = None
            credit_col = None
            amount_col = None
            balance_col = None

            for col_idx, val in enumerate(row_vals):
                if not val:
                    continue
                if _matches(val, date_keywords) and date_col is None:
                    date_col = col_idx
                elif _matches(val, balance_keywords):
                    balance_col = col_idx
                elif _matches(val, amount_keywords):
                    amount_col = col_idx
                elif _matches(val, debit_keywords) and not _matches(val, amount_keywords):
                    debit_col = col_idx
                elif _matches(val, credit_keywords) and not _matches(val, amount_keywords):
                    credit_col = col_idx
                elif _matches(val, desc_keywords) and desc_col is None:
                    desc_col = col_idx

            # If we have separate debit/credit columns, ignore the combined amount column
            if debit_col is not None and credit_col is not None:
                amount_col = None

            # Valid header: must have date and (balance or amount or debit)
            if date_col is not None and (balance_col is not None or amount_col is not None or debit_col is not None):
                col_map = {
                    'date': date_col,
                    'description': desc_col,
                    'debit': debit_col,
                    'credit': credit_col,
                    'amount': amount_col,
                    'balance': balance_col,
                }
                logger.info(f"Found header row at index {row_idx}, col_map={col_map}")
                return row_idx, col_map

        return None, {}

    def _extract_transactions_from_mapped(
        self, df, header_row: int, col_map: Dict, bank_code: str
    ) -> Tuple[List[Dict], Optional[float], Optional[float]]:
        """Extract transactions using discovered column mapping."""
        import pandas as pd

        transactions = []
        opening_balance = None
        closing_balance = None

        date_col = col_map.get('date')
        desc_col = col_map.get('description')
        debit_col = col_map.get('debit')
        credit_col = col_map.get('credit')
        amount_col = col_map.get('amount')
        balance_col = col_map.get('balance')

        for row_idx in range(header_row + 1, len(df)):
            row = df.iloc[row_idx]

            # Get date — skip rows without a valid date
            raw_date = row.iloc[date_col] if date_col is not None else None
            if pd.isna(raw_date) or str(raw_date).strip() == '':
                continue

            date_str = self._coerce_date(raw_date)
            if not date_str:
                # Might be a summary row — check for balance summary
                continue

            # Description
            description = ''
            if desc_col is not None and pd.notna(row.iloc[desc_col]):
                description = str(row.iloc[desc_col]).strip()

            # Amount / type — prefer separate debit/credit cols over combined amount
            amount = 0.0
            tx_type = 'DEBIT'

            if debit_col is not None or credit_col is not None:
                # Separate debit/credit columns (Hapoalim, Jerusalem)
                raw_debit = self._to_float(row.iloc[debit_col]) if debit_col is not None else None
                raw_credit = self._to_float(row.iloc[credit_col]) if credit_col is not None else None

                if raw_credit is not None and raw_credit > 0:
                    amount = abs(raw_credit)
                    tx_type = 'CREDIT'
                elif raw_debit is not None and raw_debit > 0:
                    amount = abs(raw_debit)
                    tx_type = 'DEBIT'
                elif raw_debit is not None and raw_debit != 0:
                    amount = abs(raw_debit)
                    tx_type = 'DEBIT'
                elif raw_credit is not None and raw_credit != 0:
                    amount = abs(raw_credit)
                    tx_type = 'CREDIT'
                else:
                    # Both are 0 or empty — skip
                    continue
            elif amount_col is not None:
                # Single combined column (Discount style: positive=credit, negative=debit)
                raw_amt = self._to_float(row.iloc[amount_col])
                if raw_amt is not None:
                    amount = abs(raw_amt)
                    tx_type = 'CREDIT' if raw_amt >= 0 else 'DEBIT'
                else:
                    continue

            # Balance
            balance = 0.0
            if balance_col is not None and pd.notna(row.iloc[balance_col]):
                bal = self._to_float(row.iloc[balance_col])
                if bal is not None:
                    balance = bal

            transactions.append(self._normalize_transaction({
                'date': date_str,
                'description': description,
                'amount': amount if tx_type == 'CREDIT' else -amount,
                'balance': balance,
                'type': tx_type,
            }))

            # Track opening/closing balance
            if balance != 0:
                if opening_balance is None:
                    opening_balance = balance
                closing_balance = balance

        return transactions, opening_balance, closing_balance

    def _parse_leumi_html(self, df) -> Tuple[List[Dict], Optional[float], Optional[float]]:
        """
        Parse Leumi HTML-format .xls files.
        Leumi has no explicit header row. Columns are:
          0: branch, 1: account, 2: date (DD/MM/YYYY), 3: description,
          4: debit, 5: credit, 6: balance, 7: (empty)
        Data rows start after the metadata rows.
        """
        import pandas as pd

        transactions = []
        opening_balance = None
        closing_balance = None

        for row_idx in range(len(df)):
            row = df.iloc[row_idx]

            # Leumi data rows: col 2 should be a date like "05/10/2025"
            raw_date = row.iloc[2] if len(row) > 2 else None
            if pd.isna(raw_date):
                continue
            date_str = self._coerce_date(raw_date)
            if not date_str:
                continue

            description = str(row.iloc[3]).strip() if len(row) > 3 and pd.notna(row.iloc[3]) else ''

            raw_debit = self._to_float(row.iloc[4]) if len(row) > 4 else None
            raw_credit = self._to_float(row.iloc[5]) if len(row) > 5 else None

            if raw_credit is not None and raw_credit > 0:
                amount = raw_credit
                tx_type = 'CREDIT'
            elif raw_debit is not None and raw_debit > 0:
                amount = raw_debit
                tx_type = 'DEBIT'
            else:
                continue

            balance = 0.0
            if len(row) > 6 and pd.notna(row.iloc[6]):
                bal = self._to_float(row.iloc[6])
                if bal is not None:
                    balance = bal

            transactions.append(self._normalize_transaction({
                'date': date_str,
                'description': description,
                'amount': amount if tx_type == 'CREDIT' else -amount,
                'balance': balance,
                'type': tx_type,
            }))

            if balance != 0:
                if opening_balance is None:
                    opening_balance = balance
                closing_balance = balance

        return transactions, opening_balance, closing_balance

    def _coerce_date(self, val) -> Optional[str]:
        """Coerce a cell value to YYYY-MM-DD string."""
        if val is None:
            return None
        if isinstance(val, datetime):
            return val.strftime('%Y-%m-%d')
        s = str(val).strip()
        if not s:
            return None
        return self._parse_date_str(s)

    def _to_float(self, val) -> Optional[float]:
        """Coerce a cell value to float, handling commas, ₪ symbols, and empty strings."""
        import pandas as pd
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        # Remove currency symbols, thousands separators, spaces
        s = s.replace('₪', '').replace(',', '').replace('\u200e', '').replace(' ', '').strip()
        if not s or s == '-' or s == '- ₪' or s == '-₪':
            return None
        try:
            return float(s)
        except ValueError:
            return None

    def _analyze_image_with_claude(
        self,
        img_base64: str,
        media_type: str,
        page_num: int = 1,
        is_first_page: bool = True
    ) -> Dict[str, Any]:
        """Use Claude vision to analyze a bank statement image"""

        prompt = self._build_vision_prompt(is_first_page, page_num)

        try:
            client = self._get_client()

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": img_base64,
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            response_text = message.content[0].text
            return self._parse_claude_response(response_text)

        except ValueError as e:
            # Missing API key or configuration error — surface as error
            logger.error(f"Configuration error for Claude API: {str(e)}")
            return {
                "transactions": [],
                "error": str(e),
                "warnings": [f"AI parsing error: {str(e)}"],
                "confidence": 0,
            }
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            return {
                "transactions": [],
                "error": f"AI parsing error: {str(e)}",
                "warnings": [f"AI parsing error: {str(e)}"],
                "confidence": 0,
            }

    def _analyze_excel_with_claude(self, df, detected_bank: Optional[str]) -> Dict[str, Any]:
        """Use Claude to intelligently parse Excel bank statement"""

        # Prepare data summary for Claude
        headers = list(df.columns)
        sample_rows = df.head(10).values.tolist()

        # Build prompt
        prompt = f"""אתה מומחה בניתוח דפי חשבון בנק. נתון לך קובץ אקסל של דף חשבון בנק ישראלי.

עמודות הקובץ: {headers}

נתונים לדוגמה (10 שורות ראשונות):
{json.dumps(sample_rows, ensure_ascii=False, default=str)}

בנק מזוהה: {detected_bank or 'לא זוהה'}

משימתך:
1. זהה את הבנק ומספר החשבון (אם קיימים בנתונים)
2. זהה את תקופת דף החשבון (תאריך התחלה וסיום)
3. חלץ את כל התנועות - תאריך, תיאור, סכום, יתרה, סוג (זכות/חובה)

החזר JSON בפורמט הבא:
{{
    "bank": "LEUMI/HAPOALIM/DISCOUNT/MIZRAHI/OTHER",
    "bank_display": "שם הבנק בעברית",
    "account_number": "מספר חשבון או null",
    "statement_start_date": "YYYY-MM-DD",
    "statement_end_date": "YYYY-MM-DD",
    "opening_balance": 0.00,
    "closing_balance": 0.00,
    "transactions": [
        {{
            "date": "YYYY-MM-DD",
            "description": "תיאור התנועה",
            "amount": 1000.00,
            "balance": 5000.00,
            "type": "CREDIT או DEBIT"
        }}
    ],
    "confidence": 0.95,
    "warnings": []
}}

חשוב:
- סכום חיובי = זכות (CREDIT), סכום שלילי = חובה (DEBIT)
- אם יש עמודות נפרדות לזכות וחובה, השתמש בהן
- וודא שכל התאריכים בפורמט YYYY-MM-DD
- אם חסר מידע, השתמש ב-null"""

        try:
            client = self._get_client()

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = message.content[0].text
            return self._parse_claude_response(response_text)

        except ValueError as e:
            # Missing API key or configuration error
            logger.error(f"Configuration error for Claude API: {str(e)}")
            return {
                "transactions": [],
                "error": str(e),
                "warnings": [f"AI parsing error: {str(e)}"],
                "confidence": 0,
            }
        except Exception as e:
            logger.error(f"Error calling Claude API for Excel: {str(e)}")
            return self._fallback_excel_parse(df, detected_bank)

    def _build_vision_prompt(self, is_first_page: bool, page_num: int) -> str:
        """Build the prompt for Claude vision analysis"""

        if is_first_page:
            return """אתה מומחה בניתוח דפי חשבון בנק. נתונה לך תמונה של דף חשבון בנק ישראלי.

משימתך:
1. זהה את הבנק (לאומי, הפועלים, דיסקונט, מזרחי-טפחות, וכו')
2. זהה את מספר החשבון
3. זהה את תקופת דף החשבון (מתאריך - עד תאריך)
4. חלץ את כל התנועות מהטבלה:
   - תאריך התנועה
   - תיאור/פרטים
   - סכום (זכות או חובה)
   - יתרה

החזר את התשובה כ-JSON בלבד בפורמט הבא:
{
    "bank": "LEUMI/HAPOALIM/DISCOUNT/MIZRAHI/INTERNATIONAL/OTHER",
    "bank_display": "שם הבנק בעברית",
    "account_number": "מספר החשבון או null",
    "statement_start_date": "YYYY-MM-DD או null",
    "statement_end_date": "YYYY-MM-DD או null",
    "opening_balance": 0.00,
    "closing_balance": 0.00,
    "transactions": [
        {
            "date": "YYYY-MM-DD",
            "description": "תיאור התנועה",
            "amount": 1000.00,
            "balance": 5000.00,
            "type": "CREDIT או DEBIT"
        }
    ],
    "confidence": 0.95,
    "warnings": ["אזהרות אם יש"]
}

חשוב:
- זכות (הפקדה/הכנסה) = CREDIT, חובה (משיכה/הוצאה) = DEBIT
- סכומים תמיד חיוביים, הסוג (type) מציין אם זכות או חובה
- תאריכים בפורמט YYYY-MM-DD
- אם לא ניתן לזהות ערך, השתמש ב-null
- confidence בין 0 ל-1 לפי רמת הביטחון בפענוח"""
        else:
            return f"""זוהי עמוד {page_num} של דף חשבון בנק. חלץ את כל התנועות מהטבלה.

החזר JSON עם התנועות בלבד:
{{
    "transactions": [
        {{
            "date": "YYYY-MM-DD",
            "description": "תיאור התנועה",
            "amount": 1000.00,
            "balance": 5000.00,
            "type": "CREDIT או DEBIT"
        }}
    ],
    "warnings": []
}}"""

    def _parse_claude_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's JSON response"""
        try:
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[json_start:json_end]
            result = json.loads(json_str)

            # Normalize transactions
            if 'transactions' in result:
                result['transactions'] = [
                    self._normalize_transaction(t)
                    for t in result['transactions']
                ]

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.error(f"Response was: {response_text[:500]}")
            return {
                "transactions": [],
                "warnings": ["Failed to parse AI response"],
                "confidence": 0
            }

    def _normalize_transaction(self, tx: Dict) -> Dict:
        """Normalize a transaction dict"""
        # Ensure amount is positive
        amount = abs(float(tx.get('amount', 0) or 0))

        # Normalize type
        tx_type = str(tx.get('type', '')).upper()
        if tx_type not in ['CREDIT', 'DEBIT']:
            # Try to infer from original amount sign or description
            original_amount = tx.get('amount', 0) or 0
            if isinstance(original_amount, (int, float)) and original_amount < 0:
                tx_type = 'DEBIT'
            else:
                tx_type = 'CREDIT'

        # Normalize date
        date_str = tx.get('date', '')
        if date_str:
            try:
                # Try various date formats
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y']:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        date_str = parsed_date.strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

        return {
            'date': date_str,
            'description': str(tx.get('description', '')).strip(),
            'amount': amount,
            'balance': float(tx.get('balance', 0) or 0),
            'type': tx_type
        }

    def _calculate_totals(self, result: Dict) -> Dict:
        """Calculate total credits and debits from transactions"""
        transactions = result.get('transactions', [])

        if not transactions:
            warnings = result.get('warnings', [])
            warnings.append("לא זוהו תנועות בדף החשבון - ייתכן שהקובץ ריק או בפורמט לא נתמך")
            result['warnings'] = warnings
            logger.warning("0 transactions detected from bank statement parsing")

        total_credits = sum(
            t['amount'] for t in transactions
            if t.get('type') == 'CREDIT'
        )
        total_debits = sum(
            t['amount'] for t in transactions
            if t.get('type') == 'DEBIT'
        )

        result['total_credits'] = round(total_credits, 2)
        result['total_debits'] = round(total_debits, 2)
        result['transaction_count'] = len(transactions)

        return result

    def _identify_bank_from_text(self, text: str) -> Optional[str]:
        """Try to identify bank from text content"""
        text_lower = text.lower()

        for keyword, bank_code in ISRAELI_BANKS.items():
            if keyword in text_lower:
                return bank_code

        return None

    def _fallback_excel_parse(self, df, detected_bank: Optional[str]) -> Dict[str, Any]:
        """Fallback Excel parsing without AI"""
        import pandas as pd

        transactions = []
        warnings = ["Using fallback parsing - AI unavailable"]

        # Try to find date, description, amount columns
        date_cols = [c for c in df.columns if any(
            x in str(c).lower() for x in ['תאריך', 'date', 'ת.ערך', 'ת.עסקה']
        )]
        desc_cols = [c for c in df.columns if any(
            x in str(c).lower() for x in ['תיאור', 'פרטים', 'description', 'פעולה']
        )]
        amount_cols = [c for c in df.columns if any(
            x in str(c).lower() for x in ['סכום', 'amount', 'זכות', 'חובה']
        )]
        balance_cols = [c for c in df.columns if any(
            x in str(c).lower() for x in ['יתרה', 'balance']
        )]

        date_col = date_cols[0] if date_cols else None
        desc_col = desc_cols[0] if desc_cols else None
        amount_col = amount_cols[0] if amount_cols else None
        balance_col = balance_cols[0] if balance_cols else None

        if date_col and amount_col:
            for _, row in df.iterrows():
                try:
                    date_val = row[date_col]
                    if pd.isna(date_val):
                        continue

                    # Parse date
                    if isinstance(date_val, datetime):
                        date_str = date_val.strftime('%Y-%m-%d')
                    else:
                        date_str = str(date_val)

                    # Get amount and determine type
                    amount = float(row[amount_col]) if not pd.isna(row[amount_col]) else 0
                    tx_type = 'CREDIT' if amount >= 0 else 'DEBIT'

                    transactions.append({
                        'date': date_str,
                        'description': str(row[desc_col]) if desc_col and not pd.isna(row[desc_col]) else '',
                        'amount': abs(amount),
                        'balance': float(row[balance_col]) if balance_col and not pd.isna(row[balance_col]) else 0,
                        'type': tx_type
                    })
                except Exception as e:
                    logger.warning(f"Error parsing row: {e}")
                    continue
        else:
            warnings.append("Could not identify required columns (date, amount)")

        return {
            'bank': detected_bank,
            'transactions': transactions,
            'confidence': 0.5,
            'warnings': warnings
        }


# Singleton instance
bank_statement_ai_parser = BankStatementAIParser()
