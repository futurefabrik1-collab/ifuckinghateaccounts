#!/usr/bin/env python3
"""Stripe client for subscription billing."""

import os
import stripe
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class StripeClient:
    """Wrapper for Stripe API operations."""
    
    def __init__(self):
        """Initialize Stripe client."""
        secret_key = os.getenv('STRIPE_SECRET_KEY')
        
        if not secret_key:
            raise ValueError("STRIPE_SECRET_KEY must be set in environment variables")
        
        stripe.api_key = secret_key
        self.price_id = os.getenv('STRIPE_PRICE_ID')
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    def create_customer(self, email: str, name: Optional[str] = None, 
                       metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create a Stripe customer.
        
        Args:
            email: Customer email
            name: Customer name (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            Customer object or error
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            return {
                "success": True,
                "customer": customer
            }
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_checkout_session(self, customer_id: str, success_url: str, 
                               cancel_url: str, trial_days: int = 14) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session for subscription.
        
        Args:
            customer_id: Stripe customer ID
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment cancelled
            trial_days: Number of free trial days (default: 14)
            
        Returns:
            Checkout session or error
        """
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': self.price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                subscription_data={
                    'trial_period_days': trial_days,
                },
                allow_promotion_codes=True,
            )
            return {
                "success": True,
                "session": session
            }
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_portal_session(self, customer_id: str, return_url: str) -> Dict[str, Any]:
        """
        Create a Stripe Customer Portal session for managing subscription.
        
        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal session
            
        Returns:
            Portal session or error
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return {
                "success": True,
                "session": session
            }
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Get subscription details.
        
        Args:
            subscription_id: Stripe subscription ID
            
        Returns:
            Subscription object or error
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                "success": True,
                "subscription": subscription
            }
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def cancel_subscription(self, subscription_id: str, 
                           at_period_end: bool = True) -> Dict[str, Any]:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            at_period_end: Cancel at end of billing period (default: True)
            
        Returns:
            Updated subscription or error
        """
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
            
            return {
                "success": True,
                "subscription": subscription
            }
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def construct_webhook_event(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """
        Construct and verify webhook event.
        
        Args:
            payload: Raw request body
            sig_header: Stripe-Signature header
            
        Returns:
            Verified event or error
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return {
                "success": True,
                "event": event
            }
        except ValueError as e:
            return {
                "success": False,
                "error": "Invalid payload"
            }
        except stripe.error.SignatureVerificationError as e:
            return {
                "success": False,
                "error": "Invalid signature"
            }


# Global instance
stripe_client = StripeClient()
