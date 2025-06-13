"""Database session management."""

import os

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://alfred:alfred@localhost:5432/alfred")
engine = create_engine(DATABASE_URL, echo=False)

def init_db() -> None:
    """Initialize database and create all tables."""
    from agent_core.db import models  # noqa: F401
    SQLModel.metadata.create_all(engine)

def get_session() -> Session:
    """Get a new database session."""
    return Session(engine)
