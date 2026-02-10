"""Process and extract data from PDF receipts"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pdfplumber


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
        Scan folder for PDF receipts
        
        Returns:
            List of PDF file paths
        """
        self.receipts = list(self.receipts_folder.glob("*.pdf"))
        return self.receipts
    
    def extract_text(self, pdf_path: Path) -> str:
        """
        Extract text from PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text content
        """
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception as e:
            print(f"Error reading {pdf_path.name}: {e}")
        
        return text
    
    def extract_amount(self, text: str) -> Optional[float]:
        """
        Extract total amount from receipt text
        
        Args:
            text: Receipt text content
            
        Returns:
            Extracted amount or None
        """
        # Common patterns for total amount
        patterns = [
            r'total[:\s]+\$?([\d,]+\.?\d{0,2})',
            r'amount[:\s]+\$?([\d,]+\.?\d{0,2})',
            r'grand total[:\s]+\$?([\d,]+\.?\d{0,2})',
            r'\$\s*([\d,]+\.\d{2})\s*$',  # Last dollar amount
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                # Get the last match (usually the total)
                amount_str = matches[-1].replace(',', '')
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        
        return None
    
    def extract_date(self, text: str) -> Optional[datetime]:
        """
        Extract date from receipt text
        
        Args:
            text: Receipt text content
            
        Returns:
            Extracted date or None
        """
        # Common date patterns
        date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                date_str = matches[0]
                # Try to parse the date
                for fmt in ['%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d', '%m-%d-%Y', '%m/%d/%y']:
                    try:
                        return datetime.strptime(date_str, fmt)
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
        # Usually the merchant name is in the first few lines
        lines = text.split('\n')
        if lines:
            # Return first non-empty line as merchant name
            for line in lines[:5]:
                line = line.strip()
                if line and len(line) > 2:
                    return line
        
        return None
    
    def process_receipt(self, pdf_path: Path) -> Dict:
        """
        Process a single receipt and extract all information
        
        Args:
            pdf_path: Path to receipt PDF
            
        Returns:
            Dictionary with extracted information
        """
        text = self.extract_text(pdf_path)
        
        return {
            'filename': pdf_path.name,
            'path': str(pdf_path),
            'text': text,
            'amount': self.extract_amount(text),
            'date': self.extract_date(text),
            'merchant': self.extract_merchant(text),
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
