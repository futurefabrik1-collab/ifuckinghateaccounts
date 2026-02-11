#!/usr/bin/env python3
"""Supabase client for authentication and database operations."""

import os
from typing import Optional, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SupabaseClient:
    """Wrapper for Supabase client with helper methods."""
    
    def __init__(self):
        """Initialize Supabase client."""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')
        
        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables"
            )
        
        self.client: Client = create_client(url, key)
        self.service_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    # Authentication methods
    def sign_up(self, email: str, password: str) -> Dict[str, Any]:
        """Register a new user."""
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password
            })
            return {
                "success": True,
                "user": response.user,
                "session": response.session
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in an existing user."""
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return {
                "success": True,
                "user": response.user,
                "session": response.session
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def sign_out(self) -> Dict[str, Any]:
        """Sign out current user."""
        try:
            self.client.auth.sign_out()
            return {"success": True}
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user from access token."""
        try:
            response = self.client.auth.get_user(access_token)
            return response.user
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh user session."""
        try:
            response = self.client.auth.refresh_session(refresh_token)
            return {
                "success": True,
                "session": response.session
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # Database methods (with RLS automatically enforced)
    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert data into table."""
        try:
            response = self.client.table(table).insert(data).execute()
            return {
                "success": True,
                "data": response.data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def select(self, table: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Select data from table."""
        try:
            query = self.client.table(table).select("*")
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            response = query.execute()
            return {
                "success": True,
                "data": response.data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def update(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
        """Update data in table."""
        try:
            query = self.client.table(table).update(data)
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            response = query.execute()
            return {
                "success": True,
                "data": response.data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete(self, table: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Delete data from table."""
        try:
            query = self.client.table(table).delete()
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            response = query.execute()
            return {
                "success": True,
                "data": response.data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Global instance
supabase_client = SupabaseClient()
