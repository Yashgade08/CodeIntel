"""
POST /api/github/clone

Accepts a GitHub repository URL, validates it, clones the repository
into a unique local workspace directory using Git, verifies the clone,
and returns the repository metadata with the real file count.

No GitHub API calls. No tokens required. No database.
Returns structured success or structured error — never crashes.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/github", tags=["github-clone"])

# Matches: https://github.com/owner/repo (with optional .git suffix or trailing slash)
_GITHUB_REPO_RE = re.compile(
    r"^https?://(?:www\.)?github\.com"
    r"/([a-zA-Z0-9_\-\.]+)"   # owner
    r"/([a-zA-Z0-9_\-\.]+?)"  # repo
    r"(?:\.git)?/?$"
)

# Workspace base directory: backend/workspace/
WORKSPACE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "workspace"


class CloneRequest(BaseModel):
    url: str


def _validate_url(raw_url: str) -> tuple[bool, dict | None, str, str, str]:
    """
    Validate the GitHub URL format.
    Returns: (is_valid, error_dict, owner, repository, canonical_url)
    """
    raw = (raw_url or "").strip()

    # Rule 1: Non-empty
    if not raw:
        return False, {
            "code": "INVALID_GITHUB_URL",
            "layer": "validation",
            "message": "Please provide a GitHub repository URL.",
            "root_cause": "The URL input is empty.",
            "fix": "Enter a valid GitHub URL, e.g. https://github.com/psf/requests",
        }, "", "", ""

    # Rule 2: Parse URL & Scheme
    try:
        parsed = urlparse(raw)
    except Exception:
        return False, {
            "code": "INVALID_GITHUB_URL",
            "layer": "validation",
            "message": "Please provide a valid GitHub repository URL.",
            "root_cause": "The URL could not be parsed.",
            "fix": "Check the URL format. Expected: https://github.com/owner/repository",
        }, "", "", ""

    if parsed.scheme not in ("http", "https"):
        return False, {
            "code": "INVALID_GITHUB_URL",
            "layer": "validation",
            "message": f"URL scheme '{parsed.scheme}' is not supported.",
            "root_cause": f"Scheme '{parsed.scheme}' is not supported. Only http:// and https:// URLs are accepted.",
            "fix": "Use a URL starting with https://",
        }, "", "", ""

    # Rule 3: Host must be github.com
    host = parsed.netloc.lower()
    if host not in ("github.com", "www.github.com"):
        return False, {
            "code": "INVALID_GITHUB_URL",
            "layer": "validation",
            "message": f"'{host}' is not github.com.",
            "root_cause": f"Host '{host}' is not github.com. Only public github.com repositories are supported.",
            "fix": "Ensure the repository URL is hosted on github.com",
        }, "", "", ""

    # Rule 4: Owner and Repository present
    match = _GITHUB_REPO_RE.match(raw)
    if not match:
        return False, {
            "code": "INVALID_GITHUB_URL",
            "layer": "validation",
            "message": "Could not parse owner and repository from the URL.",
            "root_cause": "URL format does not match expected GitHub repository pattern.",
            "fix": "Expected format: https://github.com/owner/repository",
        }, "", "", ""

    owner, repository = match.group(1), match.group(2)

    # Sanitize any accidental .git suffix
    if repository.endswith(".git"):
        repository = repository[:-4]

    # Guard against path traversal characters
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", owner) or not re.match(r"^[a-zA-Z0-9_\-\.]+$", repository):
        return False, {
            "code": "INVALID_GITHUB_URL",
            "layer": "validation",
            "message": "Invalid characters in repository owner or name.",
            "root_cause": "Owner or repository name contains illegal characters.",
            "fix": "Provide a standard GitHub repository URL.",
        }, "", "", ""

    canonical_url = f"https://github.com/{owner}/{repository}"
    return True, None, owner, repository, canonical_url


def _count_repository_files(directory: Path) -> int:
    """Recursively count actual repository files (excluding .git metadata directory)."""
    count = 0
    for root, dirs, files in os.walk(directory):
        if ".git" in dirs:
            dirs.remove(".git")
        count += len(files)
    return count


@router.post("/clone")
def clone_github_repository(body: CloneRequest) -> dict:
    """
    Validate and clone a GitHub repository into a unique local workspace directory.

    Returns:
        success=True  -> { success, repository: {owner, name}, clone: {status, workspace_id, path, file_count} }
        success=False -> { success, error: {code, layer, message, root_cause, fix} }
    """
    # ── Step 1: Validate URL ─────────────────────────────────────────────
    is_valid, err, owner, repository, canonical_url = _validate_url(body.url)
    if not is_valid:
        return {
            "success": False,
            "error": err,
        }

    # ── Step 2: Check Git Availability ───────────────────────────────────
    git_bin = shutil.which("git")
    if not git_bin:
        return {
            "success": False,
            "error": {
                "code": "GIT_NOT_INSTALLED",
                "layer": "git_clone",
                "message": "Git is not installed or not available in the system PATH.",
                "root_cause": "System could not locate the 'git' executable.",
                "fix": "Install Git on the host system and ensure it is in the PATH environment variable.",
            },
        }

    # ── Step 3: Prepare unique workspace directory ───────────────────────
    try:
        WORKSPACE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "FILESYSTEM_ERROR",
                "layer": "workspace_setup",
                "message": "Failed to create base workspace directory.",
                "root_cause": str(e),
                "fix": "Check filesystem permissions for the backend directory.",
            },
        }

    timestamp = int(time.time())
    unique_suffix = uuid.uuid4().hex[:6]
    workspace_id = f"{owner}_{repository}_{timestamp}_{unique_suffix}"
    target_dir = WORKSPACE_BASE_DIR / workspace_id

    # ── Step 4: Clone the repository ─────────────────────────────────────
    cmd = ["git", "clone", "--depth", "1", canonical_url, str(target_dir)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        return {
            "success": False,
            "error": {
                "code": "NETWORK_ERROR",
                "layer": "git_clone",
                "message": "Repository cloning timed out after 120 seconds.",
                "root_cause": "The network connection was too slow or the repository is extremely large.",
                "fix": "Check your internet connection or try again later.",
            },
        }
    except Exception as e:
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        return {
            "success": False,
            "error": {
                "code": "CLONE_FAILED",
                "layer": "git_clone",
                "message": "Repository cloning failed.",
                "root_cause": f"Subprocess execution error: {str(e)}",
                "fix": "Verify that Git is working properly on your system.",
            },
        }

    # ── Step 5: Check clone command exit status ───────────────────────────
    if result.returncode != 0:
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)

        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        combined_err = f"{stderr}\n{stdout}".strip()
        combined_lower = combined_err.lower()

        if (
            "repository not found" in combined_lower
            or "not found" in combined_lower
            or "could not read username" in combined_lower
            or "404" in combined_lower
        ):
            code = "REPOSITORY_NOT_FOUND"
            root_cause = f"GitHub repository does not exist or is private. Git output: {stderr}"
            fix = "Ensure the repository exists, the owner and repository name are spelled correctly, and it is a public repository."
        elif (
            "could not resolve host" in combined_lower
            or "failed to connect" in combined_lower
            or "connection timed out" in combined_lower
            or "unable to access" in combined_lower
        ):
            code = "NETWORK_ERROR"
            root_cause = f"Network connection failed: {stderr}"
            fix = "Check your internet connection and DNS settings."
        elif "permission denied" in combined_lower or "authentication failed" in combined_lower:
            code = "PERMISSION_DENIED"
            root_cause = f"Access denied: {stderr}"
            fix = "Ensure you have access to the repository and that it is public."
        elif "destination path" in combined_lower and "already exists" in combined_lower:
            code = "FILESYSTEM_ERROR"
            root_cause = f"Target workspace collision: {stderr}"
            fix = "Retry cloning to generate a new unique workspace."
        else:
            code = "CLONE_FAILED"
            root_cause = (
                f"Root cause could not be determined automatically. See Git error details: {stderr or stdout}"
            )
            fix = "Check the Git error details above and verify that the repository is accessible."

        return {
            "success": False,
            "error": {
                "code": code,
                "layer": "git_clone",
                "message": "Repository cloning failed.",
                "root_cause": root_cause,
                "fix": fix,
            },
        }

    # ── Step 6: Verify repository directory and count files ──────────────
    if not target_dir.exists() or not target_dir.is_dir():
        return {
            "success": False,
            "error": {
                "code": "FILESYSTEM_ERROR",
                "layer": "verification",
                "message": "Repository workspace directory was not created.",
                "root_cause": f"Expected workspace directory does not exist: {target_dir}",
                "fix": "Check filesystem write permissions in the backend directory.",
            },
        }

    file_count = _count_repository_files(target_dir)

    # ── Step 7: Return Success ───────────────────────────────────────────
    return {
        "success": True,
        "repository": {
            "owner": owner,
            "name": repository,
        },
        "clone": {
            "status": "COMPLETED",
            "workspace_id": workspace_id,
            "path": str(target_dir),
            "file_count": file_count,
        },
    }
