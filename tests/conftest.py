"""
Pytest Configuration and Fixtures

Provides reusable test fixtures for the test suite.
"""

import pytest
from pathlib import Path
from datetime import datetime
import pandas as pd
import tempfile
import shutil

from src.matcher import ReceiptMatcher
from src.statement_parser import StatementParser
from src.receipt_processor import ReceiptProcessor


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_statement_csv(temp_dir):
    """Create a sample German bank statement CSV"""
    csv_content = """Buchungstag;Betrag;Verwendungszweck
10.01.2026;-44,84;REWE SAGT DANKE/Berlin
15.01.2026;-25,00;Netflix Subscription
20.01.2026;-135,01;Vattenfall Europe Sales GmbH
25.01.2026;-18,50;Amazon.de Order 123
30.01.2026;-3,26;Mehrwertsteuer"""
    
    csv_file = temp_dir / "test_statement.csv"
    csv_file.write_text(csv_content, encoding='utf-8-sig')
    
    return csv_file


@pytest.fixture
def sample_transactions():
    """Sample transaction data"""
    return [
        {
            'date': datetime(2026, 1, 10),
            'amount': -44.84,
            'description': 'REWE SAGT DANKE/Berlin'
        },
        {
            'date': datetime(2026, 1, 15),
            'amount': -25.00,
            'description': 'Netflix Subscription'
        },
        {
            'date': datetime(2026, 1, 20),
            'amount': -135.01,
            'description': 'Vattenfall Europe Sales GmbH'
        }
    ]


@pytest.fixture
def sample_receipts():
    """Sample receipt data"""
    return [
        {
            'filename': 'receipt1.pdf',
            'path': '/tmp/receipt1.pdf',
            'amount': 44.84,
            'date': datetime(2026, 1, 10),
            'merchant': 'REWE',
            'currency': 'EUR'
        },
        {
            'filename': 'receipt2.pdf',
            'path': '/tmp/receipt2.pdf',
            'amount': 25.00,
            'date': datetime(2026, 1, 15),
            'merchant': 'Netflix',
            'currency': 'EUR'
        },
        {
            'filename': 'receipt3.pdf',
            'path': '/tmp/receipt3.pdf',
            'amount': 135.01,
            'date': datetime(2026, 1, 20),
            'merchant': 'Vattenfall',
            'currency': 'EUR'
        }
    ]


@pytest.fixture
def receipt_matcher():
    """Create a ReceiptMatcher instance"""
    return ReceiptMatcher()


@pytest.fixture
def statement_parser(sample_statement_csv):
    """Create a StatementParser instance with sample data"""
    return StatementParser(str(sample_statement_csv))
