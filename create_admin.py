#!/usr/bin/env python3
"""
Create Admin User Script

Run this once after deploying to create the first admin user.
"""

from src.database import db, init_database
from src.models import User

def create_admin():
    """Create default admin user"""
    print("Initializing database...")
    init_database()
    
    print("Creating admin user...")
    
    with db.get_session() as session:
        # Check if admin already exists
        existing = session.query(User).filter_by(username='admin').first()
        
        if existing:
            print("⚠️  Admin user already exists!")
            print(f"   Username: {existing.username}")
            print(f"   Email: {existing.email}")
            return
        
        # Create new admin
        admin = User(
            username='admin',
            email='admin@example.com',
            password='Admin123!'
        )
        admin.is_admin = True
        session.add(admin)
    
    print("✅ Admin user created successfully!")
    print("")
    print("Login credentials:")
    print("  Username: admin")
    print("  Password: Admin123!")
    print("")
    print("⚠️  IMPORTANT: Change this password after first login!")
    print("")

if __name__ == '__main__':
    create_admin()
