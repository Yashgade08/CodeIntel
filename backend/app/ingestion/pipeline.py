"""
Ingestion pipeline orchestrator.
"""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import redis_manager
from app.ingestion.cloner import SafeCloner
from app.ingestion.scanner import FileScanner
from app.ingestion.validator import GitHubClient, parse_github_url
from app.services.repository_service import RepositoryService

logger = get_logger(__name__)

# In-memory status fallback cache (used if Redis is offline/unreachable)
STATUS_CACHE: dict[str, dict] = {}


async def set_ingestion_progress(
    repo_id: str,
    status: str,
    progress: float,
    steps_completed: list[str] | None = None,
    error_message: str | None = None,
) -> None:
    """Store real-time ingestion job status and progress in Redis / in-memory cache."""
    data = {
        "repository_id": repo_id,
        "status": status,
        "progress": progress,
        "steps_completed": steps_completed or [],
        "error_message": error_message,
    }
    STATUS_CACHE[repo_id] = data

    try:
        if redis_manager._client:
            redis_key = f"ingestion:status:{repo_id}"
            await redis_manager.client.set(redis_key, json.dumps(data), ex=3600)
    except Exception as e:
        logger.debug("Redis status cache write skipped", error=str(e))


async def get_ingestion_progress(repo_id: str) -> dict:
    """Retrieve real-time ingestion job status from Redis or fallback cache."""
    try:
        if redis_manager._client:
            redis_key = f"ingestion:status:{repo_id}"
            cached = await redis_manager.client.get(redis_key)
            if cached:
                return json.loads(cached)
    except Exception as e:
        logger.debug("Redis status read failed, using memory cache", error=str(e))

    return STATUS_CACHE.get(
        repo_id,
        {
            "repository_id": repo_id,
            "status": "pending",
            "progress": 0.0,
            "steps_completed": [],
            "error_message": None,
        },
    )


class IngestionPipeline:
    """
    Orchestrates the end-to-end repository ingestion process:
    1. URL parsing & GitHub API metadata fetch
    2. Safe shallow git cloning
    3. File tree scanning & filtering
    4. Fetching GitHub issues/PRs
    5. DB record creation (Repository, File, Issue)
    """

    def __init__(
        self,
        db_session_factory=None,
    ) -> None:
        self.db_session_factory = db_session_factory
        self.cloner = SafeCloner()
        self.scanner = FileScanner()
        self.github_client = GitHubClient()

    async def run(self, repository_id: str, github_url: str, db: AsyncSession) -> None:
        """Execute the full ingestion pipeline for a given repository."""
        repo_uuid = UUID(repository_id)
        service = RepositoryService(db)
        steps_completed: list[str] = []

        logger.info("Ingestion pipeline started", repo_id=repository_id, url=github_url)

        try:
            # ── Step 1: Validate URL & Fetch Metadata ─────────────────────
            await set_ingestion_progress(repository_id, "validating", 0.1, steps_completed)
            await service.update_status(repo_uuid, "validating", 0.1)

            normalized_url, owner, repo_name = parse_github_url(github_url)
            meta = await self.github_client.fetch_repository_metadata(owner, repo_name)
            steps_completed.append("github_metadata")

            # ── Step 2: Clone Repository ──────────────────────────────────
            await set_ingestion_progress(repository_id, "cloning", 0.3, steps_completed)
            await service.update_status(repo_uuid, "cloning", 0.3)

            target_dir = await self.cloner.clone_repository(
                repository_id=repository_id,
                github_url=normalized_url,
                default_branch=meta.get("default_branch", "main"),
            )
            steps_completed.append("git_clone")

            # ── Step 3: Scan File Tree & Extract Statistics ──────────────
            await set_ingestion_progress(repository_id, "scanning", 0.6, steps_completed)
            await service.update_status(repo_uuid, "scanning", 0.6)

            scan_result = self.scanner.scan_directory(target_dir)
            steps_completed.append("file_scanning")

            # ── Step 4: Fetch Issues & PRs ────────────────────────────────
            await set_ingestion_progress(repository_id, "fetching_issues", 0.8, steps_completed)
            await service.update_status(repo_uuid, "fetching_issues", 0.8)

            settings = get_settings()
            issues_data = await self.github_client.fetch_issues_and_prs(
                owner=owner,
                repo=repo_name,
                max_issues=settings.GITHUB_MAX_ISSUES,
            )
            steps_completed.append("github_issues")

            # ── Step 5: Save Records to Database ─────────────────────────
            await set_ingestion_progress(repository_id, "storing", 0.9, steps_completed)
            await service.update_status(repo_uuid, "storing", 0.9)

            # Update repository metadata and languages
            await service.update_metadata(
                repo_id=repo_uuid,
                description=meta.get("description"),
                default_branch=meta.get("default_branch", "main"),
                star_count=meta.get("star_count", 0),
                fork_count=meta.get("fork_count", 0),
                open_issues_count=meta.get("open_issues_count", 0),
                topics=meta.get("topics", []),
                languages=scan_result.languages,
            )

            # Save scanned files & issues
            await service.save_files(repo_uuid, scan_result.files)
            if issues_data:
                await service.save_issues(repo_uuid, issues_data)

            steps_completed.append("database_persistence")

            # ── Complete ──────────────────────────────────────────────────
            await service.update_status(repo_uuid, "completed", 1.0)
            await set_ingestion_progress(repository_id, "completed", 1.0, steps_completed)

            logger.info("Ingestion pipeline completed successfully", repo_id=repository_id)

        except Exception as e:
            error_msg = str(e)
            logger.error("Ingestion pipeline failed", repo_id=repository_id, error=error_msg)
            try:
                await service.update_status(repo_uuid, "failed", 0.0)
                await set_ingestion_progress(
                    repository_id, "failed", 0.0, steps_completed, error_message=error_msg
                )
            except Exception as update_err:
                logger.error("Could not update failure status in DB", error=str(update_err))
