"""
FastAPI endpoints for Machine Learning Issue Intelligence.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.ml.training import train_issue_models
from app.models.issue import Issue
from app.schemas import (
    DuplicateCandidate,
    IssueAnalysisRequest,
    IssueAnalysisResponse,
    IssueListResponse,
    IssueResponse,
)
from app.services.issue_service import issue_intelligence_service

logger = get_logger(__name__)

router = APIRouter(tags=["issues"])


@router.post(
    "/issues/analyze",
    response_model=IssueAnalysisResponse,
    summary="Analyze GitHub issue type, severity, and find duplicate candidates using ML",
)
async def analyze_issue(
    payload: IssueAnalysisRequest,
    db: AsyncSession = Depends(get_db_session),
) -> IssueAnalysisResponse:
    """
    Run ML models (TF-IDF + Logistic Regression, Metadata Feature Predictor, Semantic Embeddings)
    to classify type, predict severity, and detect potential duplicate issues.
    """
    if payload.issue_id:
        try:
            analysis = await issue_intelligence_service.analyze_and_store_issue(
                issue_id=payload.issue_id,
                db=db,
            )
        except ValueError as e:
            raise NotFoundException(str(e))
    else:
        analysis = issue_intelligence_service.analyze(
            title=payload.title,
            body=payload.body,
            comment_count=payload.comment_count,
        )

    candidates = [
        DuplicateCandidate(**dup)
        for dup in analysis.get("duplicate_candidates", [])
    ]

    return IssueAnalysisResponse(
        issue_type=analysis["issue_type"],
        type_confidence=analysis["type_confidence"],
        severity=analysis["severity"],
        severity_confidence=analysis["severity_confidence"],
        duplicate_candidates=candidates,
        model_version=analysis["model_version"],
        models_status=analysis.get("models_status", {}),
    )


@router.get(
    "/repositories/{repo_id}/issues",
    response_model=IssueListResponse,
    summary="List all issues for a repository with ML predictions",
)
async def list_repository_issues(
    repo_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> IssueListResponse:
    """Retrieve all ingested GitHub issues for a repository including ML predictions."""
    issues = await issue_intelligence_service.get_repository_issues(
        repository_id=repo_id,
        db=db,
        limit=limit,
        offset=offset,
    )

    total_query = await db.execute(
        select(func.count(Issue.id)).where(Issue.repository_id == repo_id)
    )
    total = total_query.scalar_one()

    return IssueListResponse(
        issues=[IssueResponse.model_validate(iss) for iss in issues],
        total=total,
    )


@router.get(
    "/issues/{issue_id}",
    response_model=IssueResponse,
    summary="Get detailed issue information with ML predictions",
)
async def get_issue(
    issue_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> IssueResponse:
    """Get single issue by ID with its predictions."""
    issue = await issue_intelligence_service.get_issue(issue_id, db)
    if not issue:
        raise NotFoundException(f"Issue with ID '{issue_id}' not found.")

    return IssueResponse.model_validate(issue)


@router.post(
    "/issues/train",
    summary="Train or retrain issue ML models on seed dataset and report metrics",
)
async def train_models() -> dict:
    """Train issue classification and severity prediction models, returning evaluation metrics."""
    results = train_issue_models()
    # Reload models into active service
    issue_intelligence_service._ensure_models_loaded()
    return results
