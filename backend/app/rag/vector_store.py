"""
ChromaDB vector store manager supporting dense vector search and metadata filtering.
"""

from __future__ import annotations

import math
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.chunker import DocumentChunk

logger = get_logger(__name__)


class VectorStore:
    """ChromaDB collection manager for document chunk vector storage."""

    def __init__(self, collection_name: str = "codeintel_chunks") -> None:
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        self._memory_fallback: dict[str, list[dict[str, Any]]] = {}

    def _init_chroma(self) -> None:
        if self._collection is not None:
            return

        settings = get_settings()
        try:
            import chromadb
            # Use ephemeral / persistent Chroma client
            self._client = chromadb.Client()
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB vector store initialized", collection=self.collection_name)
        except Exception as e:
            logger.warning(
                "ChromaDB client unavailable, operating in-memory vector store mode",
                error=str(e),
            )
            self._collection = "fallback"

    def add_chunks(
        self,
        repository_id: str,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> int:
        """
        Store chunks and vector embeddings in vector database.
        """
        if not chunks or not embeddings or len(chunks) != len(embeddings):
            return 0

        self._init_chroma()

        ids = [c.id for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [
            {
                "repository_id": repository_id,
                "file_path": c.file_path,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "source_type": c.source_type,
                "language": c.language or "",
                "symbol_name": c.symbol_name or "",
            }
            for c in chunks
        ]

        # Always populate in-memory fallback store as well
        if repository_id not in self._memory_fallback:
            self._memory_fallback[repository_id] = []

        for chunk, emb, meta in zip(chunks, embeddings, metadatas):
            self._memory_fallback[repository_id].append({
                "chunk": chunk,
                "embedding": emb,
                "metadata": meta,
            })

        if self._collection != "fallback":
            try:
                self._collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                )
                logger.info("Added chunks to ChromaDB", repo_id=repository_id, count=len(chunks))
                return len(chunks)
            except Exception as e:
                logger.error("Error inserting into ChromaDB, using memory store", error=str(e))

        return len(chunks)

    def query_vectors(
        self,
        repository_id: str,
        query_vector: list[float],
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Query vector similarity.
        
        Returns list of (DocumentChunk, similarity_score) tuples sorted by descending score.
        """
        self._init_chroma()
        filters = filters or {}

        # ChromaDB requires $and if there are 2 or more conditions
        where_clauses = [{"repository_id": repository_id}]
        if "file_path" in filters:
            where_clauses.append({"file_path": filters["file_path"]})
        if "language" in filters:
            where_clauses.append({"language": filters["language"]})
        if "source_type" in filters:
            where_clauses.append({"source_type": filters["source_type"]})
        if "symbol_name" in filters:
            where_clauses.append({"symbol_name": filters["symbol_name"]})

        chroma_where: dict[str, Any] = (
            {"$and": where_clauses} if len(where_clauses) > 1 else where_clauses[0]
        )

        if self._collection != "fallback":
            try:
                results = self._collection.query(
                    query_embeddings=[query_vector],
                    n_results=top_k,
                    where=chroma_where,
                    include=["documents", "metadatas", "distances"],
                )

                items: list[tuple[DocumentChunk, float]] = []
                if results and results.get("ids") and results["ids"][0]:
                    ids = results["ids"][0]
                    docs = results["documents"][0]
                    metas = results["metadatas"][0]
                    distances = results["distances"][0]

                    for cid, doc, meta, dist in zip(ids, docs, metas, distances):
                        # Convert cosine distance to similarity score: similarity = 1 - distance
                        similarity = max(0.0, min(1.0, 1.0 - float(dist)))
                        chunk = DocumentChunk(
                            id=cid,
                            repository_id=meta["repository_id"],
                            file_path=meta["file_path"],
                            start_line=int(meta["start_line"]),
                            end_line=int(meta["end_line"]),
                            content=doc,
                            source_type=meta["source_type"],
                            language=meta.get("language") or None,
                            symbol_name=meta.get("symbol_name") or None,
                        )
                        items.append((chunk, similarity))
                return items
            except Exception as e:
                logger.error("ChromaDB query error, using fallback store", error=str(e))

        # Memory store fallback query (cosine similarity)
        items = []
        repo_items = self._memory_fallback.get(repository_id, [])
        for item in repo_items:
            meta = item["metadata"]
            # Apply metadata filters
            if "file_path" in filters and meta.get("file_path") != filters["file_path"]:
                continue
            if "language" in filters and meta.get("language") != filters["language"]:
                continue
            if "source_type" in filters and meta.get("source_type") != filters["source_type"]:
                continue
            if "symbol_name" in filters and meta.get("symbol_name") != filters["symbol_name"]:
                continue

            sim = self._cosine_similarity(query_vector, item["embedding"])
            items.append((item["chunk"], sim))

        items.sort(key=lambda x: x[1], reverse=True)
        return items[:top_k]

    def delete_repository_chunks(self, repository_id: str) -> None:
        """Remove all chunks for a given repository."""
        self._init_chroma()
        if self._collection != "fallback":
            try:
                self._collection.delete(where={"repository_id": repository_id})
            except Exception as e:
                logger.warning("ChromaDB delete exception", error=str(e))

        self._memory_fallback.pop(repository_id, None)

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
