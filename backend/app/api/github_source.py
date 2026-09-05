"""
GET /api/github/repositories/{repository_id}/file-content

Retrieves real source-code file lines from the cloned workspace for the interactive
Source Code Viewer.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/github", tags=["github-source"])

WORKSPACE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "workspace"


@router.get("/repositories/{repository_id}/file-content")
def get_file_content(
    repository_id: str,
    path: str = Query(..., description="Relative file path in repository"),
    start_line: int = Query(1, ge=1, description="Highlight start line (1-indexed)"),
    end_line: int | None = Query(None, description="Highlight end line (1-indexed)"),
    context_lines: int = Query(25, ge=0, description="Surrounding context line count"),
) -> dict:
    """
    Reads the actual source-code file from the cloned workspace and returns line-by-line
    data for code display and highlighting.
    """
    clean_id = (repository_id or "").strip()
    if not clean_id or not re.match(r"^[a-zA-Z0-9_\-\.]+$", clean_id) or ".." in clean_id:
        return {
            "success": False,
            "error": {
                "code": "INVALID_REPOSITORY_ID",
                "layer": "source_viewer",
                "message": "Invalid repository workspace identifier.",
                "root_cause": "Repository identifier contains invalid characters or path traversal elements.",
                "fix": "Provide a valid repository identifier.",
            },
        }

    resolved_base = WORKSPACE_BASE_DIR.resolve()
    target_dir = (resolved_base / clean_id).resolve()

    if target_dir.parent != resolved_base:
        return {
            "success": False,
            "error": {
                "code": "INVALID_REPOSITORY_ID",
                "layer": "source_viewer",
                "message": "Path traversal attempt detected.",
                "root_cause": "The requested repository path escapes the designated workspace directory.",
                "fix": "Only access repositories managed inside the application workspace.",
            },
        }

    # Resolve file path
    clean_path = path.strip().lstrip("/\\")
    file_path = (target_dir / clean_path).resolve()

    try:
        file_path.relative_to(target_dir)
    except ValueError:
        return {
            "success": False,
            "error": {
                "code": "PATH_TRAVERSAL_DETECTED",
                "layer": "source_viewer",
                "message": "Attempted to access file outside repository workspace.",
                "root_cause": f"Path '{path}' resolves outside repository directory.",
                "fix": "Provide a valid relative path within the repository.",
            },
        }

    if not file_path.exists() or not file_path.is_file():
        return {
            "success": False,
            "error": {
                "code": "FILE_NOT_FOUND",
                "layer": "source_viewer",
                "message": f"File '{clean_path}' was not found in repository.",
                "root_cause": f"No file exists at path: {file_path}",
                "fix": "Check the file path spelling.",
            },
        }

    try:
        raw_text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "FILESYSTEM_READ_ERROR",
                "layer": "source_viewer",
                "message": f"Failed to read file '{clean_path}'.",
                "root_cause": str(e),
                "fix": "Check file permissions.",
            },
        }

    all_lines = raw_text.splitlines()
    total_lines = len(all_lines)

    target_end = end_line if end_line is not None else start_line
    target_end = max(start_line, min(target_end, total_lines))

    # Calculate window bounds with surrounding context
    win_start = max(1, start_line - context_lines)
    win_end = min(total_lines, target_end + context_lines)

    formatted_lines = []
    for line_no in range(win_start, win_end + 1):
        idx = line_no - 1
        line_content = all_lines[idx] if idx < total_lines else ""
        is_highlighted = start_line <= line_no <= target_end
        formatted_lines.append(
            {
                "line_number": line_no,
                "content": line_content,
                "is_highlighted": is_highlighted,
            }
        )

    return {
        "success": True,
        "repository_id": clean_id,
        "file_path": clean_path,
        "total_lines": total_lines,
        "highlight_start": start_line,
        "highlight_end": target_end,
        "window_start": win_start,
        "window_end": win_end,
        "lines": formatted_lines,
    }
