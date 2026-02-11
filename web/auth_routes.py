"""
Authentication Routes

Handles login, registration, and logout endpoints.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from src.auth import AuthService, AuthUser
from src.utils.logging import setup_logger

logger = setup_logger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate password confirmation
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')
        
        # Register user
        success, message, user = AuthService.register_user(username, email, password)
        
        if success:
            # Auto-login after registration
            auth_user = AuthUser(user)
            login_user(auth_user, remember=True)
            flash('Registration successful! Welcome!', 'success')
            logger.info(f"User registered and logged in: {username}")
            return redirect(url_for('index'))
        else:
            flash(message, 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        # Authenticate user
        success, message, user = AuthService.authenticate_user(username_or_email, password)
        
        if success:
            auth_user = AuthUser(user)
            login_user(auth_user, remember=bool(remember))
            flash('Login successful!', 'success')
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash(message, 'error')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    user_id = current_user.id
    AuthService.logout_user_and_log(user_id)
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)
