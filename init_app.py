#!/usr/bin/env python3
"""
Application Initialization Script

Runs on first deployment to:
- Initialize database
- Create default admin user
- Set up necessary directories
"""

import os
from src.database import init_database
from src.models import User
from src.utils.logging import setup_logger

logger = setup_logger(__name__)


def initialize_application():
    """Initialize application on first run"""
    
    logger.info("=" * 70)
    logger.info("I FUCKING HATE ACCOUNTS - Application Initialization")
    logger.info("=" * 70)
    
    # Initialize database
    logger.info("Initializing database...")
    try:
        init_database()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # Import db after initialization
    from src.database import db
    
    # Create admin user if doesn't exist
    logger.info("Checking for admin user...")
    try:
        with db.get_session() as session:
            # Check if any admin exists
            admin_exists = session.query(User).filter_by(is_admin=True).first()
            
            if admin_exists:
                logger.info(f"✅ Admin user already exists: {admin_exists.username}")
            else:
                # Get admin credentials from environment or use defaults
                admin_username = os.getenv('ADMIN_USERNAME', 'admin')
                admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
                admin_password = os.getenv('ADMIN_PASSWORD', 'Admin123!')
                
                # Create admin user
                admin = User(
                    username=admin_username,
                    email=admin_email,
                    password=admin_password
                )
                admin.is_admin = True
                session.add(admin)
                
                logger.info("=" * 70)
                logger.info("✅ ADMIN USER CREATED SUCCESSFULLY!")
                logger.info("=" * 70)
                logger.info(f"Username: {admin_username}")
                logger.info(f"Password: {admin_password}")
                logger.info(f"Email:    {admin_email}")
                logger.info("=" * 70)
                logger.info("⚠️  IMPORTANT: Change the admin password after first login!")
                logger.info("=" * 70)
                
                print("\n" + "=" * 70)
                print("🎉 ADMIN USER CREATED!")
                print("=" * 70)
                print(f"Username: {admin_username}")
                print(f"Password: {admin_password}")
                print(f"Email:    {admin_email}")
                print("=" * 70)
                print("⚠️  CHANGE PASSWORD AFTER FIRST LOGIN!")
                print("=" * 70 + "\n")
                
    except Exception as e:
        logger.error(f"❌ Admin user creation failed: {e}")
        raise
    
    logger.info("=" * 70)
    logger.info("✅ Application initialization complete!")
    logger.info("=" * 70)


if __name__ == '__main__':
    initialize_application()
