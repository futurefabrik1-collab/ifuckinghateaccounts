"""
Authentication System

Handles user authentication, registration, and session management.
"""

from flask import session, redirect, url_for, request
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from functools import wraps
from datetime import datetime
import re

from src.models import User, AuditLog
from src.database import db
from src.utils.logging import setup_logger

logger = setup_logger(__name__)


class AuthUser(UserMixin):
    """Flask-Login user wrapper"""
    
    def __init__(self, user_model):
        self.user_model = user_model
    
    def get_id(self):
        return str(self.user_model.id)
    
    @property
    def id(self):
        return self.user_model.id
    
    @property
    def username(self):
        return self.user_model.username
    
    @property
    def email(self):
        return self.user_model.email
    
    @property
    def is_active(self):
        return self.user_model.is_active
    
    @property
    def is_admin(self):
        return self.user_model.is_admin
    
    def get_cipher(self):
        return self.user_model.get_cipher()


# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    with db.get_session() as session:
        user = session.query(User).filter_by(id=int(user_id)).first()
        if user and user.is_active:
            return AuthUser(user)
    return None


class AuthService:
    """Authentication service"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_username(username: str) -> tuple[bool, str]:
        """
        Validate username
        
        Returns:
            (is_valid, error_message)
        """
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        if len(username) > 80:
            return False, "Username must be less than 80 characters"
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Username can only contain letters, numbers, underscore, and dash"
        return True, ""
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """
        Validate password strength
        
        Returns:
            (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if len(password) > 128:
            return False, "Password is too long"
        
        # Check for required character types
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not (has_upper and has_lower and has_digit):
            return False, "Password must contain uppercase, lowercase, and numbers"
        
        return True, ""
    
    @staticmethod
    def register_user(username: str, email: str, password: str) -> tuple[bool, str, User]:
        """
        Register a new user
        
        Returns:
            (success, message, user)
        """
        # Validate inputs
        valid, msg = AuthService.validate_username(username)
        if not valid:
            return False, msg, None
        
        if not AuthService.validate_email(email):
            return False, "Invalid email address", None
        
        valid, msg = AuthService.validate_password(password)
        if not valid:
            return False, msg, None
        
        # Check if user exists
        with db.get_session() as session:
            existing_user = session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing_user:
                if existing_user.username == username:
                    return False, "Username already exists", None
                else:
                    return False, "Email already registered", None
            
            # Create new user
            new_user = User(username=username, email=email, password=password)
            session.add(new_user)
            session.flush()  # Get user ID
            
            # Log registration
            audit = AuditLog(
                user_id=new_user.id,
                action='register',
                resource_type='user',
                resource_id=new_user.id,
                ip_address=request.remote_addr if request else None,
                user_agent=request.user_agent.string if request and request.user_agent else None
            )
            session.add(audit)
            
            logger.info(f"New user registered: {username}")
            
            return True, "Registration successful", new_user
    
    @staticmethod
    def authenticate_user(username_or_email: str, password: str) -> tuple[bool, str, User]:
        """
        Authenticate user
        
        Returns:
            (success, message, user)
        """
        with db.get_session() as session:
            # Find user by username or email
            user = session.query(User).filter(
                (User.username == username_or_email) | (User.email == username_or_email)
            ).first()
            
            if not user:
                logger.warning(f"Login attempt for non-existent user: {username_or_email}")
                return False, "Invalid username or password", None
            
            if not user.is_active:
                logger.warning(f"Login attempt for inactive user: {username_or_email}")
                return False, "Account is inactive", None
            
            if not user.check_password(password):
                logger.warning(f"Failed login attempt for user: {username_or_email}")
                
                # Log failed login
                audit = AuditLog(
                    user_id=user.id,
                    action='login_failed',
                    resource_type='user',
                    resource_id=user.id,
                    ip_address=request.remote_addr if request else None,
                    user_agent=request.user_agent.string if request and request.user_agent else None
                )
                session.add(audit)
                
                return False, "Invalid username or password", None
            
            # Update last login
            user.last_login = datetime.utcnow()
            
            # Log successful login
            audit = AuditLog(
                user_id=user.id,
                action='login_success',
                resource_type='user',
                resource_id=user.id,
                ip_address=request.remote_addr if request else None,
                user_agent=request.user_agent.string if request and request.user_agent else None
            )
            session.add(audit)
            
            logger.info(f"User logged in: {user.username}")
            
            return True, "Login successful", user
    
    @staticmethod
    def logout_user_and_log(user_id: int):
        """Log user logout"""
        with db.get_session() as session:
            audit = AuditLog(
                user_id=user_id,
                action='logout',
                resource_type='user',
                resource_id=user_id,
                ip_address=request.remote_addr if request else None,
                user_agent=request.user_agent.string if request and request.user_agent else None
            )
            session.add(audit)
            
        logout_user()
        logger.info(f"User logged out: {user_id}")


def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            logger.warning(f"Non-admin user {current_user.username} attempted to access admin page")
            return "Access denied", 403
        return f(*args, **kwargs)
    return decorated_function
