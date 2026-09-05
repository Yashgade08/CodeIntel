"""
SQLAlchemy ORM models for Issue, IssuePrediction, and IssueDuplicatePair.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class Issue(Base):
    """A GitHub issue from an ingested repository."""

    __tablename__ = "issues"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    github_issue_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="open")
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    labels: Mapped[list | None] = mapped_column(JSON, nullable=True)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)

    github_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    github_closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    repository = relationship("Repository", back_populates="issues")
    predictions = relationship(
        "IssuePrediction", back_populates="issue", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Issue #{self.github_issue_number}: {self.title[:50]}>"


class IssuePrediction(Base):
    """ML predictions for a GitHub issue (type classification, severity)."""

    __tablename__ = "issue_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False
    )
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    predicted_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    type_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    severity_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    shap_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    issue = relationship("Issue", back_populates="predictions")

    def __repr__(self) -> str:
        return f"<IssuePrediction type={self.predicted_type} severity={self.predicted_severity}>"


class IssueDuplicatePair(Base):
    """A pair of issues detected as potential duplicates."""

    __tablename__ = "issue_duplicate_pairs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    issue_a_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False
    )
    issue_b_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False
    )
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<IssueDuplicatePair score={self.similarity_score:.2f}>"
