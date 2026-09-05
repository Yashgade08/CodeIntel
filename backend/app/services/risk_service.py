"""
Service layer for Code Risk Intelligence.
Orchestrates feature extraction, Random Forest prediction, SHAP explanation,
and repository dashboard risk aggregation.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.ml.risk.explainer import CodeRiskExplainer
from app.ml.risk.features import CodeFeatures, extract_code_features
from app.ml.risk.model import CodeRiskModel
from app.models.file import CodeChunk, File
from app.models.issue import Issue
from app.models.repository import Repository
from app.schemas import (
    FileRiskAssessment,
    FileRiskListResponse,
    RepositoryRiskSummary,
    RiskFactor,
)

logger = get_logger(__name__)


class RiskService:
    """Service handling code risk analysis, explainability, and repository dashboards."""

    def __init__(
        self,
        risk_model: CodeRiskModel | None = None,
        explainer: CodeRiskExplainer | None = None,
    ) -> None:
        self.model = risk_model or CodeRiskModel()
        self.explainer = explainer or CodeRiskExplainer(self.model)

    def analyze_source_code(
        self,
        file_path: str,
        content: str,
        repo_root: Path | None = None,
        churn: int | None = None,
        commit_frequency: int | None = None,
        contributors: int | None = None,
        historical_issues: int = 0,
    ) -> FileRiskAssessment:
        """
        Analyze code risk for a file given its content and optional historical parameters.
        Returns risk_score (0-100), risk_level (LOW, MEDIUM, HIGH), and SHAP top_factors.
        """
        features = extract_code_features(
            file_path=file_path,
            content=content,
            repo_root=repo_root,
            churn=churn,
            commit_frequency=commit_frequency,
            contributors=contributors,
            historical_issues=historical_issues,
        )

        risk_score, risk_level = self.model.predict(features)
        raw_factors = self.explainer.explain(features, top_n=4)

        top_factors = [
            RiskFactor(
                factor=f["factor"],
                value=f["value"],
                shap_value=f["shap_value"],
                impact=f["impact"],
                description=f["description"],
            )
            for f in raw_factors
        ]

        return FileRiskAssessment(
            file=file_path,
            risk_score=risk_score,
            risk_level=risk_level,
            top_factors=top_factors,
            features=features.to_dict(),
            model_version=self.model.VERSION,
        )

    async def analyze_file_record(
        self,
        file_record: File,
        db: AsyncSession,
    ) -> FileRiskAssessment:
        """Analyze code risk for an existing File database record."""
        # Count historical issues referencing this file
        issues_count = 0
        try:
            issue_query = await db.execute(
                select(func.count(Issue.id))
                .where(Issue.repository_id == file_record.repository_id)
                .where(Issue.body.ilike(f"%{file_record.filename}%"))
            )
            issues_count = issue_query.scalar_one() or 0
        except Exception:
            pass

        # Try to gather content from chunks if stored
        content = ""
        chunks_query = await db.execute(
            select(CodeChunk.content)
            .where(CodeChunk.file_id == file_record.id)
            .order_by(CodeChunk.start_line)
        )
        chunk_texts = chunks_query.scalars().all()
        if chunk_texts:
            content = "\n".join(chunk_texts)
        elif file_record.line_count:
            # Synthetic placeholder if raw code was not indexed in chunks
            content = "\n" * file_record.line_count

        return self.analyze_source_code(
            file_path=file_record.path,
            content=content,
            churn=file_record.metadata_.get("churn") if file_record.metadata_ else None,
            commit_frequency=file_record.metadata_.get("commit_frequency") if file_record.metadata_ else None,
            contributors=file_record.metadata_.get("contributors") if file_record.metadata_ else None,
            historical_issues=issues_count,
        )

    async def get_repository_risk_summary(
        self,
        repository_id: uuid.UUID,
        db: AsyncSession,
    ) -> RepositoryRiskSummary:
        """Generate repository-wide code risk dashboard summary."""
        repo = await db.get(Repository, repository_id)
        if not repo:
            raise NotFoundException(f"Repository '{repository_id}' not found.")

        # Query all files
        files_query = await db.execute(
            select(File).where(File.repository_id == repository_id)
        )
        files = files_query.scalars().all()

        if not files:
            return RepositoryRiskSummary(
                repository_id=repository_id,
                average_risk_score=0.0,
                risk_distribution={"LOW": 0, "MEDIUM": 0, "HIGH": 0},
                total_files_analyzed=0,
                high_risk_files_count=0,
                medium_risk_files_count=0,
                low_risk_files_count=0,
                top_riskiest_files=[],
            )

        assessments: list[FileRiskAssessment] = []
        for file in files:
            # Check cached assessment in file metadata
            if file.metadata_ and "risk_assessment" in file.metadata_:
                cached = file.metadata_["risk_assessment"]
                assessments.append(FileRiskAssessment(**cached))
            else:
                assessment = await self.analyze_file_record(file, db)
                assessments.append(assessment)

        # Compute distributions and aggregates
        scores = [a.risk_score for a in assessments]
        avg_score = round(float(sum(scores) / len(scores)), 1) if scores else 0.0

        dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for a in assessments:
            dist[a.risk_level] = dist.get(a.risk_level, 0) + 1

        # Sort top riskiest files
        assessments.sort(key=lambda a: a.risk_score, reverse=True)
        top_riskiest = assessments[:10]

        return RepositoryRiskSummary(
            repository_id=repository_id,
            average_risk_score=avg_score,
            risk_distribution=dist,
            total_files_analyzed=len(assessments),
            high_risk_files_count=dist.get("HIGH", 0),
            medium_risk_files_count=dist.get("MEDIUM", 0),
            low_risk_files_count=dist.get("LOW", 0),
            top_riskiest_files=top_riskiest,
        )

    async def list_repository_files_risk(
        self,
        repository_id: uuid.UUID,
        db: AsyncSession,
        risk_level: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> FileRiskListResponse:
        """List paginated file risk assessments for a repository."""
        summary = await self.get_repository_risk_summary(repository_id, db)
        files = summary.top_riskiest_files

        # Query all files if pagination extends beyond top 10
        files_query = await db.execute(
            select(File).where(File.repository_id == repository_id)
        )
        all_db_files = files_query.scalars().all()

        all_assessments: list[FileRiskAssessment] = []
        for file in all_db_files:
            if file.metadata_ and "risk_assessment" in file.metadata_:
                all_assessments.append(FileRiskAssessment(**file.metadata_["risk_assessment"]))
            else:
                all_assessments.append(await self.analyze_file_record(file, db))

        if risk_level:
            all_assessments = [a for a in all_assessments if a.risk_level.upper() == risk_level.upper()]

        all_assessments.sort(key=lambda a: a.risk_score, reverse=True)
        paginated = all_assessments[offset : offset + limit]

        return FileRiskListResponse(
            repository_id=repository_id,
            files=paginated,
            total=len(all_assessments),
        )
