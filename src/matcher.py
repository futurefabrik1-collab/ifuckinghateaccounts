"""Match bank statement transactions with receipts"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
import pandas as pd


class ReceiptMatcher:
    """Match transactions with receipts based on date, amount, and merchant"""
    
    def __init__(self, 
                 date_tolerance_days: int = 3,
                 amount_tolerance_percent: float = 0.01,
                 merchant_threshold: int = 60):
        """
        Initialize the matcher
        
        Args:
            date_tolerance_days: Number of days difference allowed for date matching
            amount_tolerance_percent: Percentage difference allowed for amount matching (0.01 = 1%)
            merchant_threshold: Minimum fuzzy match score for merchant names (0-100)
        """
        self.date_tolerance = timedelta(days=date_tolerance_days)
        self.amount_tolerance = amount_tolerance_percent
        self.merchant_threshold = merchant_threshold
        
    def is_date_match(self, date1: datetime, date2: datetime) -> bool:
        """
        Check if two dates match within tolerance
        
        Args:
            date1: First date
            date2: Second date
            
        Returns:
            True if dates match within tolerance
        """
        if date1 is None or date2 is None:
            return False
        
        diff = abs((date1 - date2).days)
        return diff <= self.date_tolerance.days
    
    def is_amount_match(self, amount1: float, amount2: float) -> bool:
        """
        Check if two amounts match within tolerance
        
        Args:
            amount1: First amount
            amount2: Second amount
            
        Returns:
            True if amounts match within tolerance
        """
        if amount1 is None or amount2 is None:
            return False
        
        # Handle negative amounts (debits vs credits)
        amount1 = abs(amount1)
        amount2 = abs(amount2)
        
        if amount1 == 0 or amount2 == 0:
            return amount1 == amount2
        
        diff_percent = abs(amount1 - amount2) / max(amount1, amount2)
        return diff_percent <= self.amount_tolerance
    
    def calculate_merchant_similarity(self, merchant1: str, merchant2: str) -> int:
        """
        Calculate similarity score between merchant names
        
        Args:
            merchant1: First merchant name
            merchant2: Second merchant name
            
        Returns:
            Similarity score (0-100)
        """
        if not merchant1 or not merchant2:
            return 0
        
        # Clean strings
        m1 = merchant1.lower().strip()
        m2 = merchant2.lower().strip()
        
        # Use fuzzy matching
        return fuzz.partial_ratio(m1, m2)
    
    def match_transaction_to_receipt(self, 
                                     transaction: Dict, 
                                     receipt: Dict) -> Tuple[bool, int, Dict]:
        """
        Check if a transaction matches a receipt
        
        Args:
            transaction: Transaction dictionary with date, amount, description
            receipt: Receipt dictionary with date, amount, merchant
            
        Returns:
            Tuple of (is_match, confidence_score, match_details)
        """
        match_details = {
            'date_match': False,
            'amount_match': False,
            'merchant_match': False,
            'merchant_score': 0,
        }
        
        # Check date match
        if 'date' in transaction and receipt.get('date'):
            match_details['date_match'] = self.is_date_match(
                transaction['date'], 
                receipt['date']
            )
        
        # Check amount match
        if 'amount' in transaction and receipt.get('amount'):
            match_details['amount_match'] = self.is_amount_match(
                transaction['amount'],
                receipt['amount']
            )
        
        # Check merchant match
        if 'description' in transaction and receipt.get('merchant'):
            merchant_score = self.calculate_merchant_similarity(
                transaction['description'],
                receipt['merchant']
            )
            match_details['merchant_score'] = merchant_score
            match_details['merchant_match'] = merchant_score >= self.merchant_threshold
        
        # Calculate overall confidence
        # Require at least amount match, prefer date match too
        is_match = match_details['amount_match'] and match_details['date_match']
        
        # Calculate confidence score (0-100)
        confidence = 0
        if match_details['amount_match']:
            confidence += 40
        if match_details['date_match']:
            confidence += 30
        confidence += match_details['merchant_score'] * 0.3
        
        return is_match, int(confidence), match_details
    
    def find_best_match(self, 
                       transaction: Dict, 
                       receipts: List[Dict]) -> Optional[Tuple[Dict, int, Dict]]:
        """
        Find the best matching receipt for a transaction
        
        Args:
            transaction: Transaction to match
            receipts: List of receipts to search
            
        Returns:
            Tuple of (best_receipt, confidence, details) or None
        """
        best_match = None
        best_confidence = 0
        best_details = None
        
        for receipt in receipts:
            is_match, confidence, details = self.match_transaction_to_receipt(
                transaction, 
                receipt
            )
            
            if is_match and confidence > best_confidence:
                best_match = receipt
                best_confidence = confidence
                best_details = details
        
        return (best_match, best_confidence, best_details) if best_match else None
    
    def match_all_transactions(self, 
                              transactions: List[Dict], 
                              receipts: List[Dict]) -> List[Dict]:
        """
        Match all transactions with receipts
        
        Args:
            transactions: List of transactions
            receipts: List of receipts
            
        Returns:
            List of match results
        """
        results = []
        used_receipts = set()
        
        for i, transaction in enumerate(transactions):
            # Skip already used receipts
            available_receipts = [r for r in receipts if r['filename'] not in used_receipts]
            
            match_result = self.find_best_match(transaction, available_receipts)
            
            result = {
                'transaction_index': i,
                'transaction': transaction,
                'matched': match_result is not None,
            }
            
            if match_result:
                receipt, confidence, details = match_result
                result.update({
                    'receipt': receipt,
                    'confidence': confidence,
                    'match_details': details,
                })
                used_receipts.add(receipt['filename'])
            
            results.append(result)
        
        return results
    
    def generate_report(self, match_results: List[Dict]) -> Dict:
        """
        Generate summary report of matching results
        
        Args:
            match_results: List of match results
            
        Returns:
            Summary statistics
        """
        total = len(match_results)
        matched = sum(1 for r in match_results if r['matched'])
        unmatched = total - matched
        
        avg_confidence = 0
        if matched > 0:
            avg_confidence = sum(
                r['confidence'] for r in match_results if r['matched']
            ) / matched
        
        return {
            'total_transactions': total,
            'matched': matched,
            'unmatched': unmatched,
            'match_rate': (matched / total * 100) if total > 0 else 0,
            'average_confidence': avg_confidence,
        }
