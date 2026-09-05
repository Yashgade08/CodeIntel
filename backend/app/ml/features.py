"""
Feature extraction and text preprocessing utilities for GitHub issues ML models.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np


# Keywords indicating urgency and potential high/critical severity
URGENCY_KEYWORDS = {
    "urgent", "critical", "blocker", "broken", "fatal", "crash", "segfault",
    "panic", "exception", "vulnerability", "exploit", "cve", "breach", "leak",
    "data loss", "corruption", "downtime", "outage", "regression",
}

# Keywords indicating questions or documentation
QUESTION_KEYWORDS = {"how", "why", "what", "where", "can I", "is it possible", "help", "tutorial"}
DOCS_KEYWORDS = {"readme", "docs", "documentation", "typo", "guide", "example", "api doc"}


def clean_issue_text(text: str) -> str:
    """Clean and normalize issue text (lowercase, strip markdown code blocks, normalize whitespace)."""
    if not text:
        return ""
    # Strip markdown code blocks
    cleaned = re.sub(r"```[\s\S]*?```", " [CODE_BLOCK] ", text)
    # Strip inline code
    cleaned = re.sub(r"`[^`]+`", " [CODE] ", cleaned)
    # Strip URLs
    cleaned = re.sub(r"https?://\S+", " [URL] ", cleaned)
    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.lower()


def extract_issue_metadata_features(
    title: str,
    body: str | None = None,
    comment_count: int = 0,
    labels: list[str] | None = None,
) -> np.ndarray:
    """
    Extract numerical metadata features for severity and type classification:
    - title length
    - body length
    - has code block
    - has error/stack trace
    - urgency keyword count
    - comment count
    - has question mark
    """
    body_text = body or ""
    full_text = f"{title} {body_text}".lower()

    title_len = len(title.split())
    body_len = len(body_text.split())
    has_code_block = 1.0 if "```" in body_text else 0.0
    has_traceback = 1.0 if any(term in full_text for term in ["traceback", "stack trace", "error:", "exception:"]) else 0.0
    urgency_count = sum(1.0 for kw in URGENCY_KEYWORDS if kw in full_text)
    has_question = 1.0 if "?" in title else 0.0
    comments = float(comment_count)

    return np.array([
        title_len,
        body_len,
        has_code_block,
        has_traceback,
        urgency_count,
        has_question,
        comments,
    ], dtype=np.float32)
