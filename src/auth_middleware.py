#!/usr/bin/env python3
"""Authentication middleware for Flask routes."""

from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from typing import Optional, Dict, Any
from src.supabase_client import supabase_client


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user from session.
    
    Returns:
        User object or None if not authenticated
    """
    access_token = session.get('access_token')
    
    if not access_token:
        return None
    
    return supabase_client.get_user(access_token)


def get_current_user_id() -> Optional[str]:
    """
    Get current user's ID from session.
    
    Returns:
        User ID or None if not authenticated
    """
    user = get_current_user()
    return user.get('id') if user else None


def login_required(f):
    """
    Decorator to require authentication for routes.
    Redirects to login page if not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if not user:
            # Save the original URL to redirect back after login
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    
    return decorated_function


def api_login_required(f):
    """
    Decorator to require authentication for API routes.
    Returns 401 JSON error if not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if not user:
            return jsonify({
                'error': 'Authentication required',
                'authenticated': False
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


def subscription_required(f):
    """
    Decorator to require active subscription.
    Redirects to subscription page if not subscribed.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if not user:
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))
        
        # Check subscription status
        user_id = user.get('id')
        result = supabase_client.select('subscriptions', {'user_id': user_id})
        
        if not result['success'] or not result['data']:
            return redirect(url_for('subscription.checkout'))
        
        subscription = result['data'][0]
        
        # Check if subscription is active or trialing
        if subscription['status'] not in ['active', 'trialing']:
            return redirect(url_for('subscription.manage'))
        
        return f(*args, **kwargs)
    
    return decorated_function


def api_subscription_required(f):
    """
    Decorator to require active subscription for API routes.
    Returns 403 JSON error if subscription not active.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if not user:
            return jsonify({
                'error': 'Authentication required',
                'authenticated': False
            }), 401
        
        # Check subscription status
        user_id = user.get('id')
        result = supabase_client.select('subscriptions', {'user_id': user_id})
        
        if not result['success'] or not result['data']:
            return jsonify({
                'error': 'Active subscription required',
                'subscribed': False
            }), 403
        
        subscription = result['data'][0]
        
        if subscription['status'] not in ['active', 'trialing']:
            return jsonify({
                'error': 'Active subscription required',
                'subscribed': False,
                'status': subscription['status']
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_user_subscription(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user's subscription details.
    
    Args:
        user_id: User ID
        
    Returns:
        Subscription object or None
    """
    result = supabase_client.select('subscriptions', {'user_id': user_id})
    
    if result['success'] and result['data']:
        return result['data'][0]
    
    return None


def is_subscription_active(user_id: str) -> bool:
    """
    Check if user has an active subscription.
    
    Args:
        user_id: User ID
        
    Returns:
        True if subscription is active or trialing
    """
    subscription = get_user_subscription(user_id)
    
    if not subscription:
        return False
    
    return subscription['status'] in ['active', 'trialing']
