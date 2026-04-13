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
        """Parse a PDF bank statement by converting to images and using vision"""
        try:
            # Try to import pdf2image
            from pdf2image import convert_from_bytes

            # Convert PDF to images
            images = convert_from_bytes(file_content, dpi=200)

            if not images:
                raise ValueError("Could not extract any pages from PDF")

            # For now, process first 3 pages max (to manage token usage)
            all_transactions = []
            bank_info = None

            for i, image in enumerate(images[:3]):
                # Convert PIL image to base64
                import io
                img_buffer = io.BytesIO()
                image.save(img_buffer, format='PNG')
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

                # Parse this page
                page_result = self._analyze_image_with_claude(
                    img_base64,
                    'image/png',
                    page_num=i+1,
                    is_first_page=(i == 0)
                )

                # Merge results
                if i == 0 and page_result.get('bank'):
                    bank_info = page_result

                if page_result.get('transactions'):
                    all_transactions.extend(page_result['transactions'])

            # Combine results
            result = bank_info or {}
            result['transactions'] = all_transactions
            result = self._calculate_totals(result)

            return result

        except ImportError:
            logger.warning("pdf2image not installed, trying alternative method")
            return self._parse_pdf_fallback(file_content, filename)

    def _parse_pdf_fallback(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Fallback PDF parsing using PyMuPDF or returning error"""
        try:
            import fitz  # PyMuPDF

            # Open PDF
            doc = fitz.open(stream=file_content, filetype="pdf")

            all_transactions = []
            bank_info = None

            for page_num in range(min(3, len(doc))):  # First 3 pages
                page = doc[page_num]

                # Render page to image
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                # Parse this page
                page_result = self._analyze_image_with_claude(
                    img_base64,
                    'image/png',
                    page_num=page_num+1,
                    is_first_page=(page_num == 0)
                )

                if page_num == 0 and page_result.get('bank'):
                    bank_info = page_result

                if page_result.get('transactions'):
                    all_transactions.extend(page_result['transactions'])

            doc.close()

            result = bank_info or {}
            result['transactions'] = all_transactions
            result = self._calculate_totals(result)

            return result

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
        """Parse an Excel bank statement"""
        import pandas as pd
        import io

        # Read Excel file
        df = pd.read_excel(io.BytesIO(file_content))

        # Try to identify bank from content or filename
        bank = self._identify_bank_from_text(filename + ' ' + ' '.join(df.columns.astype(str)))

        # Send to Claude for intelligent parsing
        result = self._analyze_excel_with_claude(df, bank)
        return self._calculate_totals(result)

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

        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            return {
                "transactions": [],
                "warnings": [f"AI parsing error: {str(e)}"],
                "confidence": 0
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
