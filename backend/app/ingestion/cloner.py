"""
Repository Cloner — safely clone GitHub repositories locally.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import IngestionException
from app.core.logging import get_logger

logger = get_logger(__name__)

# Strict validation for branch names to prevent flag injection
BRANCH_REGEX = re.compile(r"^[a-zA-Z0-9_\-\./]+$")


class SafeCloner:
    """Handles shallow, non-executing local git cloning with path validation and option injection guards."""

    def __init__(self, base_storage_dir: str | Path | None = None) -> None:
        settings = get_settings()
        self.base_storage_dir = Path(base_storage_dir or settings.REPO_STORAGE_PATH).resolve()
        self.base_storage_dir.mkdir(parents=True, exist_ok=True)

    def get_repo_dir(self, repository_id: str) -> Path:
        """
        Get and validate target storage path for a repository ID.
        
        Prevents path traversal attacks.
        """
        target_path = (self.base_storage_dir / str(repository_id)).resolve()
        
        # Path traversal guard
        try:
            target_path.relative_to(self.base_storage_dir)
        except ValueError:
            raise IngestionException(
                f"Path traversal detected for repository ID '{repository_id}'."
            )
        return target_path

    async def clone_repository(
        self,
        repository_id: str,
        github_url: str,
        default_branch: str = "main"
    ) -> Path:
        """
        Shallow clone a public git repository into an isolated local directory.
        
        Uses asyncio.create_subprocess_exec without shell execution to prevent command injection,
        and uses '--' argument termination to prevent Option Injection vulnerabilities.
        """
        target_dir = self.get_repo_dir(repository_id)

        # Validate branch name
        if not default_branch or not BRANCH_REGEX.match(default_branch) or default_branch.startswith("-"):
            logger.warning("Unsafe default branch name provided, falling back to 'main'", branch=default_branch)
            default_branch = "main"

        # Clean existing directory if present
        if target_dir.exists():
            logger.info("Removing existing repository directory", target_dir=str(target_dir))
            shutil.rmtree(target_dir, ignore_errors=True)

        logger.info(
            "Cloning repository",
            repo_id=repository_id,
            url=github_url,
            branch=default_branch,
            target_dir=str(target_dir),
        )

        # Command vector — arguments passed as a list, NEVER string evaluated via shell=True.
        # '--' terminates option flags to prevent Option Injection (e.g. -oProxyCommand).
        cmd = [
            "git",
            "clone",
            "--depth", "1",
            "--single-branch",
            "--branch", default_branch,
            "--",
            github_url,
            str(target_dir),
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                stderr_text = stderr.decode("utf-8", errors="replace")
                logger.warning(
                    "Branch-specific git clone failed, falling back to default clone",
                    error=stderr_text,
                )
                
                # Fallback: clone without explicit --branch
                if target_dir.exists():
                    shutil.rmtree(target_dir, ignore_errors=True)

                fallback_cmd = [
                    "git",
                    "clone",
                    "--depth", "1",
                    "--",
                    github_url,
                    str(target_dir),
                ]
                process_fb = await asyncio.create_subprocess_exec(
                    *fallback_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                fb_stdout, fb_stderr = await process_fb.communicate()
                
                if process_fb.returncode != 0:
                    fb_stderr_text = fb_stderr.decode("utf-8", errors="replace")
                    logger.error("Git clone failed completely", error=fb_stderr_text)
                    raise IngestionException(f"Failed to clone repository: {fb_stderr_text}")

            logger.info("Repository cloned successfully", repo_id=repository_id)
            return target_dir

        except Exception as e:
            if not isinstance(e, IngestionException):
                logger.error("Unexpected error during git clone", error=str(e))
                raise IngestionException(f"Git clone operation error: {str(e)}") from e
            raise

    def cleanup(self, repository_id: str) -> None:
        """Safely delete cloned repository files from disk."""
        try:
            target_dir = self.get_repo_dir(repository_id)
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
                logger.info("Cleaned up cloned repository files", repo_id=repository_id)
        except Exception as e:
            logger.warning("Error during directory cleanup", repo_id=repository_id, error=str(e))
