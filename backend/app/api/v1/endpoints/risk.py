"""
FastAPI endpoints for Code Risk Intelligence.
Exposes file risk analysis, SHAP top factors, and repository risk dashboards.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.exceptions import NotFoundException
from app.models.file import File
from app.schemas import (
    FileRiskAnalyzeRequest,
    FileRiskAssessment,
    FileRiskListResponse,
    RepositoryRiskSummary,
)
from app.services.risk_service import RiskService

router = APIRouter(tags=["code-risk"])


@router.post(
    "/risk/analyze",
    response_model=FileRiskAssessment,
    status_code=status.HTTP_200_OK,
    summary="Analyze code/maintenance risk for a source file",
)
async def analyze_file_risk(
    payload: FileRiskAnalyzeRequest,
    db: AsyncSession = Depends(get_db_session),
) -> FileRiskAssessment:
    """
    Evaluate structural complexity, AST metrics, churn, and SHAP top risk factors.
    Clearly indicates code/maintenance risk without asserting security vulnerabilities.
    """
    service = RiskService()

    # If file_id is provided, analyze the database record
    if payload.file_id:
        file_rec = await db.get(File, payload.file_id)
        if not file_rec:
            raise NotFoundException(f"File with ID '{payload.file_id}' not found.")
        return await service.analyze_file_record(file_rec, db)

    # Analyze direct content or path
    content = payload.content or ""
    return service.analyze_source_code(
        file_path=payload.file_path,
        content=content,
        churn=payload.churn,
        commit_frequency=payload.commit_frequency,
        contributors=payload.contributors,
    )


@router.get(
    "/repositories/{repo_id}/risk",
    response_model=RepositoryRiskSummary,
    summary="Get repository code risk dashboard summary",
)
async def get_repository_risk(
    repo_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> RepositoryRiskSummary:
    """
    Retrieve repository-wide code risk metrics, average score, risk distribution,
    and top riskiest files with their SHAP maintenance factors.
    """
    service = RiskService()
    return await service.get_repository_risk_summary(repo_id, db)


@router.get(
    "/repositories/{repo_id}/risk/files",
    response_model=FileRiskListResponse,
    summary="List paginated file risk assessments for a repository",
)
async def list_repository_files_risk(
    repo_id: UUID,
    risk_level: str | None = Query(None, description="Filter by level: LOW, MEDIUM, HIGH"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> FileRiskListResponse:
    """Paginated list of files with their risk score, risk level, and top factors."""
    service = RiskService()
    return await service.list_repository_files_risk(
        repository_id=repo_id,
        db=db,
        risk_level=risk_level,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/repositories/{repo_id}/files/{file_id}/risk",
    response_model=FileRiskAssessment,
    summary="Get code risk assessment for a specific file",
)
async def get_file_risk(
    repo_id: UUID,
    file_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> FileRiskAssessment:
    """Retrieve or compute risk score and SHAP factors for a specific file in a repository."""
    service = RiskService()
    file_rec = await db.get(File, file_id)
    if not file_rec or file_rec.repository_id != repo_id:
        raise NotFoundException(f"File '{file_id}' not found in repository '{repo_id}'.")

    return await service.analyze_file_record(file_rec, db)
