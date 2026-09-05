"""
Code Retrieval Layer

Performs isolated, similarity-based retrieval of relevant code chunks from ChromaDB,
with support for multi-step contextual enrichment and strict repository validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.factory import get_embedding_provider
from app.vectorstore.chroma_store import ChromaVectorStore, get_vector_store


@dataclass
class RetrievedChunk:
    chunk_id: str
    repository_id: str
    repository: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    content: str
    similarity: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "repository_id": self.repository_id,
            "repository": self.repository,
            "file_path": self.file_path,
            "language": self.language,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content": self.content,
            "similarity": round(self.similarity, 4),
        }


class CodeRetriever:
    """
    Retrieval engine for repository code chunks.
    """

    def __init__(
        self,
        vector_store: ChromaVectorStore | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.vector_store = vector_store or get_vector_store()
        self.embedding_provider = embedding_provider or get_embedding_provider()

    def retrieve(
        self,
        repository_id: str,
        query: str,
        top_k: int | None = None,
        multi_step: bool = True,
    ) -> list[RetrievedChunk]:
        """
        Retrieve top-K relevant code chunks for a specific repository.
        """
        settings = get_settings()
        limit = top_k or settings.TOP_K

        # ── Step 1: Embed User Query ─────────────────────────────────────────
        query_embedding = self.embedding_provider.embed_query(query)
        if not query_embedding:
            return []

        # ── Step 2: Query ChromaDB with mandatory repository filter ──────────
        raw_results = self.vector_store.query(
            query_embedding=query_embedding,
            repository_id=repository_id,
            top_k=limit,
        )

        chunks: list[RetrievedChunk] = []
        seen_ids: set[str] = set()

        for r in raw_results:
            # Enforce repository isolation
            if r["repository_id"] != repository_id:
                raise ValueError(f"REPOSITORY_ISOLATION_FAILURE: Chunk {r['chunk_id']} is from {r['repository_id']}")

            if r["chunk_id"] not in seen_ids:
                seen_ids.add(r["chunk_id"])
                chunks.append(
                    RetrievedChunk(
                        chunk_id=r["chunk_id"],
                        repository_id=r["repository_id"],
                        repository=r["repository"],
                        file_path=r["file_path"],
                        language=r["language"],
                        start_line=r["start_line"],
                        end_line=r["end_line"],
                        content=r["content"],
                        similarity=r["similarity"],
                    )
                )

        # ── Step 3: Multi-Step Retrieval (Targeted Symbol Enrichment) ─────────
        if multi_step and chunks and len(chunks) < (limit + 4):
            # Extract key referenced function/class names from top results
            symbols_to_expand: set[str] = set()
            for chunk in chunks[:3]:
                # Look for calls or imports e.g., auth_service.verify_token
                func_calls = re.findall(r"\b([a-zA-Z0-9_]{4,})\s*\(", chunk.content)
                for f in func_calls:
                    if f not in ("print", "return", "range", "len", "self", "str", "int", "dict", "list", "tuple", "super"):
                        symbols_to_expand.add(f)

            # Query for the top distinct symbol if any
            for sym in list(symbols_to_expand)[:2]:
                sym_query = f"definition of {sym}"
                sym_emb = self.embedding_provider.embed_query(sym_query)
                sym_results = self.vector_store.query(
                    query_embedding=sym_emb,
                    repository_id=repository_id,
                    top_k=2,
                )
                for sr in sym_results:
                    if sr["chunk_id"] not in seen_ids and sr["repository_id"] == repository_id:
                        seen_ids.add(sr["chunk_id"])
                        chunks.append(
                            RetrievedChunk(
                                chunk_id=sr["chunk_id"],
                                repository_id=sr["repository_id"],
                                repository=sr["repository"],
                                file_path=sr["file_path"],
                                language=sr["language"],
                                start_line=sr["start_line"],
                                end_line=sr["end_line"],
                                content=sr["content"],
                                similarity=sr["similarity"],
                            )
                        )

        # Sort descending by similarity
        chunks.sort(key=lambda x: x.similarity, reverse=True)
        return chunks[:limit]


def get_code_retriever() -> CodeRetriever:
    """Helper getter for CodeRetriever."""
    return CodeRetriever()
