"""
Structure-Aware Code Chunker

Splits source code files into meaningful, syntactically coherent chunks (classes,
functions, methods, logical blocks) while maintaining exact 1-indexed line numbers
and generating deterministic chunk IDs for deduplication.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Sequence

from app.scanner.source_scanner import SourceFile


@dataclass
class CodeChunk:
    chunk_id: str
    repository_id: str
    repository: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    content: str
    symbol_name: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# Regex patterns for identifying top-level and method boundaries across common languages
_PYTHON_DEF_RE = re.compile(r"^(?:async\s+)?def\s+([a-zA-Z0-9_]+)\s*\(|^class\s+([a-zA-Z0-9_]+)")
_JS_TS_DEF_RE = re.compile(
    r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\s*([a-zA-Z0-9_]*)|class\s+([a-zA-Z0-9_]+)|const\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>|let\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)"
)
_GENERIC_CLASS_FUNC_RE = re.compile(
    r"^(?:public|private|protected|static|final|native|synchronized|abstract|async|\s)*"
    r"(?:class|interface|struct|enum|fn|func|def)\s+([a-zA-Z0-9_]+)"
)


def _generate_chunk_id(
    repository_id: str,
    file_path: str,
    start_line: int,
    end_line: int,
    content: str,
) -> str:
    """Generate a deterministic 24-char SHA256 identifier."""
    content_hash = hashlib.md5(content.strip().encode("utf-8")).hexdigest()
    raw_key = f"{repository_id}:{file_path}:{start_line}:{end_line}:{content_hash}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:24]


def chunk_source_file(
    source_file: SourceFile,
    repository_id: str,
    repository_name: str,
    max_chunk_lines: int = 60,
    min_chunk_lines: int = 6,
    overlap_lines: int = 8,
) -> list[CodeChunk]:
    """
    Chunks a single source file using language-aware boundaries where possible,
    falling back to structured sliding-window chunking.
    Preserves exact 1-indexed start_line and end_line.
    """
    lines = source_file.content.splitlines()
    total_lines = len(lines)

    if total_lines == 0:
        return []

    # If the file is small, preserve it as a single intact chunk
    if total_lines <= max_chunk_lines:
        content = "\n".join(lines)
        chunk_id = _generate_chunk_id(repository_id, source_file.file_path, 1, total_lines, content)
        return [
            CodeChunk(
                chunk_id=chunk_id,
                repository_id=repository_id,
                repository=repository_name,
                file_path=source_file.file_path,
                language=source_file.language,
                start_line=1,
                end_line=total_lines,
                content=content,
            )
        ]

    # Find structural split boundaries
    boundary_indices: list[int] = [0]

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "/*", "*", '"""', "'''")):
            continue

        # Match Python definitions at indent 0 or 4
        if source_file.language == "python" and (line.startswith("def ") or line.startswith("async def ") or line.startswith("class ") or line.startswith("    def ") or line.startswith("    async def ")):
            if idx > 0 and (idx - boundary_indices[-1]) >= min_chunk_lines:
                boundary_indices.append(idx)
        # Match JS/TS/Go/Java/Rust definitions
        elif source_file.language in ("javascript", "typescript", "go", "rust", "java", "c", "cpp", "csharp"):
            if _JS_TS_DEF_RE.match(line) or _GENERIC_CLASS_FUNC_RE.match(line):
                if idx > 0 and (idx - boundary_indices[-1]) >= min_chunk_lines:
                    boundary_indices.append(idx)

    boundary_indices.append(total_lines)

    chunks: list[CodeChunk] = []

    # Assemble chunks based on boundaries, splitting any oversized segments
    for i in range(len(boundary_indices) - 1):
        seg_start = boundary_indices[i]
        seg_end = boundary_indices[i + 1]
        seg_len = seg_end - seg_start

        if seg_len <= max_chunk_lines:
            chunk_lines = lines[seg_start:seg_end]
            chunk_content = "\n".join(chunk_lines)
            if chunk_content.strip():
                start_line_1 = seg_start + 1
                end_line_1 = seg_end
                chunk_id = _generate_chunk_id(
                    repository_id, source_file.file_path, start_line_1, end_line_1, chunk_content
                )
                chunks.append(
                    CodeChunk(
                        chunk_id=chunk_id,
                        repository_id=repository_id,
                        repository=repository_name,
                        file_path=source_file.file_path,
                        language=source_file.language,
                        start_line=start_line_1,
                        end_line=end_line_1,
                        content=chunk_content,
                    )
                )
        else:
            # Segment is too large; split using window with overlap
            window_start = seg_start
            while window_start < seg_end:
                window_end = min(window_start + max_chunk_lines, seg_end)
                chunk_lines = lines[window_start:window_end]
                chunk_content = "\n".join(chunk_lines)
                if chunk_content.strip():
                    start_line_1 = window_start + 1
                    end_line_1 = window_end
                    chunk_id = _generate_chunk_id(
                        repository_id, source_file.file_path, start_line_1, end_line_1, chunk_content
                    )
                    chunks.append(
                        CodeChunk(
                            chunk_id=chunk_id,
                            repository_id=repository_id,
                            repository=repository_name,
                            file_path=source_file.file_path,
                            language=source_file.language,
                            start_line=start_line_1,
                            end_line=end_line_1,
                            content=chunk_content,
                        )
                    )

                if window_end >= seg_end:
                    break
                window_start += (max_chunk_lines - overlap_lines)

    return chunks


def chunk_repository_files(
    source_files: Sequence[SourceFile],
    repository_id: str,
    repository_name: str,
) -> list[CodeChunk]:
    """Chunk all discovered source files for a repository."""
    all_chunks: list[CodeChunk] = []
    for sf in source_files:
        chunks = chunk_source_file(sf, repository_id, repository_name)
        all_chunks.extend(chunks)
    return all_chunks
