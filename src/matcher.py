"""Match bank statement transactions with receipts"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
import pandas as pd


class ReceiptMatcher:
    """Match transactions with receipts based on date, amount, and merchant"""
    
    def __init__(self, 
                 date_tolerance_days: int = None,  # Not used anymore
                 amount_tolerance_percent: float = 0.001,  # 0.1% for EUR (essentially exact match)
                 amount_tolerance_non_eur: float = 0.20,  # 20% for non-EUR (exchange rate + fees)
                 merchant_threshold: int = 60):  # Minimum merchant score for confidence
        """
        Initialize the matcher
        
        Args:
            date_tolerance_days: Not used - dates are no longer required for matching
            amount_tolerance_percent: Percentage difference allowed for EUR amount matching (0.02 = 2%)
            amount_tolerance_non_eur: Percentage difference for non-EUR amounts (0.10 = 10%)
            merchant_threshold: Minimum fuzzy match score for merchant names (0-100)
        """
        self.amount_tolerance_eur = amount_tolerance_percent
        self.amount_tolerance_non_eur = amount_tolerance_non_eur
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
    
    def is_amount_match(self, amount1: float, amount2: float, is_eur: bool = True) -> Tuple[bool, float]:
        """
        Check if two amounts match within tolerance
        
        Args:
            amount1: First amount (transaction)
            amount2: Second amount (receipt)
            is_eur: True if amounts are in EUR (exact match), False for non-EUR (10% tolerance)
            
        Returns:
            Tuple of (is_match, diff_percent)
        """
        if amount1 is None or amount2 is None:
            return False, 1.0
        
        # Handle negative amounts (debits vs credits)
        amount1 = abs(amount1)
        amount2 = abs(amount2)
        
        if amount1 == 0 or amount2 == 0:
            return amount1 == amount2, 0.0 if amount1 == amount2 else 1.0
        
        diff_percent = abs(amount1 - amount2) / max(amount1, amount2)
        
        # Use appropriate tolerance based on currency
        tolerance = self.amount_tolerance_eur if is_eur else self.amount_tolerance_non_eur
        
        return diff_percent <= tolerance, diff_percent
    
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
    
    def convert_currency_to_eur(self, amount: float, currency: str, year: int = 2025) -> float:
        """
        Convert amount to EUR using approximate yearly average rates
        
        Args:
            amount: Amount in original currency
            currency: Currency code (GBP, USD, EUR)
            year: Year for rate (default 2025)
            
        Returns:
            Amount in EUR
        """
        # Approximate average conversion rates for 2025
        rates = {
            'EUR': 1.0,
            'GBP': 1.19,  # £1 = €1.19 (approximate 2025 average)
            'USD': 0.92,  # $1 = €0.92 (approximate 2025 average)
        }
        
        rate = rates.get(currency, 1.0)
        return amount * rate
    
    def match_transaction_to_receipt(self, 
                                     transaction: Dict, 
                                     receipt: Dict) -> Tuple[bool, int, Dict]:
        """
        Check if a transaction matches a receipt
        
        Args:
            transaction: Transaction dictionary with date, amount, description
            receipt: Receipt dictionary with date, amount, merchant, currency
            
        Returns:
            Tuple of (is_match, confidence_score, match_details)
        """
        match_details = {
            'amount_match': False,
            'amount_diff_percent': 1.0,
            'merchant_match': False,
            'merchant_score': 0,
            'is_eur': True,
            'date_score': 0,
            'days_diff': 999,
        }
        
        # SAFEGUARD: Never match bank fees, VAT, or internal transfers
        trans_desc = str(transaction.get('description', '')).upper()
        
        # Check for bank fees and internal transactions that should NEVER match
        exclude_keywords = [
            'MEHRWERTSTEUER', 'UMSATZSTEUER', 'ABSCHLUSS', 'KONTOFÜHRUNG',
            'BANK FEE', 'SERVICE FEE', 'MONTHLY FEE', 'GEBÜHR'
        ]
        
        for keyword in exclude_keywords:
            if keyword in trans_desc:
                # Immediately reject - these should never match receipts
                return False, 0, {'rejected_reason': f'Bank fee/tax detected: {keyword}'}
        
        # Detect if this is likely a currency conversion case
        # Check transaction description for USD, GBP indicators
        is_likely_currency_conversion = 'USD' in trans_desc or 'GBP' in trans_desc or 'FOREIGN' in trans_desc
        
        # Use higher tolerance for currency conversions
        is_eur = not is_likely_currency_conversion
        match_details['is_eur'] = is_eur
        
        # Check amount match - PRIMARY CRITERION
        # Convert receipt amount to EUR if needed
        receipt_amount = receipt.get('amount')
        receipt_currency = receipt.get('currency', 'EUR')
        
        if 'amount' in transaction and receipt_amount:
            # Convert receipt amount to EUR if it's in different currency
            if receipt_currency != 'EUR':
                receipt_amount_eur = self.convert_currency_to_eur(receipt_amount, receipt_currency)
                match_details['receipt_currency'] = receipt_currency
                match_details['receipt_amount_original'] = receipt_amount
                match_details['receipt_amount_converted'] = receipt_amount_eur
                match_details['conversion_rate'] = receipt_amount_eur / receipt_amount if receipt_amount > 0 else 1.0
                
                # For currency conversions, use non-EUR tolerance with 15% margin
                is_eur = False
            else:
                receipt_amount_eur = receipt_amount
                match_details['receipt_currency'] = 'EUR'
            
            amount_match, diff_percent = self.is_amount_match(
                transaction['amount'],
                receipt_amount_eur,
                is_eur=is_eur
            )
            match_details['amount_match'] = amount_match
            match_details['amount_diff_percent'] = diff_percent
        
        # Check merchant/description match - SECONDARY CRITERION
        merchant_score = 0
        if 'description' in transaction and receipt.get('merchant'):
            merchant_score = self.calculate_merchant_similarity(
                transaction['description'],
                receipt['merchant']
            )
            match_details['merchant_score'] = merchant_score
            match_details['merchant_match'] = merchant_score >= self.merchant_threshold
        
        # Check date proximity - TERTIARY CRITERION (guidance, not requirement)
        date_score = 0
        days_diff = 999
        if transaction.get('date') and receipt.get('date'):
            days_diff = abs((transaction['date'] - receipt['date']).days)
            match_details['days_diff'] = days_diff
            # Score: 100 for same day, decreasing to 0 at 30+ days
            if days_diff == 0:
                date_score = 100
            elif days_diff <= 7:
                date_score = 90
            elif days_diff <= 14:
                date_score = 70
            elif days_diff <= 21:
                date_score = 50
            elif days_diff <= 30:
                date_score = 30
            else:
                date_score = max(0, 30 - days_diff)  # Decreases further
            match_details['date_score'] = date_score
        
        # MATCHING LOGIC:
        # 1. Amount must match (primary) - OR merchant is very high when amount missing
        # 2. Merchant/description provides confidence (secondary)
        # 3. Date proximity provides additional guidance (tertiary, bonus)
        
        # Allow matching without amount if merchant score is high
        if match_details['amount_match']:
            is_match = True
        elif merchant_score >= 60 and date_score >= 40:
            # High merchant match + reasonable date = accept even without amount
            is_match = True
            match_details['matched_without_amount'] = True
        elif merchant_score >= 70 and date_score >= 20:
            # Very high merchant match + any date = accept
            is_match = True
            match_details['matched_without_amount'] = True
        else:
            is_match = False
        
        # Apply merchant + date validation to avoid false positives
        # IMPROVED: Better validation to prevent wrong merchant matches
        if is_match:
            # SAFEGUARD: Check for merchant mismatch
            # If transaction clearly mentions a merchant, the receipt should match it
            trans_desc_lower = str(transaction.get('description', '')).lower()
            receipt_merchant_lower = str(receipt.get('merchant', '')).lower()
            
            # Known merchants that should match exactly (with variations)
            specific_merchants = {
                'beatport': ['beatport'],
                'amazon': ['amazon', 'amzn'],
                'google': ['google'],
                'spotify': ['spotify', 'spoti'],  # Spotify sometimes abbreviated as "Spoti"
                'netflix': ['netflix'],
                'apple': ['apple'],
                'paypal': ['paypal']
            }
            
            for merchant_name, variations in specific_merchants.items():
                # Check if transaction mentions this merchant
                trans_has_merchant = any(var in trans_desc_lower for var in variations)
                # Check if receipt has any variation of the merchant
                receipt_has_merchant = any(var in receipt_merchant_lower for var in variations)
                
                # If transaction mentions this merchant but receipt doesn't have ANY variation, reject
                if trans_has_merchant and not receipt_has_merchant:
                    if merchant_score < 70:  # Unless merchant score is very high (fuzzy match found it)
                        is_match = False
                        match_details['rejected_reason'] = f'Merchant mismatch: transaction has {merchant_name}, receipt does not'
                        break
            
            # Original validation
            if is_match:
                # High merchant score (60+) - accept
                if merchant_score >= 60:
                    pass  # Accept
                # Medium-high merchant score (40-59) - require better amount match
                elif merchant_score >= 40:
                    # Reject if amount difference is too high (> 5%)
                    if match_details['amount_diff_percent'] > 0.05:
                        is_match = False
                # Medium merchant score (25-39) - require good amount match
                elif merchant_score >= 25:
                    # Reject if amount difference > 3%
                    if match_details['amount_diff_percent'] > 0.03:
                        is_match = False
                # Low merchant score (< 25) - require very close amount
                else:
                    # Only accept if amount is nearly exact (< 1%)
                    if match_details['amount_diff_percent'] > 0.01:
                        is_match = False
        
        # Calculate confidence score (0-100)
        confidence = 0
        
        # Amount matching worth 50 points
        if match_details['amount_match']:
            amount_score = 50 * (1 - min(match_details['amount_diff_percent'], 1.0))
            confidence += amount_score
        
        # Merchant matching worth 35 points
        confidence += merchant_score * 0.35
        
        # Date proximity worth 15 points (bonus)
        confidence += date_score * 0.15
        
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
        # Build amount frequency map for exact match boosting
        # Count how many transactions have each exact amount
        amount_frequency = {}
        for trans in transactions:
            if 'amount' in trans and trans['amount'] is not None:
                amount_key = abs(float(trans['amount']))
                amount_frequency[amount_key] = amount_frequency.get(amount_key, 0) + 1
        
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
                
                # EXACT AMOUNT BOOST: If amount is exact match AND unique in statement, boost confidence
                if details.get('amount_match') and details.get('amount_diff_percent', 1.0) < 0.001:
                    # Exact match (< 0.1% difference)
                    trans_amount = abs(float(transaction.get('amount', 0)))
                    
                    # Check if this amount appears only once in the statement
                    if amount_frequency.get(trans_amount, 0) == 1:
                        # Unique amount! Boost confidence significantly
                        old_confidence = confidence
                        # INCREASED BOOST: +30 points for unique exact match (was +20)
                        # This makes unique exact matches very reliable (typically 85-100% confidence)
                        confidence = min(100, confidence + 30)
                        details['exact_amount_boost'] = True
                        details['boosted_confidence'] = f"{old_confidence} → {confidence} (unique exact match)"
                
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
