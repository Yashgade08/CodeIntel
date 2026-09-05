"""
POST /api/github/repositories/{repository_id}/bugs/analyze

Runs AI-powered Code Review & Bug Detection using ChromaDB RAG,
multi-provider LLM analysis, and strict evidence validation.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.bug_detection.engine import get_bug_engine

router = APIRouter(prefix="/api/github", tags=["github-bugs"])

WORKSPACE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "workspace"


class BugAnalysisRequest(BaseModel):
    query: str = "Find potential bugs, logic errors, and security vulnerabilities in this repository"
    top_k: int | None = None


@router.post("/repositories/{repository_id}/bugs/analyze")
def analyze_repository_bugs(
    repository_id: str,
    body: BugAnalysisRequest,
) -> dict:
    """
    Analyzes repository code chunks for potential bugs using RAG + LLM.
    """
    clean_id = (repository_id or "").strip()
    if not clean_id or not re.match(r"^[a-zA-Z0-9_\-\.]+$", clean_id) or ".." in clean_id:
        return {
            "success": False,
            "error": {
                "code": "INVALID_REPOSITORY_ID",
                "layer": "bug_detection",
                "message": "Invalid repository workspace identifier.",
                "root_cause": f"Repository identifier '{clean_id}' contains illegal characters or path traversal elements.",
                "fix": "Provide a valid repository identifier returned from the clone operation.",
            },
        }

    resolved_base = WORKSPACE_BASE_DIR.resolve()
    target_dir = (resolved_base / clean_id).resolve()

    if target_dir.parent != resolved_base:
        return {
            "success": False,
            "error": {
                "code": "INVALID_REPOSITORY_ID",
                "layer": "bug_detection",
                "message": "Path traversal attempt detected.",
                "root_cause": "The requested repository path escapes the designated workspace directory.",
                "fix": "Only access repositories managed inside the application workspace.",
            },
        }

    if not target_dir.exists() or not target_dir.is_dir():
        return {
            "success": False,
            "error": {
                "code": "REPOSITORY_NOT_FOUND",
                "layer": "bug_detection",
                "message": f"Cloned repository directory '{clean_id}' does not exist.",
                "root_cause": f"No cloned directory exists at workspace path: {target_dir}",
                "fix": "Ensure the repository has been cloned and indexed before analyzing bugs.",
            },
        }

    try:
        engine = get_bug_engine()
        result = engine.analyze_repository_bugs(
            repository_id=clean_id,
            repo_directory=target_dir,
            query=body.query,
            top_k=body.top_k,
        )
        return result
    except ValueError as ve:
        err_msg = str(ve)
        code = "LLM_INVALID_RESPONSE" if "LLM_INVALID_RESPONSE" in err_msg else "BUG_ANALYSIS_FAILED"
        if "LLM_API_KEY_MISSING" in err_msg:
            code = "LLM_API_KEY_MISSING"
        elif "REPOSITORY_ISOLATION_FAILURE" in err_msg:
            code = "REPOSITORY_ISOLATION_FAILURE"

        return {
            "success": False,
            "error": {
                "code": code,
                "layer": "llm",
                "message": "Bug analysis failed during LLM or validation phase.",
                "root_cause": err_msg,
                "fix": "Verify LLM API key and network connection.",
            },
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "BUG_ANALYSIS_FAILED",
                "layer": "bug_detection",
                "message": "Unexpected failure during bug detection pipeline.",
                "root_cause": str(e),
                "fix": "Check backend logs for detailed stack trace.",
            },
        }
