"""Process and extract data from PDF receipts"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pdfplumber
from PIL import Image
import pytesseract


class ReceiptProcessor:
    """Extract information from receipt PDFs"""
    
    def __init__(self, receipts_folder: str):
        """
        Initialize the receipt processor
        
        Args:
            receipts_folder: Path to folder containing receipt PDFs
        """
        self.receipts_folder = Path(receipts_folder)
        self.receipts = []
        
    def scan_receipts(self) -> List[Path]:
        """
        Scan folder for PDF and image receipts
        
        Returns:
            List of receipt file paths (PDF and images)
        """
        # Scan for PDFs
        pdf_receipts = list(self.receipts_folder.glob("*.pdf"))
        
        # Scan for images
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.tiff', '*.tif', '*.bmp', '*.gif']
        image_receipts = []
        for ext in image_extensions:
            image_receipts.extend(list(self.receipts_folder.glob(ext)))
            # Also check uppercase
            image_receipts.extend(list(self.receipts_folder.glob(ext.upper())))
        
        self.receipts = pdf_receipts + image_receipts
        return self.receipts
    
    def extract_text_from_image(self, image_path: Path) -> str:
        """
        Extract text from image using OCR (Tesseract)
        
        Args:
            image_path: Path to image file
            
        Returns:
            Extracted text content
        """
        text = ""
        try:
            # Open image with Pillow
            image = Image.open(image_path)
            
            # Use Tesseract OCR to extract text
            # Configure for better German support
            custom_config = r'--oem 3 --psm 6 -l deu+eng'
            text = pytesseract.image_to_string(image, config=custom_config)
            
            print(f"OCR extracted {len(text)} characters from {image_path.name}")
            
        except Exception as e:
            print(f"Error reading image {image_path.name}: {e}")
        
        return text
    
    def extract_text(self, file_path: Path) -> str:
        """
        Extract text from PDF or image file
        
        Args:
            file_path: Path to PDF or image file
            
        Returns:
            Extracted text content
        """
        # Check file extension
        suffix = file_path.suffix.lower()
        
        # Image files - use OCR
        if suffix in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif']:
            return self.extract_text_from_image(file_path)
        
        # PDF files - try pdfplumber first, fall back to OCR if needed
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text
                
                # If no text extracted, it's likely a scanned PDF - use OCR
                if len(text.strip()) < 50:  # Very little text suggests scanned PDF
                    print(f"No text in {file_path.name} - using OCR on PDF images...")
                    text = self.extract_text_from_pdf_with_ocr(file_path)
                    
        except Exception as e:
            print(f"Error reading {file_path.name}: {e}")
        
        return text
    
    def extract_text_from_pdf_with_ocr(self, pdf_path: Path) -> str:
        """
        Extract text from scanned PDF using OCR
        Converts PDF pages to images and runs Tesseract
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text content
        """
        text = ""
        try:
            import pdf2image
            
            # Find poppler path (for macOS brew installation)
            poppler_path = None
            
            # Check if pdftoppm is in system PATH first
            import shutil
            if shutil.which('pdftoppm'):
                # Found in PATH, no need to specify
                poppler_path = None
            else:
                # Try common brew locations
                possible_paths = [
                    '/opt/homebrew/Cellar/poppler/25.10.0/bin',  # Current brew version
                    '/opt/homebrew/bin',  # Apple Silicon
                    '/usr/local/bin',     # Intel Mac
                    '/opt/local/bin',     # MacPorts
                ]
                
                for path in possible_paths:
                    if Path(path).exists() and Path(path + '/pdftoppm').exists():
                        poppler_path = path
                        print(f"Found poppler at: {poppler_path}")
                        break
            
            # Convert PDF pages to images
            print(f"Converting PDF pages to images for OCR...")
            if poppler_path:
                images = pdf2image.convert_from_path(str(pdf_path), poppler_path=poppler_path)
            else:
                images = pdf2image.convert_from_path(str(pdf_path))
            
            # Run OCR on each page
            for i, image in enumerate(images):
                print(f"  OCR on page {i+1}/{len(images)}...")
                custom_config = r'--oem 3 --psm 6 -l deu+eng'
                page_text = pytesseract.image_to_string(image, config=custom_config)
                text += page_text + "\n"
            
            print(f"OCR extracted {len(text)} characters from {len(images)} page(s)")
            
        except ImportError:
            print(f"⚠️ pdf2image not installed - cannot OCR scanned PDFs")
            print(f"   Install with: pip install pdf2image")
            print(f"   Also install poppler: brew install poppler")
        except Exception as e:
            print(f"Error during PDF OCR: {e}")
        
        return text
    
    def detect_number_format(self, text: str) -> str:
        """
        Detect if receipt uses German (comma decimal) or English (period decimal) format
        
        Args:
            text: Receipt text content
            
        Returns:
            'german' or 'english'
        """
        # Look for patterns that clearly indicate format
        # German: 1.234,56 or just 44,84
        # English: 1,234.56 or just 44.56
        
        # Find all number-like patterns
        numbers = re.findall(r'\d{1,3}[.,]\d{2,3}(?:[.,]\d{2})?', text)
        
        german_indicators = 0
        english_indicators = 0
        
        for num in numbers:
            # Pattern: X.XXX,XX (German thousands + decimal)
            if re.match(r'\d+\.\d{3},\d{2}', num):
                german_indicators += 2
            # Pattern: X,XXX.XX (English thousands + decimal)
            elif re.match(r'\d+,\d{3}\.\d{2}', num):
                english_indicators += 2
            # Pattern: XX,XX (likely German decimal)
            elif re.match(r'^\d{1,3},\d{2}$', num):
                german_indicators += 1
            # Pattern: XX.XX (likely English decimal)
            elif re.match(r'^\d{1,3}\.\d{2}$', num):
                english_indicators += 1
        
        # Also check for EUR symbol which suggests German format
        if '€' in text or 'EUR' in text.upper():
            german_indicators += 1
        
        return 'german' if german_indicators > english_indicators else 'english'
    
    def normalize_amount(self, amount_str: str, number_format: str) -> str:
        """
        Normalize amount string to standard float format
        
        Args:
            amount_str: Raw amount string
            number_format: 'german' or 'english'
            
        Returns:
            Normalized amount string (e.g., "1234.56")
        """
        if number_format == 'german':
            # German format: 1.234,56 → 1234.56
            # Remove thousands separator (period)
            amount_str = amount_str.replace('.', '')
            # Replace decimal separator (comma) with period
            amount_str = amount_str.replace(',', '.')
        else:
            # English format: 1,234.56 → 1234.56
            # Remove thousands separator (comma)
            amount_str = amount_str.replace(',', '')
            # Decimal separator (period) is already correct
        
        return amount_str
    
    def extract_amount(self, text: str) -> Optional[float]:
        """
        Extract total amount from receipt text
        Handles both German (comma decimal) and English (period decimal) formats
        
        Args:
            text: Receipt text content
            
        Returns:
            Extracted amount or None
        """
        # Detect number format used in this receipt
        number_format = self.detect_number_format(text)
        
        # Comprehensive patterns for total amount
        # Capture both German (X,XX) and English (X.XX) formats
        patterns = [
            # High priority: Amount paid/due with keywords (very specific)
            r'amount\s+paid[:\s]+[€\$£]?\s*([\d.,]+)',
            r'amount\s+due[:\s]+[€\$£]?\s*([\d.,]+)',
            r'grand\s+total[:\s]+[€\$£]?\s*([\d.,]+)',
            r'total\s+amount[:\s]+[€\$£]?\s*([\d.,]+)',
            
            # German specific patterns - CHECK BEFORE GENERIC 'TOTAL'
            r'gesamtbetrag[:\s]*[€]?\s*([\d.,]+)',  # Total amount (Gesamtbetrag) - highest priority for invoices
            r'endsumme[:\s]*[€]?\s*([\d.,]+)',  # Final sum (Endsumme) - very specific
            r'summe[:\s]*[€]?\s*([\d.,]+)\s*€',  # Sum total (most specific - check first!)
            r'zu\s+zahlender\s+betrag[:\s]*[€]?\s*([\d.,]+)',  # Amount to pay
            r'rechnungsbetrag[:\s]*(?:eur|€)?\s*([\d.,]+)',  # Invoice amount (allows EUR/€)
            r'betrag.*?in.*?höhe.*?von[:\s]*[€]?\s*([\d.,]+)\s*€',  # "Betrag in Höhe von 18.809,00 €"
            r'abschlagsbetrag.*?brutto[:\s]*[€]?\s*([\d.,]+)',  # Utility bill: "Abschlagsbetrag brutto 135,01 €"
            r'endbetrag[:\s]*[€]?\s*([\d.,]+)',  # Final amount
            r'gesamt[^0-9€]*?[€]?\s*([\d.,]+)\s*€',  # Gesamt (with tip) - check before 'Total'
            r'total[:\s]+[€\$£]?\s*([\d.,]+)',  # Total (subtotal, no tip) - check AFTER Gesamt
            r'betrag[:\s]*\((?:euro|eur)',  # Eigenbeleg: "Betrag (Euro, Cent):"
            
            # English specific patterns
            r'total\s+in\s+(?:eur|usd|gbp)[:\s]+[€\$£]?\s*([\d.,]+)',
            r'balance\s+due[:\s]+[€\$£]?\s*([\d.,]+)',
            
            # Currency directly attached to number (e.g., "50€" or "$50")
            r'(\d+(?:[.,]\d+)?)[€\$£]',  # Number followed by currency
            
            # Currency symbol patterns (lower priority)
            r'[€\$£]\s*([\d.,]+)\s+(?:paid|due|total)',
            r'[€\$£]\s*([\d.,]+)',  # Last resort: any currency amount
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Process matches and filter
                valid_amounts = []
                for match in matches:
                    # Clean up the match
                    amount_str = match.strip()
                    
                    # Skip if it doesn't look like a valid amount
                    if not re.match(r'[\d.,]+$', amount_str):
                        continue
                    
                    # Normalize based on detected format
                    try:
                        normalized = self.normalize_amount(amount_str, number_format)
                        amount = float(normalized)
                        
                        # Sanity check: reasonable amount range (€0.01 to €999,999)
                        if 0.01 <= amount <= 999999:
                            valid_amounts.append(amount)
                    except:
                        continue
                
                # Filter out zero amounts if non-zero exist
                non_zero = [a for a in valid_amounts if a > 0]
                if non_zero:
                    valid_amounts = non_zero
                
                # Return last valid amount (usually the total)
                if valid_amounts:
                    return valid_amounts[-1]
        
        return None
    
    def extract_date(self, text: str) -> Optional[datetime]:
        """
        Extract date from receipt text
        
        Args:
            text: Receipt text content
            
        Returns:
            Extracted date or None
        """
        from dateutil import parser as date_parser
        
        # Look for specific date indicators first (more reliable)
        priority_patterns = [
            r'date\s+paid[:\s]+([a-z]+\s+\d{1,2},?\s+\d{4})',
            r'paid\s+on[:\s]+([a-z]+\s+\d{1,2},?\s+\d{4})',
            r'invoice\s+date[:\s]+([a-z]+\s+\d{1,2},?\s+\d{4})',
            # Email receipts - look for sender date: "30 November 2025 at 14:07"
            r'(\d{1,2}\s+[a-z]+\s+\d{4})\s+at\s+\d{1,2}:\d{2}',
        ]
        
        for pattern in priority_patterns:
            matches = re.findall(pattern, text.lower(), re.IGNORECASE)
            if matches:
                date_str = matches[0]
                try:
                    parsed_date = date_parser.parse(date_str, fuzzy=False)
                    if parsed_date.year <= datetime.now().year + 1:
                        return parsed_date
                except:
                    pass
        
        # Common date patterns (fallback)
        date_patterns = [
            # German "den DD.MM.YYYY" format
            r'den\s+(\d{1,2}\.\d{1,2}\.\d{4})',
            # German full month name: 10. Dezember 2025
            r'\d{1,2}\.\s*(?:januar|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember)\s+\d{4}',
            # Full month name: December 13, 2025
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}',
            # Short month: Dec 13, 2025
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}',
            # Numeric: 12/13/2025 or 13.12.2025
            r'\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}',
            # ISO: 2025-12-13
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text.lower(), re.IGNORECASE)
            if matches:
                # Take first match and ensure it's not a future date range
                date_str = matches[0]
                try:
                    # Use dateutil parser for flexible date parsing
                    # IMPORTANT: Use dayfirst=True for German dates (DD.MM.YYYY)
                    parsed_date = date_parser.parse(date_str, fuzzy=False, dayfirst=True)
                    
                    # Fix year if it's in the far future (likely OCR error)
                    # Prefer recent past over next year
                    current_year = datetime.now().year
                    current_month = datetime.now().month
                    
                    # Fix OCR errors that read years incorrectly
                    # Strategy: Receipts should generally not be from the future
                    # If date is in future, try moving it back to make sense
                    
                    # Fix obvious OCR errors (2025 -> 2029, 2028, 2027)
                    if parsed_date.year >= 2029:
                        parsed_date = parsed_date.replace(year=2025)
                    elif parsed_date.year == 2028:
                        parsed_date = parsed_date.replace(year=2025)
                    elif parsed_date.year == 2027:
                        parsed_date = parsed_date.replace(year=2025)
                    
                    # If date is in the future, move it back
                    # Receipts are almost always from the past
                    if parsed_date > datetime.now():
                        # Try moving back 1 year
                        parsed_date = parsed_date.replace(year=parsed_date.year - 1)
                        
                        # If still in future, move back another year
                        if parsed_date > datetime.now():
                            parsed_date = parsed_date.replace(year=parsed_date.year - 1)
                    
                    # Final sanity check - don't return dates too far in future
                    if parsed_date.year <= current_year + 1:
                        return parsed_date
                except:
                    # Try manual parsing with German month names
                    german_months = {
                        'januar': 1, 'februar': 2, 'märz': 3, 'april': 4,
                        'mai': 5, 'juni': 6, 'juli': 7, 'august': 8,
                        'september': 9, 'oktober': 10, 'november': 11, 'dezember': 12
                    }
                    
                    # Try German date format: "10. Dezember 2025"
                    german_pattern = r'(\d{1,2})\.\s*(\w+)\s+(\d{4})'
                    german_match = re.match(german_pattern, date_str.lower())
                    if german_match:
                        day = int(german_match.group(1))
                        month_name = german_match.group(2).lower()
                        year = int(german_match.group(3))
                        
                        if month_name in german_months:
                            try:
                                parsed = datetime(year, german_months[month_name], day)
                                current_year = datetime.now().year
                                if parsed.year > current_year + 1:
                                    parsed = parsed.replace(year=current_year)
                                if parsed.year <= current_year + 1:
                                    return parsed
                            except ValueError:
                                pass
                    
                    # Try standard formats - IMPORTANT: Try DD.MM.YYYY before MM/DD/YYYY
                    for fmt in ['%d.%m.%Y', '%B %d, %Y', '%b %d, %Y', '%d/%m/%Y', '%m/%d/%Y',
                               '%Y-%m-%d', '%m-%d-%Y', '%m/%d/%y']:
                        try:
                            parsed = datetime.strptime(date_str, fmt)
                            
                            # Fix year if too far in future (including OCR errors)
                            current_year = datetime.now().year
                            current_month = datetime.now().month
                            
                            # Fix common OCR errors (2025 read as 2029, 2027, etc.)
                            if parsed.year >= 2029:
                                parsed = parsed.replace(year=2025)
                            elif parsed.year == 2028:
                                parsed = parsed.replace(year=2025)
                            elif parsed.year == 2027:
                                parsed = parsed.replace(year=2025)
                            elif parsed.year > current_year + 1:
                                parsed = parsed.replace(year=current_year)
                            # If in early 2026 and date is in future, move to 2025
                            elif parsed.year == current_year + 1 and current_month <= 6:
                                if parsed > datetime.now():
                                    parsed = parsed.replace(year=current_year - 1)
                            
                            if parsed.year <= current_year + 1:
                                return parsed
                        except ValueError:
                            continue
        
        return None
    
    def extract_merchant(self, text: str) -> Optional[str]:
        """
        Extract merchant name from receipt text
        
        Args:
            text: Receipt text content
            
        Returns:
            Merchant name or None
        """
        # Special handling for Eigenbeleg (self-made receipts)
        # Look for "Empfänger:" (recipient) field
        eigenbeleg_match = re.search(r'Empfänger[:\s]+(.+)', text, re.IGNORECASE)
        if eigenbeleg_match:
            recipient = eigenbeleg_match.group(1).strip()
            # Make sure it's not empty and not a continuation
            if recipient and len(recipient) > 2 and not recipient.startswith(('Verwendungs', 'Grund')):
                return recipient
        
        # Special handling for German receipts with "Ausgestellt von:" (issued by)
        issued_by_match = re.search(r'Ausgestellt von:\s*([^,]+)', text, re.IGNORECASE)
        if issued_by_match:
            merchant = issued_by_match.group(1).strip()
            # Clean up: remove trailing address parts (anything after first number)
            merchant = re.split(r'\s+\d', merchant)[0].strip()
            # Normalize multiple spaces
            merchant = re.sub(r'\s+', ' ', merchant)
            if merchant and len(merchant) > 2:
                return merchant
        
        lines = text.split('\n')
        if not lines:
            return None
        
        # Skip common header words that aren't merchant names
        skip_words = ['receipt', 'invoice', 'bill', 'statement', 'order', 'confirmation', 'eigenbeleg', 'rechnung', 'rechnungsbeleg', 'payment', 'document', 'artikel', 'item', 'items', 'zahlungsmethode', 'payment method']
        
        # SPECIAL CASE: Search entire document for "CompanyName GmbH" pattern (German invoices often have it at bottom)
        gmbh_pattern = r'([A-Z][A-Za-z\s&-]+(?:GmbH|AG|OHG|KG|UG|Ltd|Inc|LLC|Corp|ApS|AS))\s'
        gmbh_matches = re.findall(gmbh_pattern, text)
        if gmbh_matches:
            for match in gmbh_matches:
                # Clean up the match - remove currency codes, extra whitespace
                clean_match = re.sub(r'\b(EUR|USD|GBP|CHF)\b', '', match, flags=re.IGNORECASE)
                clean_match = ' '.join(clean_match.split()).strip()
                
                # Skip if it contains tax IDs, emails, or URLs
                if not re.search(r'(ATU|UID|VAT|@|http|www\.)', clean_match, re.IGNORECASE):
                    # Make sure it's a reasonable length (not too short, not too long)
                    if 3 < len(clean_match) < 50:
                        return clean_match
        
        # First pass: Look for lines with company identifiers (highest priority)
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            
            # Skip empty lines
            if not line or len(line) < 3:
                continue
            
            # Skip lines starting with tax IDs or containing them
            if re.search(r'(^|\s)(ATU|UID|VAT|USt-IdNr)[:\s]*\d', line, re.IGNORECASE):
                continue
            
            # Look for company identifiers (Inc, LLC, GmbH, Ltd, etc.)
            if re.search(r'\b(inc|llc|gmbh|ltd|limited|corp|corporation|co\.|aps|as|ag)\b', line, re.IGNORECASE):
                # Skip if line contains tax ID numbers
                if re.search(r'ATU\s*\d|UID\s*\d|VAT\s*\d', line, re.IGNORECASE):
                    continue
                    
                # If "Bill to" is on the line, extract what comes before it
                if 'bill to' in line.lower():
                    parts = re.split(r'\s*bill\s+to\s*', line, flags=re.IGNORECASE)
                    if parts[0].strip() and len(parts[0].strip()) > 2:
                        return parts[0].strip()
                else:
                    # Extract just the company name, remove URLs and emails
                    company = re.sub(r'\s+(bill to|invoice|receipt|http|www\.|@).*', '', line, flags=re.IGNORECASE)
                    # Clean up extra whitespace
                    company = ' '.join(company.split())
                    if len(company) > 2:
                        return company.strip()
        
        # Second pass: Look for other substantial lines
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            
            # Skip empty lines
            if not line or len(line) < 3:
                continue
            
            # Skip if line is just a header word
            if line.lower() in skip_words:
                continue
            
            # Skip lines with only numbers or invoice numbers
            if re.match(r'^[\d\s\-\.:]+$', line):
                continue
            
            # Skip lines that look like UUIDs or invoice numbers with dates
            if re.search(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', line, re.IGNORECASE):
                continue
            
            # Skip lines that look like header fields (e.g., "RECHNUNGSNUMMER DATUM", "NUMBER DATE")
            if re.match(r'^[A-Z\s]+$', line) and len(line.split()) <= 3:
                continue
            
            # Skip if line starts with common invoice/date/period prefixes
            if re.match(r'^(invoice|date|number|bill|paid|order|ref|period|type|profile|rechnungsnummer|datum)', line.lower()):
                continue
            
            # If line has "Bill to", extract what comes before
            if 'bill to' in line.lower():
                parts = re.split(r'\s*bill\s+to\s*', line, flags=re.IGNORECASE)
                if parts[0].strip() and len(parts[0].strip()) > 2:
                    return parts[0].strip()
                # Skip this line if extraction failed
                continue
            
            # Return first substantial line (likely merchant name)
            if len(line) > 5 and not line.startswith(('Invoice', 'Date', 'Number', 'Period', 'Type')):
                return line
        
        return None
    
    def detect_currency(self, text: str) -> str:
        """
        Detect currency from receipt text
        
        Args:
            text: Receipt text content
            
        Returns:
            Currency code: 'EUR', 'GBP', 'USD', or 'EUR' (default)
        """
        text_upper = text.upper()
        
        # Check for explicit currency codes and symbols (prioritize EUR for German receipts)
        # Count occurrences to determine primary currency
        eur_count = text_upper.count('EUR') + text.count('€')
        gbp_count = text_upper.count('GBP') + text.count('£')
        usd_count = text_upper.count('USD') + text.count('$')
        
        # If EUR appears, it's almost certainly EUR (especially for German receipts)
        if eur_count > 0 or '€' in text:
            return 'EUR'
        
        # Check for explicit GBP/USD only if EUR not found
        if gbp_count > usd_count and gbp_count > 0:
            return 'GBP'
        elif usd_count > 0:
            return 'USD'
        
        # Check for country indicators
        if 'UNITED KINGDOM' in text_upper or 'UK VAT' in text_upper or 'IRELAND' in text_upper:
            return 'GBP'
        elif 'USA' in text_upper or 'UNITED STATES' in text_upper:
            return 'USD'
        
        # Check for German indicators (Deutschland, MwSt, etc.)
        if 'DEUTSCHLAND' in text_upper or 'MWST' in text_upper or 'RECHNUNG' in text_upper:
            return 'EUR'
        
        # Default to EUR
        return 'EUR'
    
    def process_receipt(self, file_path: Path) -> Dict:
        """
        Process a single receipt (PDF or image) and extract all information
        
        Args:
            file_path: Path to receipt file (PDF or image)
            
        Returns:
            Dictionary with extracted information
        """
        text = self.extract_text(file_path)
        
        # Check if it's an image file
        is_image = file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif']
        
        return {
            'filename': file_path.name,
            'path': str(file_path),
            'text': text,
            'amount': self.extract_amount(text),
            'date': self.extract_date(text),
            'merchant': self.extract_merchant(text),
            'currency': self.detect_currency(text),
            'is_image': is_image,
        }
    
    def process_all_receipts(self) -> List[Dict]:
        """
        Process all receipts in the folder
        
        Returns:
            List of dictionaries with receipt information
        """
        if not self.receipts:
            self.scan_receipts()
        
        results = []
        for receipt_path in self.receipts:
            receipt_data = self.process_receipt(receipt_path)
            results.append(receipt_data)
        
        return results
