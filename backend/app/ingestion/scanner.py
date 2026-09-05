"""
File Tree Scanner & Classifier for ingested repositories.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import IngestionException
from app.core.logging import get_logger

logger = get_logger(__name__)

# Directories to ignore during scanning
IGNORED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".target",
    "target",
    ".idea",
    ".vscode",
    "vendor",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
}

# Binary, media, and archive file extensions to skip
IGNORED_EXTENSIONS = {
    # Binaries & Executables
    ".exe", ".dll", ".so", ".dylib", ".pyc", ".pyo", ".pyd", ".o", ".obj", ".a", ".lib", ".bin", ".class",
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp", ".tiff", ".psd",
    # Audio & Video
    ".mp4", ".webm", ".avi", ".mov", ".flv", ".mkv", ".mp3", ".wav", ".ogg", ".flac",
    # Archives & Compressed
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".iso", ".jar", ".war",
    # Fonts
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    # Documents / PDFs
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Database files
    ".sqlite", ".sqlite3", ".db",
}

# Lock files to ignore/skip from deep source indexing
IGNORED_LOCK_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "cargo.lock",
    "gemfile.lock",
    "composer.lock",
}

# Extension to language mapping
LANGUAGE_MAP = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".cpp": "C++",
    ".hpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".c": "C",
    ".h": "C",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".swift": "Swift",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".sass": "CSS",
    ".less": "CSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".xml": "XML",
}


@dataclass
class ScannedFile:
    """Metadata extracted for a scanned file."""
    relative_path: str
    filename: str
    extension: str | None
    language: str | None
    size_bytes: int
    line_count: int
    sha256_hash: str
    is_readme: bool = False
    is_documentation: bool = False


@dataclass
class ScanResult:
    """Aggregated repository statistics and files."""
    total_files: int = 0
    total_size_bytes: int = 0
    total_directories: int = 0
    readme_path: str | None = None
    readme_content: str | None = None
    languages: dict[str, int] = field(default_factory=dict)  # language -> file_count
    language_lines: dict[str, int] = field(default_factory=dict)  # language -> line_count
    files: list[ScannedFile] = field(default_factory=list)
    documentation_files: list[str] = field(default_factory=list)


class FileScanner:
    """Scans and analyzes a cloned repository directory tree."""

    def __init__(
        self,
        max_file_size_bytes: int | None = None,
        max_repo_size_bytes: int | None = None,
    ) -> None:
        settings = get_settings()
        self.max_file_size_bytes = max_file_size_bytes or settings.MAX_FILE_SIZE_BYTES
        self.max_repo_size_bytes = max_repo_size_bytes or settings.MAX_REPO_SIZE_BYTES

    def scan_directory(self, repo_dir: Path) -> ScanResult:
        """
        Recursively scan a repository directory.
        
        Collects file count, language distribution, size statistics, README, and source files.
        Enforces path safety and configured size limits.
        """
        repo_dir = repo_dir.resolve()
        if not repo_dir.exists() or not repo_dir.is_dir():
            raise IngestionException(f"Repository directory '{repo_dir}' does not exist or is not a directory.")

        result = ScanResult()
        dirs_seen: set[str] = set()

        for root, dirs, files in os.walk(repo_dir, topdown=True):
            # Exclude ignored directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            rel_root = Path(root).relative_to(repo_dir)
            if str(rel_root) != ".":
                dirs_seen.add(str(rel_root))

            for filename in files:
                file_path = Path(root) / filename
                rel_file_path = file_path.relative_to(repo_dir)
                rel_path_str = str(rel_file_path).replace("\\", "/")

                # Path safety check
                try:
                    file_path.resolve().relative_to(repo_dir)
                except ValueError:
                    logger.warning("Skipping file outside repository root (path traversal check)", path=rel_path_str)
                    continue

                # Check lock files
                if filename.lower() in IGNORED_LOCK_FILES:
                    logger.debug("Skipping lock file", file=rel_path_str)
                    continue

                # Check extension
                ext = file_path.suffix.lower()
                if ext in IGNORED_EXTENSIONS:
                    logger.debug("Skipping binary/media file", file=rel_path_str, ext=ext)
                    continue

                # Check file size
                try:
                    file_size = file_path.stat().st_size
                except OSError:
                    continue

                if file_size > self.max_file_size_bytes:
                    logger.info("Skipping oversized file", file=rel_path_str, size_bytes=file_size)
                    continue

                # Enforce total repo cumulative size limit
                result.total_size_bytes += file_size
                if result.total_size_bytes > self.max_repo_size_bytes:
                    raise IngestionException(
                        f"Repository total size exceeds maximum limit of "
                        f"{self.max_repo_size_bytes / (1024 * 1024):.1f} MB."
                    )

                # Process text file content
                try:
                    content_bytes = file_path.read_bytes()
                except OSError as e:
                    logger.warning("Could not read file", file=rel_path_str, error=str(e))
                    continue

                # Quick null-byte check to filter out undetected binary files
                if b"\x00" in content_bytes[:1024]:
                    logger.debug("Skipping binary file detected by null-bytes", file=rel_path_str)
                    result.total_size_bytes -= file_size
                    continue

                # Calculate SHA256 and line count
                sha256_hash = hashlib.sha256(content_bytes).hexdigest()
                text_content = content_bytes.decode("utf-8", errors="replace")
                line_count = len(text_content.splitlines())

                # Determine language
                language = LANGUAGE_MAP.get(ext)
                if not language and filename.lower() in ("dockerfile", "makefile", "jenkinsfile"):
                    language = filename.capitalize()

                if language:
                    result.languages[language] = result.languages.get(language, 0) + 1
                    result.language_lines[language] = result.language_lines.get(language, 0) + line_count

                # README check
                is_readme = filename.lower().startswith("readme")
                if is_readme and not result.readme_path:
                    result.readme_path = rel_path_str
                    result.readme_content = text_content[:10000]  # Store prefix of README

                # Documentation check
                is_docs = "docs/" in rel_path_str.lower() or ext in (".md", ".rst")
                if is_docs:
                    result.documentation_files.append(rel_path_str)

                scanned_file = ScannedFile(
                    relative_path=rel_path_str,
                    filename=filename,
                    extension=ext if ext else None,
                    language=language,
                    size_bytes=file_size,
                    line_count=line_count,
                    sha256_hash=sha256_hash,
                    is_readme=is_readme,
                    is_documentation=is_docs,
                )
                result.files.append(scanned_file)
                result.total_files += 1

        result.total_directories = len(dirs_seen)
        logger.info(
            "Completed file tree scan",
            total_files=result.total_files,
            total_size_mb=result.total_size_bytes / (1024 * 1024),
            languages=list(result.languages.keys()),
        )
        return result
