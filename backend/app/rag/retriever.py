"""
Hybrid Retriever combining Dense Vector Search and Sparse BM25 Search using Reciprocal Rank Fusion (RRF).
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.bm25 import BM25Index
from app.rag.chunker import DocumentChunk
from app.rag.embeddings import EmbeddingManager
from app.rag.vector_store import VectorStore

logger = get_logger(__name__)


class HybridRetriever:
    """Combines Dense Vector Retrieval and Sparse BM25 Keyword Search using RRF."""

    def __init__(
        self,
        vector_store: VectorStore,
        bm25_index: BM25Index,
        embedding_manager: EmbeddingManager,
        vector_weight: float = 1.0,
        bm25_weight: float = 1.0,
        rrf_k: int = 60,
    ) -> None:
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.embedding_manager = embedding_manager
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.rrf_k = rrf_k

    def retrieve(
        self,
        repository_id: str,
        query_text: str,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Execute hybrid retrieval with Reciprocal Rank Fusion (RRF).
        
        Returns top-k candidate chunks with fused relevance scores.
        """
        settings = get_settings()
        k_retrieve = top_k or settings.TOP_K_RETRIEVAL
        filters = filters or {}

        # 1. Dense Vector Search
        query_vector = self.embedding_manager.embed_query(query_text)
        vector_results = self.vector_store.query_vectors(
            repository_id=repository_id,
            query_vector=query_vector,
            top_k=k_retrieve,
            filters=filters,
        )

        # 2. Sparse BM25 Keyword Search
        bm25_results = self.bm25_index.query_bm25(
            repository_id=repository_id,
            query_text=query_text,
            top_k=k_retrieve,
            filters=filters,
        )

        # 3. Reciprocal Rank Fusion (RRF)
        fused_scores: dict[str, float] = {}
        chunk_map: dict[str, DocumentChunk] = {}

        # Rank vector candidates
        for rank, (chunk, _) in enumerate(vector_results, start=1):
            chunk_map[chunk.id] = chunk
            fused_scores[chunk.id] = fused_scores.get(chunk.id, 0.0) + (
                self.vector_weight / (self.rrf_k + rank)
            )

        # Rank BM25 candidates
        for rank, (chunk, _) in enumerate(bm25_results, start=1):
            chunk_map[chunk.id] = chunk
            fused_scores[chunk.id] = fused_scores.get(chunk.id, 0.0) + (
                self.bm25_weight / (self.rrf_k + rank)
            )

        # Sort candidate chunks by fused RRF score
        fused_results = [
            (chunk_map[cid], score)
            for cid, score in sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        ]

        logger.info(
            "Hybrid retrieval completed",
            repo_id=repository_id,
            vector_candidates=len(vector_results),
            bm25_candidates=len(bm25_results),
            fused_total=len(fused_results),
        )

        return fused_results[:k_retrieve]
