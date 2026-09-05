"""
Model 3: Semantic Duplicate Issue Detection.
Uses dense semantic embeddings and cosine similarity to detect duplicate GitHub issues.
"""

from __future__ import annotations

import math
from typing import Any

from app.core.logging import get_logger
from app.rag.embeddings import EmbeddingManager

logger = get_logger(__name__)


class DuplicateDetector:
    """Detects duplicate GitHub issues using semantic vector embeddings."""

    VERSION = "duplicate-detector-v1.0.0"

    def __init__(self, embedding_manager: EmbeddingManager | None = None) -> None:
        self.embedding_manager = embedding_manager or EmbeddingManager()

    def find_duplicates(
        self,
        query_title: str,
        query_body: str | None,
        existing_issues: list[dict[str, Any]],
        similarity_threshold: float = 0.65,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Compare target issue against existing repository issues using semantic embeddings.
        
        Returns list of matched duplicate candidates sorted by similarity score.
        """
        if not existing_issues:
            return []

        target_text = f"{query_title}\n{query_body or ''}"
        target_vec = self.embedding_manager.embed_query(target_text)

        corpus_texts = [f"{iss.get('title', '')}\n{iss.get('body') or ''}" for iss in existing_issues]
        corpus_vecs = self.embedding_manager.embed_texts(corpus_texts)

        candidates = []
        for issue_dict, vec in zip(existing_issues, corpus_vecs):
            sim = self._cosine_similarity(target_vec, vec)
            if sim >= similarity_threshold:
                # Classify confidence
                if sim >= 0.85:
                    confidence = "HIGH"
                elif sim >= 0.72:
                    confidence = "MEDIUM"
                else:
                    confidence = "LOW"

                candidates.append({
                    "issue_id": str(issue_dict.get("id", "")),
                    "github_issue_number": issue_dict.get("github_issue_number"),
                    "title": issue_dict.get("title", ""),
                    "similarity_score": round(float(sim), 4),
                    "confidence": confidence,
                })

        candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
        return candidates[:top_k]

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two float vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))
