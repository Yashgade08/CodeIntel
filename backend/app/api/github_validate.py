"""
POST /api/github/validate

Accepts a GitHub repository URL, validates it, and extracts owner + repository name.

No GitHub API calls. No database. No tokens required.
Returns structured success or structured error — never crashes.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/github", tags=["github-validate"])

# Matches: https://github.com/owner/repo  (with optional .git suffix or trailing slash)
_GITHUB_REPO_RE = re.compile(
    r"^https?://(?:www\.)?github\.com"
    r"/([a-zA-Z0-9_\-\.]+)"   # owner
    r"/([a-zA-Z0-9_\-\.]+?)"  # repo
    r"(?:\.git)?/?$"
)


class ValidateRequest(BaseModel):
    url: str


@router.post("/validate")
def validate_github_url(body: ValidateRequest) -> dict:
    """
    Validate a GitHub repository URL and extract owner + repository name.

    Rules (in order):
    1. URL must be a non-empty string.
    2. Scheme must be http or https.
    3. Host must be github.com (or www.github.com).
    4. Path must contain both owner and repository segments.

    Returns:
        success=True  → { success, url, owner, repository }
        success=False → { success, error: { code, message } }

    Never raises an unhandled exception.
    """
    raw = (body.url or "").strip()

    # ── Rule 1: non-empty ──────────────────────────────────────────────────
    if not raw:
        return {
            "success": False,
            "error": {
                "code": "INVALID_GITHUB_URL",
                "message": "Please provide a GitHub repository URL.",
            },
        }

    # ── Rule 2: scheme ────────────────────────────────────────────────────
    try:
        parsed = urlparse(raw)
    except Exception:
        return {
            "success": False,
            "error": {
                "code": "INVALID_GITHUB_URL",
                "message": "Please provide a valid GitHub repository URL.",
            },
        }

    if parsed.scheme not in ("http", "https"):
        return {
            "success": False,
            "error": {
                "code": "INVALID_GITHUB_URL",
                "message": (
                    f"URL scheme '{parsed.scheme}' is not supported. "
                    "Only http:// and https:// URLs are accepted."
                ),
            },
        }

    # ── Rule 3: host ──────────────────────────────────────────────────────
    host = parsed.netloc.lower()
    if host not in ("github.com", "www.github.com"):
        return {
            "success": False,
            "error": {
                "code": "INVALID_GITHUB_URL",
                "message": (
                    f"'{host}' is not github.com. "
                    "Only public github.com repositories are supported."
                ),
            },
        }

    # ── Rule 4: owner + repo present ──────────────────────────────────────
    match = _GITHUB_REPO_RE.match(raw)
    if not match:
        return {
            "success": False,
            "error": {
                "code": "INVALID_GITHUB_URL",
                "message": (
                    "Could not parse owner and repository from the URL. "
                    "Expected format: https://github.com/owner/repository"
                ),
            },
        }

    owner, repository = match.group(1), match.group(2)

    # Normalise to canonical HTTPS form (no .git, no trailing slash)
    canonical_url = f"https://github.com/{owner}/{repository}"

    return {
        "success": True,
        "url": canonical_url,
        "owner": owner,
        "repository": repository,
    }
