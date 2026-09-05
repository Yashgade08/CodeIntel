"""
SQLAlchemy ORM models for Dependency and CodeRiskPrediction.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class Dependency(Base):
    """An import/call/inheritance relationship between files."""

    __tablename__ = "dependencies"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    source_file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )
    target_file_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("files.id", ondelete="SET NULL"), nullable=True
    )
    source_symbol: Mapped[str | None] = mapped_column(String(500), nullable=True)
    target_symbol: Mapped[str | None] = mapped_column(String(500), nullable=True)
    dependency_type: Mapped[str] = mapped_column(String(50), nullable=False)  # import, call, inheritance, composition
    target_module: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_external: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Dependency {self.dependency_type}: {self.source_symbol} → {self.target_symbol}>"


class CodeRiskPrediction(Base):
    """ML-generated risk score for a source file."""

    __tablename__ = "code_risk_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_factors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    shap_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<CodeRiskPrediction score={self.risk_score:.2f}>"
