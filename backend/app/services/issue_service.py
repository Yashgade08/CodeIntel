"""
Issue Intelligence Service — orchestrates ML issue classification, severity prediction, and duplicate detection.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.ml.duplicate_detector import DuplicateDetector
from app.ml.issue_classifier import IssueClassifier
from app.ml.severity_predictor import IssueSeverityPredictor
from app.ml.training import DEFAULT_MODELS_DIR, train_issue_models
from app.models.issue import Issue, IssueDuplicatePair, IssuePrediction

logger = get_logger(__name__)


class IssueIntelligenceService:
    """Orchestrates ML-powered issue categorization, severity prediction, and duplicate tracking."""

    def __init__(self, models_dir: Path | None = None) -> None:
        self.models_dir = models_dir or DEFAULT_MODELS_DIR
        self.classifier_path = self.models_dir / "issue_classifier.joblib"
        self.severity_path = self.models_dir / "severity_predictor.joblib"

        self.classifier: IssueClassifier | None = None
        self.severity_predictor: IssueSeverityPredictor | None = None
        self.duplicate_detector = DuplicateDetector()

        self._ensure_models_loaded()

    def _ensure_models_loaded(self) -> None:
        """Load trained models from disk, or train on startup if artifacts do not exist."""
        if not self.classifier_path.exists() or not self.severity_path.exists():
            logger.info("ML model artifacts missing, training baseline models on seed dataset")
            try:
                train_issue_models(self.models_dir)
            except Exception as e:
                logger.warning("Auto-training failed on startup, will use heuristic fallback", error=str(e))

        self.classifier = IssueClassifier(self.classifier_path if self.classifier_path.exists() else None)
        self.severity_predictor = IssueSeverityPredictor(self.severity_path if self.severity_path.exists() else None)

    def analyze(
        self,
        title: str,
        body: str | None = None,
        comment_count: int = 0,
        existing_issues: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze issue text with ML models without requiring database persistence.
        """
        assert self.classifier is not None
        assert self.severity_predictor is not None

        # 1. Type Classification
        issue_type, type_conf = self.classifier.predict(title, body)

        # 2. Severity Prediction
        severity, sev_conf = self.severity_predictor.predict(title, body, comment_count)

        # 3. Duplicate Detection
        duplicates = []
        if existing_issues:
            duplicates = self.duplicate_detector.find_duplicates(
                query_title=title,
                query_body=body,
                existing_issues=existing_issues,
            )

        return {
            "issue_type": issue_type,
            "type_confidence": type_conf,
            "severity": severity,
            "severity_confidence": sev_conf,
            "duplicate_candidates": duplicates,
            "model_version": f"{self.classifier.VERSION};{self.severity_predictor.VERSION}",
            "models_status": {
                "classifier_trained": self.classifier.is_trained,
                "severity_trained": self.severity_predictor.is_trained,
            },
        }

    async def analyze_and_store_issue(
        self,
        issue_id: UUID,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Analyze an existing repository issue in PostgreSQL, persist predictions and duplicates.
        """
        # Fetch target issue
        result = await db.execute(select(Issue).where(Issue.id == issue_id))
        target_issue = result.scalar_one_or_none()
        if not target_issue:
            raise ValueError(f"Issue with ID '{issue_id}' not found.")

        # Fetch other issues in repository for duplicate comparison
        repo_issues_query = await db.execute(
            select(Issue)
            .where(Issue.repository_id == target_issue.repository_id)
            .where(Issue.id != issue_id)
        )
        other_issues = list(repo_issues_query.scalars().all())
        other_dicts = [
            {
                "id": str(iss.id),
                "github_issue_number": iss.github_issue_number,
                "title": iss.title,
                "body": iss.body,
            }
            for iss in other_issues
        ]

        # Run ML inference
        analysis = self.analyze(
            title=target_issue.title,
            body=target_issue.body,
            comment_count=target_issue.comment_count,
            existing_issues=other_dicts,
        )

        # Store prediction record
        prediction = IssuePrediction(
            issue_id=issue_id,
            model_version=analysis["model_version"],
            predicted_type=analysis["issue_type"],
            type_confidence=analysis["type_confidence"],
            predicted_severity=analysis["severity"],
            severity_confidence=analysis["severity_confidence"],
        )
        db.add(prediction)

        # Store duplicate pairs
        for dup in analysis["duplicate_candidates"]:
            dup_pair = IssueDuplicatePair(
                issue_a_id=issue_id,
                issue_b_id=UUID(dup["issue_id"]),
                similarity_score=dup["similarity_score"],
                model_version=self.duplicate_detector.VERSION,
            )
            db.add(dup_pair)

        await db.commit()
        logger.info("Persisted ML predictions for issue", issue_id=str(issue_id))
        return analysis

    async def get_repository_issues(
        self,
        repository_id: UUID,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Issue]:
        """Retrieve repository issues with predictions eagerly loaded."""
        result = await db.execute(
            select(Issue)
            .options(selectinload(Issue.predictions))
            .where(Issue.repository_id == repository_id)
            .order_by(Issue.github_issue_number.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_issue(self, issue_id: UUID, db: AsyncSession) -> Issue | None:
        """Get single issue with predictions eagerly loaded."""
        result = await db.execute(
            select(Issue)
            .options(selectinload(Issue.predictions))
            .where(Issue.id == issue_id)
        )
        return result.scalar_one_or_none()


# Singleton service instance
issue_intelligence_service = IssueIntelligenceService()
