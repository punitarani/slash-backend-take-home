"""db.py"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/postgres")

# Create engine, sessionmaker and base for sqlalchemy
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
