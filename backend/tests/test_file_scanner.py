"""
Unit tests for file scanner, directory filtering, and language detection.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.core.exceptions import IngestionException
from app.ingestion.scanner import FileScanner


def test_file_scanner_filtering_and_detection():
    """Test scanner correctly filters ignored dirs/binaries and detects languages."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create valid source files
        py_file = tmp_path / "main.py"
        py_file.write_text("print('hello world')\n", encoding="utf-8")

        ts_file = tmp_path / "app.tsx"
        ts_file.write_text("export const App = () => <div>Hello</div>;\n", encoding="utf-8")

        readme_file = tmp_path / "README.md"
        readme_file.write_text("# Test Repo\nThis is a test readme.\n", encoding="utf-8")

        # Create ignored directory and files
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("git config", encoding="utf-8")

        node_modules = tmp_path / "node_modules" / "package"
        node_modules.mkdir(parents=True)
        (node_modules / "index.js").write_text("console.log()", encoding="utf-8")

        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()
        (venv_dir / "pyvenv.cfg").write_text("home = ...", encoding="utf-8")

        # Create ignored binary and lock file
        (tmp_path / "binary.exe").write_bytes(b"\x00\x01\x02\x03\x04")
        (tmp_path / "yarn.lock").write_text("# lock file", encoding="utf-8")

        scanner = FileScanner()
        result = scanner.scan_directory(tmp_path)

        # Assert correct file counts
        assert result.total_files == 3  # main.py, app.tsx, README.md
        rel_paths = [f.relative_path for f in result.files]
        assert "main.py" in rel_paths
        assert "app.tsx" in rel_paths
        assert "README.md" in rel_paths

        # Assert ignored files are excluded
        assert not any("node_modules" in p for p in rel_paths)
        assert not any(".git" in p for p in rel_paths)
        assert not any("venv" in p for p in rel_paths)
        assert "binary.exe" not in rel_paths
        assert "yarn.lock" not in rel_paths

        # Assert language detection
        assert result.languages.get("Python") == 1
        assert result.languages.get("TypeScript") == 1
        assert result.languages.get("Markdown") == 1

        # Assert README path
        assert result.readme_path == "README.md"


def test_file_scanner_oversized_file_handling():
    """Test scanner skips files exceeding max_file_size_bytes."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        large_file = tmp_path / "large.py"
        large_file.write_text("a" * 200, encoding="utf-8")

        small_file = tmp_path / "small.py"
        small_file.write_text("print('small')", encoding="utf-8")

        # Set limit to 100 bytes
        scanner = FileScanner(max_file_size_bytes=100)
        result = scanner.scan_directory(tmp_path)

        assert result.total_files == 1
        assert result.files[0].relative_path == "small.py"


def test_file_scanner_repo_size_limit_exceeded():
    """Test scanner raises IngestionException if cumulative size exceeds limit."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        (tmp_path / "file1.py").write_text("a" * 100, encoding="utf-8")
        (tmp_path / "file2.py").write_text("b" * 100, encoding="utf-8")

        # Set max total repo size to 150 bytes
        scanner = FileScanner(max_file_size_bytes=1000, max_repo_size_bytes=150)

        with pytest.raises(IngestionException) as exc_info:
            scanner.scan_directory(tmp_path)

        assert "Repository total size exceeds maximum limit" in str(exc_info.value)
