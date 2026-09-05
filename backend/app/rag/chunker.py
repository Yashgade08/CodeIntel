"""
Semantic chunker for source code, markdown documentation, READMEs, and GitHub issues/PRs.
Preserves line-level provenance and citation metadata.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DocumentChunk:
    """A semantically coherent chunk of text/code with provenance metadata."""
    id: str
    repository_id: str
    file_path: str
    start_line: int
    end_line: int
    content: str
    source_type: str  # code, readme, documentation, issue, pull_request
    language: str | None = None
    symbol_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def citation_str(self) -> str:
        """Format citation representation, e.g. auth/service.py:42-78."""
        if self.start_line == self.end_line or self.end_line <= 0:
            return f"{self.file_path}:{max(1, self.start_line)}"
        return f"{self.file_path}:{self.start_line}-{self.end_line}"


class SemanticChunker:
    """Splits documents and source code into semantically meaningful chunks."""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        settings = get_settings()
        self.max_chunk_chars = (chunk_size or settings.CHUNK_SIZE) * 4  # char approximation
        self.overlap_chars = (chunk_overlap or settings.CHUNK_OVERLAP) * 4

    def chunk_source_code(
        self,
        content: str,
        file_path: str,
        repository_id: str,
        language: str | None = None,
    ) -> list[DocumentChunk]:
        """
        Chunk source code files into line-aware chunks, detecting function/class definitions.
        """
        lines = content.splitlines()
        if not lines:
            return []

        chunks: list[DocumentChunk] = []
        current_lines: list[str] = []
        current_start_line = 1
        current_symbol: str | None = None

        # Basic definition patterns for Python, JS/TS, Java, Go, C++
        def_pattern = re.compile(
            r"^\s*(class|def|function|async function|pub fn|func|type|interface|const\s+\w+\s*=)\s+([a-zA-Z0-9_]+)"
        )

        for i, line in enumerate(lines, start=1):
            match = def_pattern.match(line)
            if match and not current_symbol:
                current_symbol = match.group(2)

            current_lines.append(line)
            current_text = "\n".join(current_lines)

            # If cumulative size exceeds max_chunk_chars or top-level block ends
            if len(current_text) >= self.max_chunk_chars:
                chunk_id = str(uuid.uuid4())
                chunks.append(
                    DocumentChunk(
                        id=chunk_id,
                        repository_id=repository_id,
                        file_path=file_path,
                        start_line=current_start_line,
                        end_line=i,
                        content=current_text,
                        source_type="code",
                        language=language,
                        symbol_name=current_symbol,
                    )
                )
                
                # Apply line overlap
                overlap_line_count = max(1, min(5, len(current_lines) // 4))
                current_lines = current_lines[-overlap_line_count:]
                current_start_line = i - overlap_line_count + 1
                current_symbol = None

        # Final remaining lines
        if current_lines:
            chunk_id = str(uuid.uuid4())
            chunks.append(
                DocumentChunk(
                    id=chunk_id,
                    repository_id=repository_id,
                    file_path=file_path,
                    start_line=current_start_line,
                    end_line=len(lines),
                    content="\n".join(current_lines),
                    source_type="code",
                    language=language,
                    symbol_name=current_symbol,
                )
            )

        return chunks

    def chunk_markdown(
        self,
        content: str,
        file_path: str,
        repository_id: str,
        source_type: str = "documentation",
    ) -> list[DocumentChunk]:
        """
        Chunk Markdown and documentation files based on headers (#, ##, ###) and line ranges.
        """
        lines = content.splitlines()
        if not lines:
            return []

        chunks: list[DocumentChunk] = []
        current_lines: list[str] = []
        current_start_line = 1
        header_pattern = re.compile(r"^#{1,6}\s+(.+)$")
        current_header: str | None = None

        for i, line in enumerate(lines, start=1):
            h_match = header_pattern.match(line)
            if h_match:
                if current_lines and len("\n".join(current_lines)) >= self.max_chunk_chars // 2:
                    chunk_id = str(uuid.uuid4())
                    chunks.append(
                        DocumentChunk(
                            id=chunk_id,
                            repository_id=repository_id,
                            file_path=file_path,
                            start_line=current_start_line,
                            end_line=i - 1,
                            content="\n".join(current_lines),
                            source_type=source_type,
                            symbol_name=current_header,
                        )
                    )
                    current_lines = []
                    current_start_line = i
                current_header = h_match.group(1)

            current_lines.append(line)
            if len("\n".join(current_lines)) >= self.max_chunk_chars:
                chunk_id = str(uuid.uuid4())
                chunks.append(
                    DocumentChunk(
                        id=chunk_id,
                        repository_id=repository_id,
                        file_path=file_path,
                        start_line=current_start_line,
                        end_line=i,
                        content="\n".join(current_lines),
                        source_type=source_type,
                        symbol_name=current_header,
                    )
                )
                overlap_line_count = max(1, min(3, len(current_lines) // 4))
                current_lines = current_lines[-overlap_line_count:]
                current_start_line = i - overlap_line_count + 1

        if current_lines:
            chunk_id = str(uuid.uuid4())
            chunks.append(
                DocumentChunk(
                    id=chunk_id,
                    repository_id=repository_id,
                    file_path=file_path,
                    start_line=current_start_line,
                    end_line=len(lines),
                    content="\n".join(current_lines),
                    source_type=source_type,
                    symbol_name=current_header,
                )
            )

        return chunks

    def chunk_issue(
        self,
        issue_data: dict[str, Any],
        repository_id: str,
    ) -> list[DocumentChunk]:
        """
        Format and chunk a GitHub issue or pull request record.
        """
        issue_num = issue_data.get("github_issue_number", 0)
        is_pr = issue_data.get("is_pull_request", False)
        source_type = "pull_request" if is_pr else "issue"
        prefix = "PR #" if is_pr else "Issue #"

        title = issue_data.get("title", "")
        body = issue_data.get("body") or ""
        author = issue_data.get("author") or "unknown"
        state = issue_data.get("state", "open")
        labels = issue_data.get("labels", [])

        file_path = f"{source_type}s/{source_type}_{issue_num}.md"
        formatted_content = (
            f"# {prefix}{issue_num}: {title}\n"
            f"**Author**: {author} | **State**: {state} | **Labels**: {', '.join(labels)}\n\n"
            f"{body}"
        )

        lines = formatted_content.splitlines()
        return [
            DocumentChunk(
                id=str(uuid.uuid4()),
                repository_id=repository_id,
                file_path=file_path,
                start_line=1,
                end_line=len(lines),
                content=formatted_content,
                source_type=source_type,
                symbol_name=f"{prefix}{issue_num}",
                metadata={"issue_number": issue_num, "state": state, "author": author},
            )
        ]
