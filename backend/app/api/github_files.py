"""
GET /api/github/repositories/{repository_id}/files

Scans the local workspace directory of a cloned repository.
Returns:
- Total file count
- Total directory count
- File-extension / language summary
- List of relative file paths, extensions, and file sizes

Excludes generated/dependency directories (.git, node_modules, __pycache__, etc.)
Strict security: prevents path traversal and enforces repository isolation.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/github", tags=["github-files"])

# Base workspace directory: backend/workspace/
WORKSPACE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "workspace"

# Standard directories and files to exclude from scanning
EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".cache",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    ".turbo",
    "target",
    "bin",
    "obj",
    ".cargo",
    ".egg-info",
}

EXCLUDED_FILES = {
    ".ds_store",
    "thumbs.db",
}

# Extension to language display name mapping
EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".pyi": "Python (Stub)",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".rst": "reStructuredText",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".ini": "INI / Config",
    ".cfg": "Config",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SASS",
    ".less": "LESS",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cpp": "C++",
    ".cc": "C++",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".bat": "Batch",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".txt": "Text",
    ".xml": "XML",
    ".svg": "SVG / Image",
    ".png": "Image (PNG)",
    ".jpg": "Image (JPEG)",
    ".jpeg": "Image (JPEG)",
    ".gif": "Image (GIF)",
    ".lock": "Lockfile",
}


def _extract_repo_metadata(repo_dir: Path, repository_id: str) -> tuple[str, str]:
    """
    Extract repository owner and name from .git/config if available,
    falling back to parsing the repository_id string.
    """
    git_config = repo_dir / ".git" / "config"
    if git_config.exists():
        try:
            content = git_config.read_text(encoding="utf-8", errors="ignore")
            # Look for github.com/owner/repo or github.com:owner/repo
            match = re.search(r"github\.com[/:]([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+?)(?:\.git)?\s*$", content, re.MULTILINE)
            if match:
                return match.group(1), match.group(2)
        except Exception:
            pass

    # Fallback: parse workspace_id format {owner}_{name}_{timestamp}_{hash}
    parts = repository_id.split("_")
    if len(parts) >= 4:
        owner = parts[0]
        # In case repository name has underscores, middle tokens belong to repo name
        name = "_".join(parts[1:-2])
        return owner, name
    elif len(parts) >= 2:
        return parts[0], parts[1]

    return "unknown", repository_id


@router.get("/repositories/{repository_id}/files")
def get_repository_files(repository_id: str) -> dict:
    """
    Scan the workspace directory for the specified repository_id.

    Returns:
        success=True  -> { success, repository, files: { total, directories, summary, items } }
        success=False -> { success, error: { code, layer, message, root_cause, fix } }
    """
    # ── Step 1: Validate repository_id security & format ─────────────────
    clean_id = (repository_id or "").strip()
    if not clean_id or not re.match(r"^[a-zA-Z0-9_\-\.]+$", clean_id) or ".." in clean_id:
        return {
            "success": False,
            "error": {
                "code": "INVALID_REPOSITORY_ID",
                "layer": "file_scanner",
                "message": "Invalid repository workspace identifier.",
                "root_cause": f"Repository identifier '{clean_id}' contains illegal characters or path traversal elements.",
                "fix": "Provide a valid repository identifier returned from the clone operation.",
            },
        }

    # ── Step 2: Resolve workspace path & enforce workspace boundary ───────
    try:
        resolved_base = WORKSPACE_BASE_DIR.resolve()
        target_dir = (resolved_base / clean_id).resolve()

        # Strict containment check: target_dir must be an immediate child of WORKSPACE_BASE_DIR
        if target_dir.parent != resolved_base:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_REPOSITORY_ID",
                    "layer": "file_scanner",
                    "message": "Path traversal attempt detected.",
                    "root_cause": "The requested repository path escapes the designated workspace directory.",
                    "fix": "Only access repositories managed inside the application workspace.",
                },
            }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "FILE_SCAN_FAILED",
                "layer": "file_scanner",
                "message": "Failed to resolve repository workspace path.",
                "root_cause": str(e),
                "fix": "Check the workspace identifier format.",
            },
        }

    # ── Step 3: Check existence ──────────────────────────────────────────
    if not target_dir.exists() or not target_dir.is_dir():
        return {
            "success": False,
            "error": {
                "code": "REPOSITORY_NOT_FOUND",
                "layer": "file_scanner",
                "message": f"Repository workspace '{clean_id}' was not found.",
                "root_cause": f"No cloned directory exists at workspace path: {target_dir}",
                "fix": "Ensure the repository has been cloned before scanning its files.",
            },
        }

    # ── Step 4: Scan directory recursively ───────────────────────────────
    owner, name = _extract_repo_metadata(target_dir, clean_id)

    items: list[dict] = []
    discovered_directories: set[str] = set()
    extension_counts: dict[str, int] = {}

    try:
        for root, dirs, files in os.walk(target_dir):
            # Exclude unwanted directories in-place (prevents recursion into them)
            dirs[:] = [
                d for d in dirs
                if d.lower() not in EXCLUDED_DIRS
                and not d.startswith(".git")
                and not any(d.lower().endswith(suffix) for suffix in [".egg-info"])
            ]

            current_dir_path = Path(root)

            # Record relative directory path if not the root repo folder itself
            if current_dir_path != target_dir:
                rel_dir = current_dir_path.relative_to(target_dir).as_posix()
                discovered_directories.add(rel_dir)

            for filename in files:
                if filename.lower() in EXCLUDED_FILES:
                    continue

                file_path = current_dir_path / filename
                rel_file_path = file_path.relative_to(target_dir).as_posix()
                suffix = file_path.suffix.lower()

                # Basic file size
                try:
                    size = file_path.stat().st_size
                except (OSError, PermissionError):
                    size = 0

                items.append({
                    "path": rel_file_path,
                    "type": "file",
                    "extension": suffix,
                    "size": size,
                })

                # Aggregate extension summary
                lang_name = EXTENSION_LANGUAGE_MAP.get(suffix, suffix.upper().lstrip(".") if suffix else "No Extension")
                extension_counts[lang_name] = extension_counts.get(lang_name, 0) + 1

    except PermissionError as pe:
        return {
            "success": False,
            "error": {
                "code": "FILESYSTEM_READ_ERROR",
                "layer": "file_scanner",
                "message": "Permission denied while scanning repository files.",
                "root_cause": str(pe),
                "fix": "Check filesystem read permissions for the workspace directory.",
            },
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "FILE_SCAN_FAILED",
                "layer": "file_scanner",
                "message": "An error occurred while scanning repository files.",
                "root_cause": str(e),
                "fix": "Verify that the workspace files are accessible and not corrupted.",
            },
        }

    # Sort items by path for predictable, deterministic order
    items.sort(key=lambda item: item["path"].lower())

    # Sort summary by count descending
    sorted_summary = dict(sorted(extension_counts.items(), key=lambda x: x[1], reverse=True))

    return {
        "success": True,
        "repository": {
            "owner": owner,
            "name": name,
            "workspace_id": clean_id,
        },
        "files": {
            "total": len(items),
            "directories": len(discovered_directories),
            "summary": sorted_summary,
            "items": items,
        },
    }
