from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

# Engine setup using SQLite as the client-grade base.
# 'check_same_thread': False is only necessary for SQLite.
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args=connect_args
)

# Standard session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()

def get_db():
    """
    Dependency to generate and yield a database session per HTTP request.
    Automatically closes the session after request lifecycle.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
