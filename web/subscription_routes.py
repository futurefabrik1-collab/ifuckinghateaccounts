#!/usr/bin/env python3
"""Subscription routes for Stripe billing management."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from src.stripe_client import stripe_client
from src.supabase_client import supabase_client
from src.auth_middleware import get_current_user, get_current_user_id, login_required
import os
from datetime import datetime

# Create blueprint
subscription_bp = Blueprint('subscription', __name__, url_prefix='/subscribe')


@subscription_bp.route('/checkout')
@login_required
def checkout():
    """Subscription checkout page."""
    user = get_current_user()
    user_id = user.get('id')
    user_email = user.get('email')
    
    # Check if user already has a subscription
    existing_sub = supabase_client.select('subscriptions', {'user_id': user_id})
    
    if existing_sub['success'] and existing_sub['data']:
        subscription = existing_sub['data'][0]
        
        # If already active or trialing, redirect to manage page
        if subscription['status'] in ['active', 'trialing']:
            flash('You already have an active subscription', 'info')
            return redirect(url_for('subscription.manage'))
    
    return render_template('subscription/checkout.html', 
                         user_email=user_email,
                         stripe_publishable_key=os.getenv('STRIPE_PUBLISHABLE_KEY'))


@subscription_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create Stripe checkout session."""
    user = get_current_user()
    user_id = user.get('id')
    user_email = user.get('email')
    
    try:
        # Check if user has a Stripe customer ID
        subscription_data = supabase_client.select('subscriptions', {'user_id': user_id})
        
        if subscription_data['success'] and subscription_data['data']:
            customer_id = subscription_data['data'][0]['stripe_customer_id']
        else:
            # Create Stripe customer
            customer_result = stripe_client.create_customer(
                email=user_email,
                metadata={'user_id': user_id}
            )
            
            if not customer_result['success']:
                return jsonify({'error': 'Failed to create customer'}), 400
            
            customer_id = customer_result['customer'].id
            
            # Save customer ID to database
            supabase_client.insert('subscriptions', {
                'user_id': user_id,
                'stripe_customer_id': customer_id,
                'status': 'incomplete',
                'stripe_price_id': os.getenv('STRIPE_PRICE_ID')
            })
        
        # Create checkout session
        success_url = url_for('subscription.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}'
        cancel_url = url_for('subscription.checkout', _external=True)
        
        session_result = stripe_client.create_checkout_session(
            customer_id=customer_id,
            success_url=success_url,
            cancel_url=cancel_url,
            trial_days=14
        )
        
        if session_result['success']:
            return jsonify({'sessionId': session_result['session'].id})
        else:
            return jsonify({'error': session_result.get('error')}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_bp.route('/success')
@login_required
def success():
    """Subscription success page."""
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash('Invalid session', 'error')
        return redirect(url_for('subscription.checkout'))
    
    return render_template('subscription/success.html')


@subscription_bp.route('/cancel')
def cancel():
    """Subscription cancelled page."""
    flash('Subscription checkout cancelled', 'info')
    return redirect(url_for('subscription.checkout'))


@subscription_bp.route('/manage')
@login_required
def manage():
    """Subscription management page."""
    user_id = get_current_user_id()
    
    # Get subscription from database
    result = supabase_client.select('subscriptions', {'user_id': user_id})
    
    if not result['success'] or not result['data']:
        flash('No subscription found', 'error')
        return redirect(url_for('subscription.checkout'))
    
    subscription = result['data'][0]
    
    # Get latest from Stripe
    if subscription.get('stripe_subscription_id'):
        stripe_sub = stripe_client.get_subscription(subscription['stripe_subscription_id'])
        
        if stripe_sub['success']:
            # Update local database with latest info
            stripe_subscription = stripe_sub['subscription']
            
            supabase_client.update('subscriptions', {
                'status': stripe_subscription.status,
                'current_period_start': datetime.fromtimestamp(stripe_subscription.current_period_start).isoformat(),
                'current_period_end': datetime.fromtimestamp(stripe_subscription.current_period_end).isoformat(),
                'cancel_at_period_end': stripe_subscription.cancel_at_period_end
            }, {'user_id': user_id})
            
            # Refresh subscription data
            result = supabase_client.select('subscriptions', {'user_id': user_id})
            subscription = result['data'][0] if result['success'] else subscription
    
    return render_template('subscription/manage.html', subscription=subscription)


@subscription_bp.route('/create-portal-session', methods=['POST'])
@login_required
def create_portal_session():
    """Create Stripe customer portal session."""
    user_id = get_current_user_id()
    
    # Get customer ID
    result = supabase_client.select('subscriptions', {'user_id': user_id})
    
    if not result['success'] or not result['data']:
        return jsonify({'error': 'No subscription found'}), 404
    
    customer_id = result['data'][0]['stripe_customer_id']
    
    # Create portal session
    return_url = url_for('subscription.manage', _external=True)
    portal_result = stripe_client.create_portal_session(customer_id, return_url)
    
    if portal_result['success']:
        return jsonify({'url': portal_result['session'].url})
    else:
        return jsonify({'error': portal_result.get('error')}), 400


@subscription_bp.route('/api/status')
@login_required
def subscription_status():
    """Get subscription status (API endpoint)."""
    user_id = get_current_user_id()
    
    result = supabase_client.select('subscriptions', {'user_id': user_id})
    
    if not result['success'] or not result['data']:
        return jsonify({
            'subscribed': False,
            'status': 'none'
        })
    
    subscription = result['data'][0]
    
    return jsonify({
        'subscribed': subscription['status'] in ['active', 'trialing'],
        'status': subscription['status'],
        'trial_end': subscription.get('trial_end'),
        'current_period_end': subscription.get('current_period_end'),
        'cancel_at_period_end': subscription.get('cancel_at_period_end', False)
    })


# Webhook endpoint (not protected by login)
@subscription_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks."""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    # Verify webhook signature
    event_result = stripe_client.construct_webhook_event(payload, sig_header)
    
    if not event_result['success']:
        return jsonify({'error': event_result.get('error')}), 400
    
    event = event_result['event']
    event_type = event['type']
    
    # Handle different event types
    if event_type == 'checkout.session.completed':
        handle_checkout_completed(event['data']['object'])
    
    elif event_type == 'customer.subscription.created':
        handle_subscription_created(event['data']['object'])
    
    elif event_type == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])
    
    elif event_type == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])
    
    elif event_type == 'invoice.paid':
        handle_invoice_paid(event['data']['object'])
    
    elif event_type == 'invoice.payment_failed':
        handle_payment_failed(event['data']['object'])
    
    return jsonify({'status': 'success'})


def handle_checkout_completed(session):
    """Handle successful checkout session."""
    customer_id = session.get('customer')
    subscription_id = session.get('subscription')
    
    # Find user by customer ID
    result = supabase_client.select('subscriptions', {'stripe_customer_id': customer_id})
    
    if result['success'] and result['data']:
        # Update subscription with subscription ID
        supabase_client.update('subscriptions', {
            'stripe_subscription_id': subscription_id,
            'status': 'trialing'  # Will be updated by subscription.created event
        }, {'stripe_customer_id': customer_id})


def handle_subscription_created(subscription):
    """Handle subscription creation."""
    customer_id = subscription.get('customer')
    subscription_id = subscription.get('id')
    status = subscription.get('status')
    
    current_period_start = datetime.fromtimestamp(subscription.get('current_period_start')).isoformat()
    current_period_end = datetime.fromtimestamp(subscription.get('current_period_end')).isoformat()
    
    trial_end = None
    if subscription.get('trial_end'):
        trial_end = datetime.fromtimestamp(subscription.get('trial_end')).isoformat()
    
    # Update subscription
    supabase_client.update('subscriptions', {
        'stripe_subscription_id': subscription_id,
        'status': status,
        'current_period_start': current_period_start,
        'current_period_end': current_period_end,
        'trial_end': trial_end
    }, {'stripe_customer_id': customer_id})


def handle_subscription_updated(subscription):
    """Handle subscription updates."""
    subscription_id = subscription.get('id')
    status = subscription.get('status')
    cancel_at_period_end = subscription.get('cancel_at_period_end', False)
    
    current_period_end = datetime.fromtimestamp(subscription.get('current_period_end')).isoformat()
    
    # Update subscription
    supabase_client.update('subscriptions', {
        'status': status,
        'current_period_end': current_period_end,
        'cancel_at_period_end': cancel_at_period_end
    }, {'stripe_subscription_id': subscription_id})


def handle_subscription_deleted(subscription):
    """Handle subscription cancellation."""
    subscription_id = subscription.get('id')
    
    # Update subscription status
    supabase_client.update('subscriptions', {
        'status': 'canceled',
        'canceled_at': datetime.utcnow().isoformat()
    }, {'stripe_subscription_id': subscription_id})


def handle_invoice_paid(invoice):
    """Handle successful payment."""
    subscription_id = invoice.get('subscription')
    
    if subscription_id:
        # Update subscription to active (if it was trialing)
        supabase_client.update('subscriptions', {
            'status': 'active'
        }, {'stripe_subscription_id': subscription_id})


def handle_payment_failed(invoice):
    """Handle failed payment."""
    subscription_id = invoice.get('subscription')
    
    if subscription_id:
        # Update subscription status
        supabase_client.update('subscriptions', {
            'status': 'past_due'
        }, {'stripe_subscription_id': subscription_id})
