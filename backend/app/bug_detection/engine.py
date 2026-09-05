"""
Bug Detection Engine

Orchestrates RAG retrieval, LLM analysis, and Evidence Validation for code intelligence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.bug_detection.prompts import SYSTEM_BUG_DETECTION_PROMPT, build_user_prompt
from app.bug_detection.validator import validate_findings
from app.core.config import get_settings
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider
from app.retrieval.code_retriever import CodeRetriever, get_code_retriever


class BugDetectionEngine:
    """
    Coordinates RAG code retrieval, LLM prompting, and evidence validation.
    """

    def __init__(
        self,
        retriever: CodeRetriever | None = None,
        llm_provider: LLMProvider | None = None,
    ):
        self.retriever = retriever or get_code_retriever()
        self.llm_provider = llm_provider or get_llm_provider()

    def analyze_repository_bugs(
        self,
        repository_id: str,
        repo_directory: Path,
        query: str = "Find potential bugs, logic errors, and security issues in this repository",
        top_k: int | None = None,
    ) -> dict[str, Any]:
        """
        Runs the full Bug Detection RAG pipeline.
        """
        settings = get_settings()

        # ── Step 1: Retrieve Relevant Code Chunks ────────────────────────────
        retrieved_chunks = self.retriever.retrieve(
            repository_id=repository_id,
            query=query,
            top_k=top_k or settings.TOP_K,
        )

        if not retrieved_chunks:
            return {
                "success": True,
                "repository_id": repository_id,
                "query": query,
                "summary": "No indexed code chunks found for this repository. Please index the repository first.",
                "total_findings": 0,
                "findings": [],
                "retrieved_context_count": 0,
            }

        repo_name = retrieved_chunks[0].repository if retrieved_chunks else repository_id

        # ── Step 2: Build Prompts ────────────────────────────────────────────
        user_prompt = build_user_prompt(
            user_query=query,
            retrieved_chunks=retrieved_chunks,
            repository_name=repo_name,
        )

        # ── Step 3: LLM Inference ────────────────────────────────────────────
        llm_response = self.llm_provider.generate_analysis(
            system_prompt=SYSTEM_BUG_DETECTION_PROMPT,
            user_prompt=user_prompt,
            temperature=settings.LLM_TEMPERATURE,
        )

        raw_findings = llm_response.get("findings", [])
        summary = llm_response.get("summary", "Analysis completed.")

        # ── Step 4: Validate Evidence (Hallucination Control) ─────────────────
        valid_findings, rejected_findings = validate_findings(
            raw_findings=raw_findings,
            repo_directory=repo_directory,
            retrieved_chunks=retrieved_chunks,
        )

        # If no valid findings remain, summarize honestly
        if not valid_findings:
            summary = summary or "No high-confidence bug was identified from the analyzed evidence."

        return {
            "success": True,
            "repository_id": repository_id,
            "query": query,
            "summary": summary,
            "total_findings": len(valid_findings),
            "findings": valid_findings,
            "rejected_findings_count": len(rejected_findings),
            "retrieved_context_count": len(retrieved_chunks),
            "retrieved_chunks": [c.to_dict() for c in retrieved_chunks],
        }


def get_bug_engine() -> BugDetectionEngine:
    return BugDetectionEngine()
