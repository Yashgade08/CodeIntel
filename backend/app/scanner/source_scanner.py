"""
Source Code File Scanner & Reader

Discovers and reads source-code files relevant for Code Intelligence and Bug Analysis.
Filters by supported programming language extensions and excludes non-code, generated,
and oversized files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Supported source code and configuration extensions
SUPPORTED_EXTENSIONS = {
    # Core programming languages
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c_header",
    ".hpp": "cpp_header",
    ".go": "go",
    ".rs": "rust",
    ".php": "php",
    ".rb": "ruby",
    ".cs": "csharp",
    # Config & Documentation
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
}

# Directories to exclude from scanning
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

# Explicit excluded filenames
EXCLUDED_FILENAMES = {
    ".ds_store",
    "thumbs.db",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "cargo.lock",
    "poetry.lock",
}


@dataclass
class SourceFile:
    file_path: str       # Relative path (e.g. src/auth.py)
    absolute_path: str   # Local absolute filesystem path
    language: str        # Normalized language identifier
    extension: str       # File suffix (e.g. .py)
    size_bytes: int      # File size
    content: str         # File text content


def scan_source_files(
    repo_directory: Path,
    max_file_size_mb: int = 5,
) -> list[SourceFile]:
    """
    Recursively scans the cloned repository workspace and reads all relevant
    source code files into SourceFile objects.
    """
    max_bytes = max_file_size_mb * 1024 * 1024
    discovered: list[SourceFile] = []

    for root, dirs, files in os.walk(repo_directory):
        # Exclude unwanted directories in-place to prevent traversing them
        dirs[:] = [
            d for d in dirs
            if d.lower() not in EXCLUDED_DIRS
            and not d.startswith(".git")
            and not d.lower().endswith(".egg-info")
        ]

        current_dir = Path(root)

        for filename in files:
            lower_name = filename.lower()
            if lower_name in EXCLUDED_FILENAMES:
                continue

            file_ext = Path(filename).suffix.lower()
            if file_ext not in SUPPORTED_EXTENSIONS:
                continue

            full_path = current_dir / filename

            try:
                stat = full_path.stat()
                if stat.st_size > max_bytes:
                    continue  # Skip oversized files
            except (OSError, PermissionError):
                continue

            # Read content safely
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                try:
                    content = full_path.read_text(encoding="latin-1", errors="replace")
                except Exception:
                    continue

            # If file is empty, skip
            if not content.strip():
                continue

            rel_path = full_path.relative_to(repo_directory).as_posix()
            language = SUPPORTED_EXTENSIONS[file_ext]

            discovered.append(
                SourceFile(
                    file_path=rel_path,
                    absolute_path=str(full_path),
                    language=language,
                    extension=file_ext,
                    size_bytes=stat.st_size,
                    content=content,
                )
            )

    return discovered
