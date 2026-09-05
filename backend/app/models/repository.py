"""
SQLAlchemy ORM model for the Repository table.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class Repository(Base):
    """A GitHub repository that has been ingested."""

    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    github_url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    languages: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    topics: Mapped[list | None] = mapped_column(JSON, nullable=True)
    star_count: Mapped[int] = mapped_column(Integer, default=0)
    fork_count: Mapped[int] = mapped_column(Integer, default=0)
    open_issues_count: Mapped[int] = mapped_column(Integer, default=0)

    # Ingestion state
    ingestion_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )
    ingestion_progress: Mapped[float] = mapped_column(Float, default=0.0)
    last_commit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    files = relationship("File", back_populates="repository", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="repository", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Repository {self.owner}/{self.name}>"
