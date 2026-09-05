"""
Cross-Encoder reranker for high-precision query-document relevance scoring.
"""

from __future__ import annotations

import re
from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.chunker import DocumentChunk

logger = get_logger(__name__)


class CrossEncoderReranker:
    """Reranks candidate document chunks using a Cross-Encoder model."""

    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.RERANKER_MODEL
        self._model = None

    def _load_model(self) -> None:
        if self._model is not None:
            return

        try:
            from sentence_transformers import CrossEncoder
            logger.info("Loading CrossEncoder model", model=self.model_name)
            self._model = CrossEncoder(self.model_name)
        except Exception as e:
            logger.warning(
                "Could not load CrossEncoder model, using fallback lexical reranker",
                error=str(e),
            )
            self._model = "fallback"

    def rerank(
        self,
        query_text: str,
        candidates: list[tuple[DocumentChunk, float]],
        top_k: int | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Rerank hybrid retrieval candidate chunks.
        
        Returns top-k reranked (DocumentChunk, score) tuples sorted by descending relevance.
        """
        if not candidates:
            return []

        settings = get_settings()
        k_final = top_k or settings.TOP_K_FINAL
        chunks = [c for c, _ in candidates]

        self._load_model()

        if self._model != "fallback":
            try:
                pairs = [[query_text, c.content] for c in chunks]
                scores = self._model.predict(pairs)
                
                # Normalize scores to [0.0, 1.0] range using sigmoid / min-max normalization
                scored_results = []
                for chunk, raw_score in zip(chunks, scores):
                    # Sigmoid transform: 1 / (1 + exp(-score))
                    import math
                    norm_score = 1.0 / (1.0 + math.exp(-float(raw_score)))
                    scored_results.append((chunk, norm_score))

                scored_results.sort(key=lambda x: x[1], reverse=True)
                return scored_results[:k_final]

            except Exception as e:
                logger.error("CrossEncoder inference error, falling back to lexical reranker", error=str(e))

        # Fallback lexical reranker
        scored_results = []
        q_tokens = set(re.findall(r"\w+", query_text.lower()))

        for chunk, initial_score in candidates:
            c_tokens = set(re.findall(r"\w+", chunk.content.lower()))
            overlap = len(q_tokens & c_tokens) / max(1, len(q_tokens))
            combined_score = (initial_score * 0.4) + (overlap * 0.6)
            scored_results.append((chunk, combined_score))

        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results[:k_final]
