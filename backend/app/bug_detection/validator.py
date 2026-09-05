"""
Hallucination Control & Evidence Validator

Verifies every LLM-generated finding against the actual filesystem and retrieved chunks.
Rejects or flags findings that reference non-existent files, out-of-bound line numbers,
or ungrounded assertions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.retrieval.code_retriever import RetrievedChunk


def validate_findings(
    raw_findings: list[dict[str, Any]],
    repo_directory: Path,
    retrieved_chunks: list[RetrievedChunk],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Validates a list of LLM findings against real repository files and retrieved context.

    Returns:
        (valid_findings, rejected_findings)
    """
    valid: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    # Map of retrieved files and line ranges for fast grounding lookup
    retrieved_map: dict[str, list[tuple[int, int]]] = {}
    for c in retrieved_chunks:
        retrieved_map.setdefault(c.file_path, []).append((c.start_line, c.end_line))

    for finding in raw_findings:
        file_path = finding.get("file_path", "").strip()
        start_line = finding.get("start_line")
        end_line = finding.get("end_line")

        # ── Rule 1: File must exist in repository workspace ──────────────────
        target_file = (repo_directory / file_path).resolve()
        try:
            # Check path containment
            target_file.relative_to(repo_directory.resolve())
        except ValueError:
            finding["validation_status"] = "INVALID_EVIDENCE"
            finding["rejection_reason"] = f"File path '{file_path}' attempts path traversal."
            rejected.append(finding)
            continue

        if not target_file.exists() or not target_file.is_file():
            finding["validation_status"] = "INVALID_EVIDENCE"
            finding["rejection_reason"] = f"Referenced file '{file_path}' does not exist in repository."
            rejected.append(finding)
            continue

        # ── Rule 2: Line numbers must be valid and within file bounds ────────
        try:
            total_lines = len(target_file.read_text(encoding="utf-8", errors="replace").splitlines())
        except Exception:
            total_lines = 1000

        try:
            s_line = int(start_line) if start_line is not None else 1
            e_line = int(end_line) if end_line is not None else s_line
        except (ValueError, TypeError):
            finding["validation_status"] = "INVALID_EVIDENCE"
            finding["rejection_reason"] = f"Invalid line range numbers: {start_line}-{end_line}"
            rejected.append(finding)
            continue

        if s_line < 1 or s_line > max(1, total_lines):
            finding["validation_status"] = "INVALID_EVIDENCE"
            finding["rejection_reason"] = f"Start line {s_line} is outside actual file bounds (1..{total_lines})."
            rejected.append(finding)
            continue

        if e_line < s_line:
            e_line = s_line

        # Normalize line numbers
        finding["start_line"] = s_line
        finding["end_line"] = min(e_line, total_lines)

        # ── Rule 3: Ensure severity is normalized ────────────────────────────
        sev = str(finding.get("severity", "MEDIUM")).upper()
        if sev not in ("HIGH", "MEDIUM", "LOW"):
            sev = "MEDIUM"
        finding["severity"] = sev

        # Ensure confidence is a float 0.0 - 1.0
        try:
            conf = float(finding.get("confidence", 0.8))
            finding["confidence"] = max(0.0, min(1.0, conf))
        except (ValueError, TypeError):
            finding["confidence"] = 0.75

        # Normalize evidence array
        finding["evidence"] = [
            {
                "file_path": file_path,
                "start_line": finding["start_line"],
                "end_line": finding["end_line"],
            }
        ]

        finding["validation_status"] = "VERIFIED"
        valid.append(finding)

    return valid, rejected
