"""
ChromaDB Persistent Vector Store

Manages persistent vector indexing and similarity retrieval in ChromaDB with
mandatory repository isolation.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb

from app.chunking.code_chunker import CodeChunk
from app.core.config import get_settings


class ChromaVectorStore:
    """
    Persistent ChromaDB wrapper for code chunk storage and isolated similarity queries.
    """

    COLLECTION_NAME = "code_chunks"

    def __init__(self, persist_directory: str | Path | None = None):
        settings = get_settings()
        if persist_directory is None:
            # Resolve relative to backend folder
            persist_directory = Path(__file__).resolve().parent.parent.parent / "data" / "chroma"
        else:
            persist_directory = Path(persist_directory)

        persist_directory.mkdir(parents=True, exist_ok=True)
        self.persist_directory = str(persist_directory)

        self._client = chromadb.PersistentClient(path=self.persist_directory)
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(
        self,
        chunks: list[CodeChunk],
        embeddings: list[list[float]],
        batch_size: int = 250,
    ) -> int:
        """
        Upsert code chunks and embedding vectors into ChromaDB using deterministic IDs.
        """
        if not chunks or not embeddings or len(chunks) != len(embeddings):
            return 0

        total_upserted = 0
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]

            ids = [c.chunk_id for c in batch_chunks]
            documents = [c.content for c in batch_chunks]
            metadatas: list[dict[str, Any]] = [
                {
                    "repository_id": c.repository_id,
                    "repository": c.repository,
                    "file_path": c.file_path,
                    "language": c.language,
                    "start_line": int(c.start_line),
                    "end_line": int(c.end_line),
                }
                for c in batch_chunks
            ]

            self._collection.upsert(
                ids=ids,
                embeddings=batch_embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            total_upserted += len(batch_chunks)

        return total_upserted

    def query(
        self,
        query_embedding: list[float],
        repository_id: str,
        top_k: int = 8,
    ) -> list[dict[str, Any]]:
        """
        Query ChromaDB with mandatory repository_id filtering.
        Validates that 100% of returned vectors belong to repository_id.
        """
        if not query_embedding or not repository_id:
            return []

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"repository_id": repository_id},
            include=["documents", "metadatas", "distances"],
        )

        matched_chunks: list[dict[str, Any]] = []

        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        for chunk_id, doc, meta, dist in zip(ids, docs, metas, dists):
            # Strict isolation safeguard: reject any vector not belonging to repository_id
            if meta.get("repository_id") != repository_id:
                raise ValueError(
                    f"REPOSITORY_ISOLATION_FAILURE: Vector {chunk_id} belongs to '{meta.get('repository_id')}' instead of requested '{repository_id}'"
                )

            # Cosine distance to similarity conversion
            similarity = max(0.0, min(1.0, 1.0 - float(dist)))

            matched_chunks.append(
                {
                    "chunk_id": chunk_id,
                    "repository_id": meta.get("repository_id"),
                    "repository": meta.get("repository"),
                    "file_path": meta.get("file_path"),
                    "language": meta.get("language"),
                    "start_line": int(meta.get("start_line", 1)),
                    "end_line": int(meta.get("end_line", 1)),
                    "content": doc,
                    "similarity": similarity,
                }
            )

        return matched_chunks

    def count_by_repository(self, repository_id: str) -> int:
        """Count total vectors indexed for a specific repository."""
        res = self._collection.get(
            where={"repository_id": repository_id},
            include=[],
        )
        return len(res.get("ids", []))


@lru_cache(maxsize=1)
def get_vector_store() -> ChromaVectorStore:
    """Singleton getter for the persistent ChromaVectorStore."""
    return ChromaVectorStore()
