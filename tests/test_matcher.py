"""
Tests for Receipt Matcher

Tests the matching algorithm logic.
"""

import pytest
from datetime import datetime
from src.matcher import ReceiptMatcher


class TestAmountMatching:
    """Test amount matching logic"""
    
    def test_exact_eur_match(self, receipt_matcher):
        """Test exact EUR amount match"""
        is_match, diff = receipt_matcher.is_amount_match(100.00, 100.00, is_eur=True)
        assert is_match is True
        assert diff == 0.0
    
    def test_eur_within_tolerance(self, receipt_matcher):
        """Test EUR amount within tolerance"""
        is_match, diff = receipt_matcher.is_amount_match(100.00, 100.05, is_eur=True)
        assert is_match is True
        assert diff < 0.001
    
    def test_eur_outside_tolerance(self, receipt_matcher):
        """Test EUR amount outside tolerance"""
        is_match, diff = receipt_matcher.is_amount_match(100.00, 105.00, is_eur=True)
        assert is_match is False
        assert diff > 0.001
    
    def test_non_eur_currency_conversion(self, receipt_matcher):
        """Test non-EUR with 20% tolerance"""
        # $100 USD should match €92 EUR (within 20% tolerance)
        is_match, diff = receipt_matcher.is_amount_match(92.0, 100.0, is_eur=False)
        assert is_match is True
    
    def test_negative_amounts(self, receipt_matcher):
        """Test handling of negative amounts"""
        is_match, diff = receipt_matcher.is_amount_match(-100.00, 100.00, is_eur=True)
        assert is_match is True  # Should compare absolute values
    
    def test_zero_amounts(self, receipt_matcher):
        """Test zero amount handling"""
        is_match, diff = receipt_matcher.is_amount_match(0.0, 0.0, is_eur=True)
        assert is_match is True


class TestMerchantMatching:
    """Test merchant name matching"""
    
    def test_exact_merchant_match(self, receipt_matcher):
        """Test exact merchant name match"""
        score = receipt_matcher.calculate_merchant_similarity('REWE', 'REWE')
        assert score == 100
    
    def test_partial_merchant_match(self, receipt_matcher):
        """Test partial merchant name match"""
        score = receipt_matcher.calculate_merchant_similarity('REWE SAGT DANKE', 'REWE')
        assert score >= 60  # Should get high partial match score
    
    def test_different_merchants(self, receipt_matcher):
        """Test completely different merchants"""
        score = receipt_matcher.calculate_merchant_similarity('REWE', 'Netflix')
        assert score < 30
    
    def test_case_insensitive(self, receipt_matcher):
        """Test case-insensitive matching"""
        score = receipt_matcher.calculate_merchant_similarity('REWE', 'rewe')
        assert score == 100


class TestTransactionMatching:
    """Test full transaction matching"""
    
    def test_perfect_match(self, receipt_matcher):
        """Test perfect match with all criteria"""
        transaction = {
            'date': datetime(2026, 1, 10),
            'amount': 44.84,
            'description': 'REWE SAGT DANKE/Berlin'
        }
        
        receipt = {
            'date': datetime(2026, 1, 10),
            'amount': 44.84,
            'merchant': 'REWE',
            'currency': 'EUR'
        }
        
        is_match, confidence, details = receipt_matcher.match_transaction_to_receipt(
            transaction, receipt
        )
        
        assert is_match is True
        assert confidence >= 80
        assert details['amount_match'] is True
    
    def test_amount_match_only(self, receipt_matcher):
        """Test match with amount but no merchant"""
        transaction = {
            'date': datetime(2026, 1, 10),
            'amount': 44.84,
            'description': 'Unknown Merchant'
        }
        
        receipt = {
            'date': datetime(2026, 1, 10),
            'amount': 44.84,
            'merchant': 'REWE',
            'currency': 'EUR'
        }
        
        is_match, confidence, details = receipt_matcher.match_transaction_to_receipt(
            transaction, receipt
        )
        
        assert is_match is True  # Amount match should be enough
        assert details['amount_match'] is True
    
    def test_reject_bank_fees(self, receipt_matcher):
        """Test rejection of bank fees and taxes"""
        transaction = {
            'date': datetime(2026, 1, 10),
            'amount': 3.26,
            'description': 'MEHRWERTSTEUER'
        }
        
        receipt = {
            'date': datetime(2026, 1, 10),
            'amount': 3.26,
            'merchant': 'Some Store',
            'currency': 'EUR'
        }
        
        is_match, confidence, details = receipt_matcher.match_transaction_to_receipt(
            transaction, receipt
        )
        
        assert is_match is False  # Should reject tax transactions


class TestBatchMatching:
    """Test matching multiple transactions"""
    
    def test_match_all_transactions(self, receipt_matcher, sample_transactions, sample_receipts):
        """Test matching all transactions with receipts"""
        results = receipt_matcher.match_all_transactions(sample_transactions, sample_receipts)
        
        assert len(results) == len(sample_transactions)
        
        # Count matches
        matched_count = sum(1 for r in results if r['matched'])
        assert matched_count >= 2  # At least 2 should match
    
    def test_no_duplicate_matches(self, receipt_matcher, sample_transactions, sample_receipts):
        """Test that receipts aren't matched to multiple transactions"""
        results = receipt_matcher.match_all_transactions(sample_transactions, sample_receipts)
        
        matched_receipts = [r['receipt']['filename'] for r in results if r['matched']]
        
        # No duplicates in matched receipts
        assert len(matched_receipts) == len(set(matched_receipts))


class TestCurrencyConversion:
    """Test currency conversion"""
    
    def test_eur_to_eur(self, receipt_matcher):
        """Test EUR to EUR (no conversion)"""
        result = receipt_matcher.convert_currency_to_eur(100.0, 'EUR')
        assert result == 100.0
    
    def test_usd_to_eur(self, receipt_matcher):
        """Test USD to EUR conversion"""
        result = receipt_matcher.convert_currency_to_eur(100.0, 'USD')
        assert 90 <= result <= 95  # Approximate rate
    
    def test_gbp_to_eur(self, receipt_matcher):
        """Test GBP to EUR conversion"""
        result = receipt_matcher.convert_currency_to_eur(100.0, 'GBP')
        assert 115 <= result <= 125  # Approximate rate


class TestReportGeneration:
    """Test matching report generation"""
    
    def test_generate_report(self, receipt_matcher, sample_transactions, sample_receipts):
        """Test report generation"""
        results = receipt_matcher.match_all_transactions(sample_transactions, sample_receipts)
        report = receipt_matcher.generate_report(results)
        
        assert 'total_transactions' in report
        assert 'matched' in report
        assert 'unmatched' in report
        assert 'match_rate' in report
        assert 'average_confidence' in report
        
        assert report['total_transactions'] == len(sample_transactions)
        assert report['matched'] + report['unmatched'] == report['total_transactions']
