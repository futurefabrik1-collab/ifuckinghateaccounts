#!/usr/bin/env python3
"""Encryption utilities for sensitive data."""

import os
from cryptography.fernet import Fernet
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""
    
    def __init__(self):
        """Initialize encryption service with key from environment."""
        key = os.getenv('ENCRYPTION_KEY')
        
        if not key:
            raise ValueError(
                "ENCRYPTION_KEY must be set in environment variables. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        self.cipher = Fernet(key.encode())
    
    def encrypt(self, text: str) -> str:
        """
        Encrypt plaintext string.
        
        Args:
            text: Plaintext to encrypt
            
        Returns:
            Encrypted text as base64 string
        """
        if not text:
            return ""
        
        encrypted_bytes = self.cipher.encrypt(text.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt encrypted string.
        
        Args:
            encrypted_text: Encrypted text to decrypt
            
        Returns:
            Decrypted plaintext
        """
        if not encrypted_text:
            return ""
        
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_text.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            print(f"Decryption error: {e}")
            return ""
    
    def encrypt_dict(self, data: dict, fields: list) -> dict:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary with data
            fields: List of field names to encrypt
            
        Returns:
            Dictionary with encrypted fields
        """
        encrypted_data = data.copy()
        
        for field in fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt(str(encrypted_data[field]))
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict, fields: list) -> dict:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary with encrypted data
            fields: List of field names to decrypt
            
        Returns:
            Dictionary with decrypted fields
        """
        decrypted_data = data.copy()
        
        for field in fields:
            if field in decrypted_data and decrypted_data[field]:
                decrypted_data[field] = self.decrypt(decrypted_data[field])
        
        return decrypted_data


# Global instance
encryption_service = EncryptionService()


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Returns:
        Base64-encoded encryption key
    """
    return Fernet.generate_key().decode()


if __name__ == '__main__':
    # Generate a new key when run directly
    print("Generated encryption key:")
    print(generate_encryption_key())
    print("\nAdd this to your .env file as ENCRYPTION_KEY=...")
