"""
FastAPI endpoints for repository ingestion and management.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import get_logger
from app.ingestion.pipeline import IngestionPipeline, get_ingestion_progress
from app.ingestion.validator import parse_github_url
from app.models.database import sessionmanager
from app.models.file import File
from app.models.repository import Repository
from app.schemas import (
    IngestionStatusResponse,
    RepositoryCreate,
    RepositoryDetailResponse,
    RepositoryListResponse,
    RepositoryResponse,
)
from app.services.repository_service import RepositoryService

logger = get_logger(__name__)

router = APIRouter(prefix="/repositories", tags=["repositories"])


async def run_background_ingestion(repository_id: str, github_url: str) -> None:
    """Async background task runner for the repository ingestion pipeline."""
    pipeline = IngestionPipeline()
    try:
        async with sessionmanager.session() as db:
            await pipeline.run(repository_id, github_url, db)
    except Exception as e:
        logger.error("Background ingestion runner failed", repo_id=repository_id, error=str(e))


@router.post(
    "",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new GitHub repository",
)
async def create_repository(
    payload: RepositoryCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
) -> RepositoryResponse:
    """
    Validate a public GitHub URL, register the repository, and start asynchronous ingestion.
    """
    normalized_url, owner, repo_name = parse_github_url(payload.github_url)

    service = RepositoryService(db)
    repo = await service.create_repository(
        github_url=normalized_url,
        owner=owner,
        name=repo_name,
    )

    # Schedule background ingestion pipeline
    background_tasks.add_task(
        run_background_ingestion,
        repository_id=str(repo.id),
        github_url=normalized_url,
    )

    return RepositoryResponse.model_validate(repo)


@router.get(
    "",
    response_model=RepositoryListResponse,
    summary="List all ingested repositories",
)
async def list_repositories(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> RepositoryListResponse:
    """Retrieve paginated list of ingested repositories."""
    service = RepositoryService(db)
    repos = await service.list_repositories(limit=limit, offset=offset)
    
    total_query = await db.execute(select(func.count(Repository.id)))
    total = total_query.scalar_one()

    return RepositoryListResponse(
        repositories=[RepositoryResponse.model_validate(r) for r in repos],
        total=total,
    )


@router.get(
    "/{repo_id}",
    response_model=RepositoryDetailResponse,
    summary="Get detailed repository metadata and file statistics",
)
async def get_repository(
    repo_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> RepositoryDetailResponse:
    """Get detailed metadata, file count, and storage size for a repository."""
    service = RepositoryService(db)
    repo = await service.get_repository(repo_id)
    if not repo:
        raise NotFoundException(f"Repository with ID '{repo_id}' not found.")

    # Calculate file statistics from DB
    stats_query = await db.execute(
        select(
            func.count(File.id).label("total_files"),
            func.coalesce(func.sum(File.size_bytes), 0).label("total_size_bytes"),
        ).where(File.repository_id == repo_id)
    )
    stats = stats_query.one()

    # Locate readme path if present
    readme_query = await db.execute(
        select(File.path)
        .where(File.repository_id == repo_id)
        .where(File.path.ilike("%readme%"))
        .limit(1)
    )
    readme_path = readme_query.scalar_one_or_none()

    repo_dict = RepositoryResponse.model_validate(repo).model_dump()
    repo_dict.update({
        "total_files": stats.total_files,
        "total_size_bytes": stats.total_size_bytes,
        "readme_path": readme_path,
    })

    return RepositoryDetailResponse(**repo_dict)


@router.post(
    "/{repo_id}/ingest",
    response_model=IngestionStatusResponse,
    summary="Trigger/Re-trigger ingestion process for a repository",
)
async def trigger_ingestion(
    repo_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
) -> IngestionStatusResponse:
    """Trigger or re-trigger the ingestion job asynchronously."""
    service = RepositoryService(db)
    repo = await service.get_repository(repo_id)
    if not repo:
        raise NotFoundException(f"Repository with ID '{repo_id}' not found.")

    # Reset status
    await service.update_status(repo_id, "pending", 0.0)

    # Schedule task
    background_tasks.add_task(
        run_background_ingestion,
        repository_id=str(repo.id),
        github_url=repo.github_url,
    )

    return IngestionStatusResponse(
        repository_id=repo_id,
        status="pending",
        progress=0.0,
        steps_completed=[],
        error_message=None,
    )


@router.get(
    "/{repo_id}/ingestion-status",
    response_model=IngestionStatusResponse,
    summary="Get real-time ingestion job status",
)
async def get_status(
    repo_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> IngestionStatusResponse:
    """Poll real-time ingestion status, progress, and completed steps."""
    service = RepositoryService(db)
    repo = await service.get_repository(repo_id)
    if not repo:
        raise NotFoundException(f"Repository with ID '{repo_id}' not found.")

    # Check real-time progress cache
    status_data = await get_ingestion_progress(str(repo_id))

    return IngestionStatusResponse(
        repository_id=repo_id,
        status=status_data.get("status", repo.ingestion_status),
        progress=status_data.get("progress", repo.ingestion_progress),
        steps_completed=status_data.get("steps_completed", []),
        error_message=status_data.get("error_message"),
    )
