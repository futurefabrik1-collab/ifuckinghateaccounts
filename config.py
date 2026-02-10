"""
Configuration Management for Receipt Checker

Centralized configuration using environment variables with sensible defaults.
Create a .env file in the project root to override these values.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""
    
    # Base paths
    BASE_DIR = Path(os.getenv('RECEIPT_CHECKER_BASE_DIR', Path(__file__).parent))
    STATEMENTS_FOLDER = BASE_DIR / 'statements'
    
    # Upload limits
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 50 * 1024 * 1024))  # 50MB default
    MAX_RECEIPTS_PER_UPLOAD = int(os.getenv('MAX_RECEIPTS_PER_UPLOAD', 50))
    
    # Allowed file types
    ALLOWED_STATEMENT_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    ALLOWED_RECEIPT_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
    
    ALLOWED_MIME_TYPES = {
        'application/pdf': ['.pdf'],
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        'text/csv': ['.csv'],
        'application/vnd.ms-excel': ['.xls'],
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
    }
    
    # Matching parameters
    AMOUNT_TOLERANCE_EUR = float(os.getenv('AMOUNT_TOLERANCE_EUR', 0.001))  # 0.1%
    AMOUNT_TOLERANCE_NON_EUR = float(os.getenv('AMOUNT_TOLERANCE_NON_EUR', 0.20))  # 20%
    MERCHANT_THRESHOLD = int(os.getenv('MERCHANT_THRESHOLD', 60))
    
    # Server configuration
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    PORT = int(os.getenv('PORT', 5001))
    HOST = os.getenv('HOST', '127.0.0.1')
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    
    # OCR Configuration
    TESSERACT_PATH = os.getenv('TESSERACT_PATH', '/opt/homebrew/bin/tesseract')
    OCR_CACHE_ENABLED = os.getenv('OCR_CACHE_ENABLED', 'True').lower() == 'true'
    OCR_CACHE_DIR = BASE_DIR / '.cache' / 'ocr'
    
    # Backup configuration
    BACKUP_ENABLED = os.getenv('BACKUP_ENABLED', 'True').lower() == 'true'
    BACKUP_RETENTION_COUNT = int(os.getenv('BACKUP_RETENTION_COUNT', 10))
    
    # Undo history
    UNDO_HISTORY_SIZE = int(os.getenv('UNDO_HISTORY_SIZE', 50))
    UNDO_PERSIST = os.getenv('UNDO_PERSIST', 'True').lower() == 'true'
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = BASE_DIR / 'logs' / 'receipt_checker.log'
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10 * 1024 * 1024))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))
    
    # Rate limiting
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    RATE_LIMIT_DEFAULT = os.getenv('RATE_LIMIT_DEFAULT', '200 per day, 50 per hour')
    RATE_LIMIT_STORAGE_URL = os.getenv('RATE_LIMIT_STORAGE_URL', 'memory://')
    
    @classmethod
    def init_app(cls):
        """Initialize application directories"""
        cls.STATEMENTS_FOLDER.mkdir(parents=True, exist_ok=True)
        cls.OCR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        errors = []
        
        if cls.MAX_FILE_SIZE < 1024:
            errors.append("MAX_FILE_SIZE must be at least 1KB")
        
        if cls.AMOUNT_TOLERANCE_EUR < 0 or cls.AMOUNT_TOLERANCE_EUR > 1:
            errors.append("AMOUNT_TOLERANCE_EUR must be between 0 and 1")
        
        if cls.MERCHANT_THRESHOLD < 0 or cls.MERCHANT_THRESHOLD > 100:
            errors.append("MERCHANT_THRESHOLD must be between 0 and 100")
        
        if cls.PORT < 1 or cls.PORT > 65535:
            errors.append("PORT must be between 1 and 65535")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(errors))
        
        return True


class MatchingWeights:
    """Constants for matching algorithm weights"""
    AMOUNT_WEIGHT = 0.50  # 50 points
    MERCHANT_WEIGHT = 0.35  # 35 points
    DATE_WEIGHT = 0.15  # 15 points
    UNIQUE_EXACT_MATCH_BOOST = 30
    MERCHANT_MIN_SCORE = 60


class Thresholds:
    """Matching thresholds"""
    MERCHANT_HIGH = 60
    MERCHANT_MEDIUM_HIGH = 40
    MERCHANT_MEDIUM = 25
    AMOUNT_DIFF_HIGH = 0.05
    AMOUNT_DIFF_MEDIUM = 0.03
    AMOUNT_DIFF_LOW = 0.01


# Initialize on import
Config.init_app()
