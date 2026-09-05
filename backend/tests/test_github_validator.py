"""
Unit tests for GitHub URL validator and metadata parser.
"""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationException
from app.ingestion.validator import parse_github_url


def test_parse_valid_github_urls():
    """Test parsing various valid GitHub repository URLs."""
    urls = [
        ("https://github.com/facebook/react", "https://github.com/facebook/react", "facebook", "react"),
        ("https://github.com/fastapi/fastapi.git", "https://github.com/fastapi/fastapi", "fastapi", "fastapi"),
        ("https://www.github.com/golang/go/", "https://github.com/golang/go", "golang", "go"),
        ("http://github.com/python/cpython", "https://github.com/python/cpython", "python", "cpython"),
    ]

    for input_url, expected_norm, expected_owner, expected_repo in urls:
        norm, owner, repo = parse_github_url(input_url)
        assert norm == expected_norm
        assert owner == expected_owner
        assert repo == expected_repo


def test_parse_invalid_github_urls():
    """Test invalid GitHub repository URLs raise ValidationException."""
    invalid_urls = [
        "",
        "not a url",
        "https://gitlab.com/owner/repo",
        "https://github.com/onlyowner",
        "https://github.com/owner/repo/extra/path",
        "ftp://github.com/owner/repo",
    ]

    for url in invalid_urls:
        with pytest.raises(ValidationException):
            parse_github_url(url)
