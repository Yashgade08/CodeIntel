"""
Repository service — orchestrates database CRUD operations for repositories, files, and issues.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.ingestion.scanner import ScannedFile
from app.models.file import File
from app.models.issue import Issue
from app.models.repository import Repository

logger = get_logger(__name__)


class RepositoryService:
    """Handles repository CRUD operations, metadata updating, and child record persistence."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_repositories(self, limit: int = 50, offset: int = 0) -> list[Repository]:
        """List all ingested repositories ordered by creation date."""
        result = await self._db.execute(
            select(Repository)
            .order_by(Repository.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_repository(self, repo_id: UUID) -> Repository | None:
        """Get a single repository by ID."""
        result = await self._db.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        return result.scalar_one_or_none()

    async def get_by_url(self, github_url: str) -> Repository | None:
        """Look up a repository by its GitHub URL."""
        result = await self._db.execute(
            select(Repository).where(Repository.github_url == github_url)
        )
        return result.scalar_one_or_none()

    async def create_repository(
        self, github_url: str, owner: str, name: str
    ) -> Repository:
        """Create a new repository record with status 'pending'."""
        existing = await self.get_by_url(github_url)
        if existing:
            return existing

        repo = Repository(
            github_url=github_url,
            owner=owner,
            name=name,
            ingestion_status="pending",
            ingestion_progress=0.0,
        )
        self._db.add(repo)
        await self._db.flush()
        await self._db.commit()
        logger.info("Repository record created", repo_id=str(repo.id), owner=owner, name=name)
        return repo

    async def update_status(
        self,
        repo_id: UUID,
        status: str,
        progress: float,
    ) -> Repository | None:
        """Update ingestion status and progress for a repository."""
        repo = await self.get_repository(repo_id)
        if not repo:
            return None

        repo.ingestion_status = status
        repo.ingestion_progress = progress
        if status == "completed":
            repo.ingested_at = datetime.now(timezone.utc)

        self._db.add(repo)
        await self._db.commit()
        await self._db.refresh(repo)
        logger.info("Repository status updated", repo_id=str(repo_id), status=status, progress=progress)
        return repo

    async def update_metadata(
        self,
        repo_id: UUID,
        description: str | None = None,
        default_branch: str = "main",
        star_count: int = 0,
        fork_count: int = 0,
        open_issues_count: int = 0,
        topics: list[str] | None = None,
        languages: dict | None = None,
    ) -> Repository | None:
        """Update GitHub metadata fields on the Repository model."""
        repo = await self.get_repository(repo_id)
        if not repo:
            return None

        if description is not None:
            repo.description = description
        repo.default_branch = default_branch
        repo.star_count = star_count
        repo.fork_count = fork_count
        repo.open_issues_count = open_issues_count
        repo.topics = topics or []
        repo.languages = languages or {}

        self._db.add(repo)
        await self._db.commit()
        await self._db.refresh(repo)
        return repo

    async def save_files(self, repo_id: UUID, files: list[ScannedFile]) -> int:
        """Clear existing files and bulk insert scanned files for a repository."""
        # Delete previous file records if re-ingesting
        await self._db.execute(
            delete(File).where(File.repository_id == repo_id)
        )

        file_objects = [
            File(
                repository_id=repo_id,
                path=f.relative_path,
                filename=f.filename,
                extension=f.extension,
                language=f.language,
                size_bytes=f.size_bytes,
                line_count=f.line_count,
                sha256_hash=f.sha256_hash,
                metadata_={
                    "is_readme": f.is_readme,
                    "is_documentation": f.is_documentation,
                },
            )
            for f in files
        ]

        self._db.add_all(file_objects)
        await self._db.commit()
        logger.info("Saved scanned files to database", repo_id=str(repo_id), count=len(file_objects))
        return len(file_objects)

    async def save_issues(self, repo_id: UUID, issues_data: list[dict]) -> int:
        """Clear existing issues and insert fetched GitHub issues for a repository."""
        await self._db.execute(
            delete(Issue).where(Issue.repository_id == repo_id)
        )

        issue_objects = []
        for item in issues_data:
            if not item.get("github_issue_number"):
                continue
            issue_objects.append(
                Issue(
                    repository_id=repo_id,
                    github_issue_number=item["github_issue_number"],
                    title=item["title"],
                    body=item.get("body"),
                    state=item.get("state", "open"),
                    author=item.get("author"),
                    labels=item.get("labels", []),
                    comment_count=item.get("comment_count", 0),
                )
            )

        if issue_objects:
            self._db.add_all(issue_objects)
            await self._db.commit()

        logger.info("Saved GitHub issues to database", repo_id=str(repo_id), count=len(issue_objects))
        return len(issue_objects)

    async def delete_repository(self, repo_id: UUID) -> bool:
        """Delete a repository and all associated child records."""
        repo = await self.get_repository(repo_id)
        if repo is None:
            return False
        await self._db.delete(repo)
        await self._db.commit()
        logger.info("Repository deleted from database", repo_id=str(repo_id))
        return True
