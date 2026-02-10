"""
Tests for Security Utilities

Tests validation and sanitization functions.
"""

import pytest
from pathlib import Path
from src.utils.security import (
    sanitize_filename,
    validate_path_traversal,
    validate_statement_name,
    validate_row_number,
    SecurityError
)


class TestFilenameSanitization:
    """Test filename sanitization"""
    
    def test_simple_filename(self):
        """Test simple valid filename"""
        result = sanitize_filename('test.pdf')
        assert result == 'test.pdf'
    
    def test_remove_path_separators(self):
        """Test removal of path separators"""
        result = sanitize_filename('../../../etc/passwd')
        assert '/' not in result
        assert '\\' not in result
        assert '..' not in result
    
    def test_remove_null_bytes(self):
        """Test removal of null bytes"""
        result = sanitize_filename('test\x00.pdf')
        assert '\x00' not in result
    
    def test_remove_leading_dots(self):
        """Test removal of leading dots"""
        result = sanitize_filename('.hidden_file.pdf')
        assert not result.startswith('.')
    
    def test_long_filename(self):
        """Test filename length limiting"""
        long_name = 'a' * 300 + '.pdf'
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith('.pdf')
    
    def test_empty_filename_raises(self):
        """Test that empty filename raises error"""
        with pytest.raises(SecurityError):
            sanitize_filename('')
        
        with pytest.raises(SecurityError):
            sanitize_filename('.')


class TestPathTraversal:
    """Test path traversal validation"""
    
    def test_valid_path(self, temp_dir):
        """Test valid path within base directory"""
        base = temp_dir
        requested = temp_dir / 'subdir' / 'file.txt'
        
        result = validate_path_traversal(base, requested)
        assert result == requested.resolve()
    
    def test_path_traversal_attack(self, temp_dir):
        """Test detection of path traversal attack"""
        base = temp_dir / 'statements'
        requested = temp_dir / '..' / '..' / 'etc' / 'passwd'
        
        with pytest.raises(SecurityError):
            validate_path_traversal(base, requested)
    
    def test_relative_path_escape(self, temp_dir):
        """Test detection of relative path escape"""
        base = temp_dir / 'statements'
        requested = base / '..' / '..' / 'etc' / 'passwd'
        
        with pytest.raises(SecurityError):
            validate_path_traversal(base, requested)


class TestStatementNameValidation:
    """Test statement name validation"""
    
    def test_valid_statement_name(self):
        """Test valid statement name"""
        result = validate_statement_name('statement_2026.csv')
        assert result == 'statement_2026.csv'
    
    def test_reject_path_traversal(self):
        """Test rejection of path traversal in name"""
        with pytest.raises(SecurityError):
            validate_statement_name('../etc/passwd')
        
        with pytest.raises(SecurityError):
            validate_statement_name('../../file.csv')
    
    def test_reject_absolute_path(self):
        """Test rejection of absolute paths"""
        with pytest.raises(SecurityError):
            validate_statement_name('/etc/passwd')
    
    def test_reject_too_long(self):
        """Test rejection of overly long names"""
        long_name = 'a' * 300 + '.csv'
        with pytest.raises(SecurityError):
            validate_statement_name(long_name)


class TestRowNumberValidation:
    """Test row number validation"""
    
    def test_valid_row_number(self):
        """Test valid row number"""
        result = validate_row_number(5)
        assert result == 5
    
    def test_string_row_number(self):
        """Test converting string to int"""
        result = validate_row_number('10')
        assert result == 10
    
    def test_reject_negative(self):
        """Test rejection of negative numbers"""
        with pytest.raises(SecurityError):
            validate_row_number(-1)
    
    def test_reject_zero(self):
        """Test rejection of zero"""
        with pytest.raises(SecurityError):
            validate_row_number(0)
    
    def test_reject_too_large(self):
        """Test rejection of overly large numbers"""
        with pytest.raises(SecurityError):
            validate_row_number(999999)
    
    def test_reject_invalid_type(self):
        """Test rejection of invalid types"""
        with pytest.raises(SecurityError):
            validate_row_number('invalid')
        
        with pytest.raises(SecurityError):
            validate_row_number(None)
