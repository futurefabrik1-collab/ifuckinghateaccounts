"""
Database Models for Receipt Checker

SQLAlchemy models with encryption for sensitive data.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import os
import base64

Base = declarative_base()


class User(Base):
    """User account model"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Encryption key for this user's data (encrypted itself)
    encryption_key = Column(LargeBinary, nullable=False)
    
    # Relationships
    statements = relationship('Statement', back_populates='user', cascade='all, delete-orphan')
    
    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.set_password(password)
        self.encryption_key = Fernet.generate_key()
    
    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def get_cipher(self):
        """Get Fernet cipher for encrypting/decrypting user data"""
        return Fernet(self.encryption_key)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Statement(Base):
    """Bank statement model"""
    __tablename__ = 'statements'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    file_path = Column(String(500))  # Path to original statement file
    
    # Relationships
    user = relationship('User', back_populates='statements')
    transactions = relationship('Transaction', back_populates='statement', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Statement {self.name}>'


class Transaction(Base):
    """Transaction from bank statement"""
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    statement_id = Column(Integer, ForeignKey('statements.id'), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    
    # Transaction data
    date = Column(DateTime, nullable=False, index=True)
    amount = Column(Float, nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    # Matching data
    matched = Column(Boolean, default=False, index=True)
    receipt_id = Column(Integer, ForeignKey('receipts.id'), nullable=True)
    match_confidence = Column(Integer, default=0)
    no_receipt_needed = Column(Boolean, default=False)
    
    # Ownership
    owner_mark = Column(Boolean, default=False)
    owner_flo = Column(Boolean, default=False)
    
    # Category and tags (encrypted)
    category = Column(String(100))
    tags = Column(Text)  # JSON string, encrypted
    notes = Column(Text)  # Encrypted
    
    # Relationships
    statement = relationship('Statement', back_populates='transactions')
    receipt = relationship('Receipt', back_populates='transactions')
    
    def __repr__(self):
        return f'<Transaction {self.id}: {self.amount} on {self.date}>'


class Receipt(Base):
    """Receipt metadata (OCR text, not the file itself)"""
    __tablename__ = 'receipts'
    
    id = Column(Integer, primary_key=True)
    statement_id = Column(Integer, ForeignKey('statements.id'), nullable=False, index=True)
    
    # File information
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # Relative path to file
    file_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256 hash
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Extracted data (ENCRYPTED)
    ocr_text_encrypted = Column(LargeBinary)  # Encrypted OCR text
    amount = Column(Float)
    date = Column(DateTime, index=True)
    merchant = Column(String(255), index=True)
    currency = Column(String(3))
    
    # Metadata
    is_matched = Column(Boolean, default=False, index=True)
    
    # Relationships
    statement = relationship('Statement')
    transactions = relationship('Transaction', back_populates='receipt')
    
    def encrypt_ocr_text(self, text: str, cipher: Fernet):
        """Encrypt OCR text"""
        self.ocr_text_encrypted = cipher.encrypt(text.encode('utf-8'))
    
    def decrypt_ocr_text(self, cipher: Fernet) -> str:
        """Decrypt OCR text"""
        if self.ocr_text_encrypted:
            return cipher.decrypt(self.ocr_text_encrypted).decode('utf-8')
        return ""
    
    def __repr__(self):
        return f'<Receipt {self.filename}>'


class AuditLog(Base):
    """Audit log for security and compliance"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    action = Column(String(100), nullable=False, index=True)  # 'login', 'upload', 'match', 'delete', etc.
    resource_type = Column(String(50))  # 'statement', 'receipt', 'transaction'
    resource_id = Column(Integer)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    details = Column(Text)  # JSON string with additional details
    
    # Relationship
    user = relationship('User')
    
    def __repr__(self):
        return f'<AuditLog {self.action} by user {self.user_id} at {self.timestamp}>'
