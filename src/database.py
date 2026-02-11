"""
Database Connection and Session Management

Handles database connection, session creation, and initialization.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from pathlib import Path

from config import Config
from src.models import Base
from src.utils.logging import setup_logger

logger = setup_logger(__name__)


class Database:
    """Database connection manager"""
    
    def __init__(self, database_url: str = None):
        """
        Initialize database connection
        
        Args:
            database_url: SQLAlchemy database URL (uses config if None)
        """
        self.database_url = database_url or self._get_database_url()
        self.engine = None
        self.session_factory = None
        self.Session = None
    
    def _get_database_url(self) -> str:
        """Get database URL from config"""
        # For development, use SQLite
        if Config.DEBUG:
            db_path = Config.BASE_DIR / 'data' / 'receipts.db'
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f'sqlite:///{db_path}'
        
        # For production, use PostgreSQL from environment
        import os
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            raise ValueError("DATABASE_URL environment variable not set for production")
        
        # Fix for Heroku postgres:// -> postgresql://
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        return db_url
    
    def init_db(self):
        """Initialize database connection"""
        logger.info(f"Initializing database: {self.database_url.split('@')[-1]}")  # Don't log credentials
        
        # Create engine
        if self.database_url.startswith('sqlite'):
            # SQLite-specific settings
            self.engine = create_engine(
                self.database_url,
                connect_args={'check_same_thread': False},
                poolclass=StaticPool,
                echo=Config.DEBUG
            )
        else:
            # PostgreSQL settings
            self.engine = create_engine(
                self.database_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                echo=Config.DEBUG
            )
        
        # Create session factory
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
        
        logger.info("Database connection initialized")
    
    def create_tables(self):
        """Create all tables"""
        logger.info("Creating database tables...")
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created")
    
    def drop_tables(self):
        """Drop all tables (USE WITH CAUTION!)"""
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(self.engine)
        logger.info("Database tables dropped")
    
    @contextmanager
    def get_session(self):
        """
        Get a database session with automatic cleanup
        
        Usage:
            with db.get_session() as session:
                user = session.query(User).first()
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def close(self):
        """Close database connection"""
        if self.Session:
            self.Session.remove()
        if self.engine:
            self.engine.dispose()
        logger.info("Database connection closed")


# Global database instance
db = None


def init_database():
    """Initialize database (call on app startup)"""
    global db
    if db is None:
        db = Database()
    db.init_db()
    db.create_tables()
    logger.info("Database initialization complete")


def get_db_session():
    """Get database session for Flask request context"""
    return db.Session()


def close_db_session():
    """Close database session (call after request)"""
    db.Session.remove()
