"""
GET /api/github/repositories/{repository_id}/file-structure

Parses a specific source-code file inside a cloned repository workspace using
AST (Python) or structure-aware token scanning (JS/TS/polyglot).
Returns:
- Classes, interfaces, methods, attributes
- Functions, arguments, return types, decorators, line ranges
- Imports and dependencies
- Internal function-to-function / method call-flow relationships
- Render-ready Mermaid.js syntax (Flowchart and Class Diagram)

Enforces strict repository isolation and path traversal prevention.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Query

from app.parser.file_structure_parser import analyze_file_structure

router = APIRouter(prefix="/api/github", tags=["github-file-structure"])

WORKSPACE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "workspace"


@router.get("/repositories/{repository_id}/file-structure")
def get_file_structure(
    repository_id: str,
    path: str = Query(..., description="Relative file path within repository"),
    format: str = Query("flowchart", description="Diagram format: flowchart | class_diagram"),
) -> dict:
    """
    Analyzes the internal symbol structure of a file and returns Mermaid.js diagram syntax.
    """
    clean_id = (repository_id or "").strip()
    if not clean_id or not re.match(r"^[a-zA-Z0-9_\-\.]+$", clean_id) or ".." in clean_id:
        return {
            "success": False,
            "error": {
                "code": "INVALID_REPOSITORY_ID",
                "layer": "file_structure",
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
                "layer": "file_structure",
                "message": "Path traversal attempt detected.",
                "root_cause": "The requested repository path escapes the designated workspace directory.",
                "fix": "Only access repositories managed inside the application workspace.",
            },
        }

    # Validate file path safety immediately
    clean_file_path = path.strip().lstrip("/\\")
    if not clean_file_path or ".." in clean_file_path:
        return {
            "success": False,
            "error": {
                "code": "INVALID_FILE_PATH",
                "layer": "file_structure",
                "message": "Invalid or unsafe file path requested.",
                "root_cause": f"File path '{path}' contains path traversal or empty value.",
                "fix": "Provide a safe relative file path within the repository.",
            },
        }

    if not target_dir.is_dir():
        return {
            "success": False,
            "error": {
                "code": "REPOSITORY_NOT_FOUND",
                "layer": "file_structure",
                "message": f"Workspace '{clean_id}' not found.",
                "root_cause": f"No cloned directory exists at backend/workspace/{clean_id}.",
                "fix": "Clone the repository first via POST /api/github/clone.",
            },
        }

    target_file = (target_dir / clean_file_path).resolve()
    try:
        target_file.relative_to(target_dir)
    except ValueError:
        return {
            "success": False,
            "error": {
                "code": "PATH_TRAVERSAL_DETECTED",
                "layer": "file_structure",
                "message": "File path escapes workspace root.",
                "root_cause": f"Resolved path '{target_file}' is outside repository directory.",
                "fix": "Specify a relative file path that remains inside the repository.",
            },
        }

    if not target_file.is_file():
        return {
            "success": False,
            "error": {
                "code": "FILE_NOT_FOUND",
                "layer": "file_structure",
                "message": f"Source file '{clean_file_path}' not found.",
                "root_cause": f"The file does not exist on disk at {target_file}.",
                "fix": "Verify that the file path matches a discovered source file from GET /files.",
            },
        }

    # Parse file structure
    try:
        data = analyze_file_structure(target_file, clean_file_path)
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "PARSING_FAILED",
                "layer": "file_structure",
                "message": f"Failed to parse internal structure of '{clean_file_path}'.",
                "root_cause": str(e),
                "fix": "Check that the file contains valid text/source code.",
            },
        }

    selected_syntax = (
        data["class_diagram_syntax"]
        if format == "class_diagram" and data.get("class_diagram_syntax")
        else data["mermaid_syntax"]
    )

    return {
        "success": True,
        "repository_id": clean_id,
        "format": format,
        "active_syntax": selected_syntax,
        **data,
    }
