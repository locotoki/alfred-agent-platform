"""Database models for pgvector integration."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import VECTOR  # type: ignore
from sqlmodel import Field, SQLModel

class DocumentChunk(SQLModel, table=True):
    """Document chunk with embedding vector."""

    __tablename__ = "document_chunks"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: str = Field(sa_column=Column(String, index=True))
    content: str
    embedding: List[float] = Field(sa_column=Column(VECTOR(1536)))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True)),
    )
