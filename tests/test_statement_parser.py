"""
Tests for Statement Parser

Tests CSV parsing and German number format handling.
"""

import pytest
import pandas as pd
from src.statement_parser import StatementParser


class TestStatementLoading:
    """Test statement file loading"""
    
    def test_load_csv(self, sample_statement_csv):
        """Test loading CSV file"""
        parser = StatementParser(str(sample_statement_csv))
        df = parser.load_statement(
            date_column='Buchungstag',
            amount_column='Betrag',
            description_column='Verwendungszweck'
        )
        
        assert df is not None
        assert len(df) == 5
        assert 'date' in df.columns
        assert 'amount' in df.columns
        assert 'description' in df.columns
    
    def test_german_number_format(self, sample_statement_csv):
        """Test German number format parsing (comma decimal)"""
        parser = StatementParser(str(sample_statement_csv))
        df = parser.load_statement(
            date_column='Buchungstag',
            amount_column='Betrag',
            description_column='Verwendungszweck'
        )
        
        # Check that amounts are parsed correctly
        assert df.loc[0, 'amount'] == -44.84
        assert df.loc[1, 'amount'] == -25.00
        assert df.loc[4, 'amount'] == -3.26
    
    def test_date_parsing(self, sample_statement_csv):
        """Test German date format parsing (DD.MM.YYYY)"""
        parser = StatementParser(str(sample_statement_csv))
        df = parser.load_statement(
            date_column='Buchungstag',
            amount_column='Betrag',
            description_column='Verwendungszweck'
        )
        
        # Check dates are parsed
        assert pd.notna(df.loc[0, 'date'])
        assert df.loc[0, 'date'].day == 10
        assert df.loc[0, 'date'].month == 1
        assert df.loc[0, 'date'].year == 2026


class TestTransactionRetrieval:
    """Test transaction retrieval methods"""
    
    def test_get_transactions(self, statement_parser):
        """Test getting all transactions"""
        statement_parser.load_statement(
            date_column='Buchungstag',
            amount_column='Betrag',
            description_column='Verwendungszweck'
        )
        
        transactions = statement_parser.get_transactions()
        
        assert isinstance(transactions, list)
        assert len(transactions) == 5
        assert all('date' in t for t in transactions)
        assert all('amount' in t for t in transactions)
    
    def test_get_unmatched_transactions(self, statement_parser):
        """Test getting unmatched transactions"""
        statement_parser.load_statement(
            date_column='Buchungstag',
            amount_column='Betrag',
            description_column='Verwendungszweck'
        )
        
        unmatched = statement_parser.get_unmatched_transactions()
        
        # All should be unmatched initially
        assert len(unmatched) == 5


class TestMatchMarking:
    """Test marking transactions as matched"""
    
    def test_mark_as_matched(self, statement_parser):
        """Test marking a transaction as matched"""
        statement_parser.load_statement(
            date_column='Buchungstag',
            amount_column='Betrag',
            description_column='Verwendungszweck'
        )
        
        # Mark first transaction as matched
        statement_parser.mark_as_matched(0, 'receipt1.pdf')
        
        # Check it's marked
        assert statement_parser.df.loc[0, 'matched'] is True
        assert statement_parser.df.loc[0, 'matched_receipt'] == 'receipt1.pdf'
        
        # Others should be unmatched
        assert statement_parser.df.loc[1, 'matched'] is False


class TestExport:
    """Test exporting results"""
    
    def test_export_csv(self, statement_parser, temp_dir):
        """Test exporting to CSV"""
        statement_parser.load_statement(
            date_column='Buchungstag',
            amount_column='Betrag',
            description_column='Verwendungszweck'
        )
        
        output_file = temp_dir / 'output.csv'
        statement_parser.export_results(str(output_file))
        
        assert output_file.exists()
        
        # Load and verify
        df = pd.read_csv(output_file)
        assert len(df) == 5
