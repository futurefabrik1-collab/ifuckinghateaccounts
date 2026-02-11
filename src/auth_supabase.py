#!/usr/bin/env python3
"""
Supabase Authentication Service

This module provides authentication using Supabase Auth,
replacing the existing local auth system for SaaS.
"""

from typing import Tuple, Optional, Dict, Any
from flask_login import UserMixin
from src.supabase_client import supabase_client
from src.utils.logging import setup_logger

logger = setup_logger(__name__)


class SupabaseUser(UserMixin):
    """User class for Flask-Login compatible with Supabase."""
    
    def __init__(self, user_data: Dict[str, Any]):
        """
        Initialize user from Supabase user data.
        
        Args:
            user_data: User data from Supabase auth
        """
        self.id = user_data.get('id')
        self.email = user_data.get('email')
        self.created_at = user_data.get('created_at')
        self.user_metadata = user_data.get('user_metadata', {})
        
        # Extract profile data
        self.username = self.user_metadata.get('username', self.email.split('@')[0])
        self.full_name = self.user_metadata.get('full_name', '')
    
    def get_id(self):
        """Return user ID for Flask-Login."""
        return str(self.id)
    
    @property
    def is_authenticated(self):
        """User is authenticated."""
        return True
    
    @property
    def is_active(self):
        """User is active."""
        return True
    
    @property
    def is_anonymous(self):
        """User is not anonymous."""
        return False
    
    def __repr__(self):
        return f'<SupabaseUser {self.email}>'


class SupabaseAuthService:
    """Authentication service using Supabase."""
    
    @staticmethod
    def register_user(email: str, password: str, username: str = None, 
                     full_name: str = None) -> Tuple[bool, str, Optional[SupabaseUser]]:
        """
        Register a new user with Supabase.
        
        Args:
            email: User email
            password: User password
            username: Optional username
            full_name: Optional full name
            
        Returns:
            Tuple of (success, message, user_object)
        """
        try:
            # Validate inputs
            if not email or not password:
                return False, "Email and password are required", None
            
            if len(password) < 8:
                return False, "Password must be at least 8 characters", None
            
            # Register with Supabase
            result = supabase_client.sign_up(email, password)
            
            if not result['success']:
                error_msg = result.get('error', 'Registration failed')
                logger.error(f"Registration failed for {email}: {error_msg}")
                return False, error_msg, None
            
            # Create user object
            user = SupabaseUser(result['user'])
            
            logger.info(f"User registered successfully: {email}")
            return True, "Registration successful", user
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return False, "An error occurred during registration", None
    
    @staticmethod
    def authenticate_user(email: str, password: str) -> Tuple[bool, str, Optional[SupabaseUser]]:
        """
        Authenticate user with Supabase.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Tuple of (success, message, user_object)
        """
        try:
            if not email or not password:
                return False, "Email and password are required", None
            
            # Sign in with Supabase
            result = supabase_client.sign_in(email, password)
            
            if not result['success']:
                logger.warning(f"Failed login attempt for: {email}")
                return False, "Invalid email or password", None
            
            # Create user object
            user = SupabaseUser(result['user'])
            
            logger.info(f"User authenticated successfully: {email}")
            return True, "Login successful", user
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False, "An error occurred during login", None
    
    @staticmethod
    def load_user_by_id(user_id: str) -> Optional[SupabaseUser]:
        """
        Load user by ID from session.
        
        Args:
            user_id: User ID
            
        Returns:
            SupabaseUser object or None
        """
        try:
            # In a real implementation, you'd validate the session token
            # For now, we'll get user from profile
            result = supabase_client.select('user_profiles', {'id': user_id})
            
            if result['success'] and result['data']:
                profile = result['data'][0]
                # Construct minimal user data
                user_data = {
                    'id': user_id,
                    'email': profile.get('email', ''),
                    'user_metadata': {
                        'full_name': profile.get('full_name', ''),
                        'username': profile.get('username', '')
                    }
                }
                return SupabaseUser(user_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading user {user_id}: {str(e)}")
            return None
    
    @staticmethod
    def logout_user(user_id: str) -> bool:
        """
        Logout user from Supabase.
        
        Args:
            user_id: User ID
            
        Returns:
            Success boolean
        """
        try:
            result = supabase_client.sign_out()
            logger.info(f"User logged out: {user_id}")
            return result['success']
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return False
    
    @staticmethod
    def check_subscription_active(user_id: str) -> bool:
        """
        Check if user has an active subscription.
        
        Args:
            user_id: User ID
            
        Returns:
            True if subscription is active or trialing
        """
        try:
            result = supabase_client.select('subscriptions', {'user_id': user_id})
            
            if result['success'] and result['data']:
                subscription = result['data'][0]
                return subscription['status'] in ['active', 'trialing']
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking subscription for {user_id}: {str(e)}")
            return False
    
    @staticmethod
    def get_user_subscription(user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's subscription details.
        
        Args:
            user_id: User ID
            
        Returns:
            Subscription dict or None
        """
        try:
            result = supabase_client.select('subscriptions', {'user_id': user_id})
            
            if result['success'] and result['data']:
                return result['data'][0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting subscription for {user_id}: {str(e)}")
            return None
