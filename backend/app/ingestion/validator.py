"""
GitHub URL validator and GitHub API metadata extractor.

Enforces SSRF prevention, protocol checks, and strict owner/repo sanitization.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.exceptions import ValidationException
from app.core.logging import get_logger

logger = get_logger(__name__)

# Regular expression to validate GitHub repository URLs
# Matches: https://github.com/owner/repo or http://github.com/owner/repo (.git optional)
GITHUB_URL_REGEX = re.compile(
    r"^https?://(?:www\.)?github\.com/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+?)(?:\.git)?/?$"
)


def parse_github_url(url: str) -> tuple[str, str, str]:
    """
    Validate and parse a GitHub URL into (normalized_url, owner, repo_name).
    
    Normalizes HTTP URLs to HTTPS and enforces github.com domain to prevent SSRF or malformed host attacks.
    Raises ValidationException if the URL is invalid or unsafe.
    """
    if not url or not isinstance(url, str):
        raise ValidationException("Invalid GitHub repository URL: Must be a non-empty string.")

    cleaned_url = url.strip()

    # SSRF & protocol check: reject unsupported protocols or IP addresses
    parsed = urlparse(cleaned_url)
    if parsed.scheme not in ("http", "https"):
        raise ValidationException(f"Invalid GitHub repository URL: Unsupported protocol '{parsed.scheme}'. Only HTTP/HTTPS URLs are supported.")

    if parsed.netloc.lower() not in ("github.com", "www.github.com"):
        raise ValidationException(f"Invalid GitHub repository URL: Host '{parsed.netloc}' is not allowed. Only public github.com repositories are supported.")

    match = GITHUB_URL_REGEX.match(cleaned_url)
    if not match:
        raise ValidationException(
            f"Invalid GitHub repository URL format: '{cleaned_url}'. "
            "Expected format: https://github.com/owner/repository"
        )

    owner, repo = match.group(1), match.group(2)
    if not owner or not repo or owner.startswith(".") or repo.startswith(".") or ".." in owner or ".." in repo:
        raise ValidationException("Invalid GitHub repository URL: Could not extract valid owner and repository name from URL.")

    # Always normalize to HTTPS
    normalized_url = f"https://github.com/{owner}/{repo}"
    return normalized_url, owner, repo


class GitHubClient:
    """Async client for interacting with the GitHub REST API."""

    def __init__(self, token: str | None = None, api_base: str | None = None) -> None:
        settings = get_settings()
        self.token = token or settings.GITHUB_TOKEN
        self.api_base = (api_base or settings.GITHUB_API_BASE).rstrip("/")

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CodeIntel-Copilot/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    async def fetch_repository_metadata(self, owner: str, repo: str) -> dict[str, Any]:
        """
        Fetch repository metadata from GitHub API.
        
        Returns a dict containing owner, name, description, stars, forks, open issues count, default_branch, topics.
        """
        url = f"{self.api_base}/repos/{owner}/{repo}"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code == 404:
                    raise ValidationException(f"GitHub repository '{owner}/{repo}' not found (404).")
                elif response.status_code == 403:
                    logger.warning("GitHub API rate limit hit or forbidden", status=response.status_code)
                    raise ValidationException("GitHub API access forbidden or rate limit exceeded.")
                response.raise_for_status()
                data = response.json()

                return {
                    "owner": data.get("owner", {}).get("login", owner),
                    "name": data.get("name", repo),
                    "description": data.get("description"),
                    "default_branch": data.get("default_branch", "main"),
                    "star_count": data.get("stargazers_count", 0),
                    "fork_count": data.get("forks_count", 0),
                    "open_issues_count": data.get("open_issues_count", 0),
                    "topics": data.get("topics", []),
                    "languages_url": data.get("languages_url"),
                }
            except httpx.HTTPStatusError as e:
                logger.error("GitHub API request failed", error=str(e), status_code=e.response.status_code)
                raise ValidationException(f"Failed to fetch metadata from GitHub: {e.response.text}")
            except httpx.RequestError as e:
                logger.warning("Network issue connecting to GitHub API, using basic metadata", error=str(e))
                return {
                    "owner": owner,
                    "name": repo,
                    "description": None,
                    "default_branch": "main",
                    "star_count": 0,
                    "fork_count": 0,
                    "open_issues_count": 0,
                    "topics": [],
                    "languages_url": None,
                }

    async def fetch_issues_and_prs(
        self, owner: str, repo: str, max_issues: int = 100
    ) -> list[dict[str, Any]]:
        """
        Fetch public issues and pull requests from GitHub API.
        
        Distinguishes issues from PRs based on the 'pull_request' key in the GitHub response.
        """
        url = f"{self.api_base}/repos/{owner}/{repo}/issues"
        params = {"state": "all", "per_page": min(max_issues, 100)}
        headers = self._get_headers()

        issues: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    logger.warning("Could not fetch issues from GitHub API", status=response.status_code)
                    return []
                
                raw_data = response.json()
                for item in raw_data:
                    is_pr = "pull_request" in item
                    issues.append({
                        "github_issue_number": item.get("number"),
                        "title": item.get("title", ""),
                        "body": item.get("body"),
                        "state": item.get("state", "open"),
                        "is_pull_request": is_pr,
                        "author": item.get("user", {}).get("login") if item.get("user") else None,
                        "labels": [label.get("name") for label in item.get("labels", []) if isinstance(label, dict)],
                        "comment_count": item.get("comments", 0),
                        "github_created_at": item.get("created_at"),
                        "github_closed_at": item.get("closed_at"),
                    })
            except Exception as e:
                logger.warning("Error fetching issues from GitHub API", error=str(e))

        return issues
