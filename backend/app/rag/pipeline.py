"""
RAG Pipeline Orchestrator — indexing, hybrid retrieval, reranking, and grounded Q&A.

Includes graph-aware retrieval: when a query contains dependency-signal
keywords (e.g. "depends on", "imports", "affected by"), the pipeline
looks up the dependency graph and prepends a structured context block
to the LLM prompt before generation.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.llm.generator import GroundedAnswerGenerator
from app.models.file import File
from app.models.issue import Issue
from app.rag.bm25 import BM25Index
from app.rag.chunker import DocumentChunk, SemanticChunker
from app.rag.embeddings import EmbeddingManager
from app.rag.reranker import CrossEncoderReranker
from app.rag.retriever import HybridRetriever
from app.rag.vector_store import VectorStore

# Lazy import to avoid circular dependency at module load time
# graph_service is only accessed inside async methods
_DEPENDENCY_KEYWORDS = frozenset([
    "depend", "imports", "imported", "affected", "uses", "calls",
    "inherit", "what calls", "what imports", "relies on", "linked to",
    "downstream", "upstream", "breaks", "change",
])

logger = get_logger(__name__)


class RAGPipeline:
    """Orchestrates end-to-end RAG indexing, hybrid search, reranking, and grounded generation."""

    def __init__(self) -> None:
        self.chunker = SemanticChunker()
        self.embedding_manager = EmbeddingManager()
        self.vector_store = VectorStore()
        self.bm25_index = BM25Index()
        self.retriever = HybridRetriever(
            vector_store=self.vector_store,
            bm25_index=self.bm25_index,
            embedding_manager=self.embedding_manager,
        )
        self.reranker = CrossEncoderReranker()
        self.generator = GroundedAnswerGenerator()

    async def index_repository(self, repository_id: UUID, db: AsyncSession) -> int:
        """
        Extract files and issues from DB/disk, chunk documents, generate embeddings,
        and store in ChromaDB & BM25 index.
        """
        repo_id_str = str(repository_id)
        logger.info("Starting RAG indexing for repository", repo_id=repo_id_str)

        chunks: list[DocumentChunk] = []

        # 1. Index files from database
        files_query = await db.execute(
            select(File).where(File.repository_id == repository_id)
        )
        files = list(files_query.scalars().all())

        for file_obj in files:
            # We construct a representative document chunk for indexed file metadata
            source_type = "readme" if file_obj.metadata_ and file_obj.metadata_.get("is_readme") else (
                "documentation" if file_obj.metadata_ and file_obj.metadata_.get("is_documentation") else "code"
            )

            chunk_content = f"// File: {file_obj.path}\n// Language: {file_obj.language or 'Text'}\n// Size: {file_obj.size_bytes} bytes"
            if source_type in ("readme", "documentation"):
                file_chunks = self.chunker.chunk_markdown(chunk_content, file_obj.path, repo_id_str, source_type=source_type)
            else:
                file_chunks = self.chunker.chunk_source_code(chunk_content, file_obj.path, repo_id_str, language=file_obj.language)
            chunks.extend(file_chunks)

        # 2. Index GitHub issues & PRs from database
        issues_query = await db.execute(
            select(Issue).where(Issue.repository_id == repository_id)
        )
        issues = list(issues_query.scalars().all())

        for issue in issues:
            issue_dict = {
                "github_issue_number": issue.github_issue_number,
                "title": issue.title,
                "body": issue.body,
                "author": issue.author,
                "state": issue.state,
                "labels": issue.labels or [],
            }
            chunks.extend(self.chunker.chunk_issue(issue_dict, repo_id_str))

        if not chunks:
            logger.warning("No indexable chunks found for repository", repo_id=repo_id_str)
            return 0

        # 3. Generate embeddings
        texts = [c.content for c in chunks]
        embeddings = self.embedding_manager.embed_texts(texts)

        # 4. Store in ChromaDB & BM25 index
        self.vector_store.add_chunks(repo_id_str, chunks, embeddings)
        self.bm25_index.index_chunks(repo_id_str, chunks)

        logger.info("RAG indexing completed", repo_id=repo_id_str, total_chunks=len(chunks))
        return len(chunks)

    def search(
        self,
        repository_id: str,
        query_text: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Execute hybrid retrieval and cross-encoder reranking.
        """
        # Hybrid retrieval (Dense Vector + BM25 RRF)
        candidates = self.retriever.retrieve(
            repository_id=repository_id,
            query_text=query_text,
            top_k=20,
            filters=filters,
        )

        # Cross-Encoder reranking
        reranked = self.reranker.rerank(
            query_text=query_text,
            candidates=candidates,
            top_k=top_k,
        )

        return reranked

    def ask_question(
        self,
        repository_id: str,
        query_text: str,
        filters: dict[str, Any] | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Run end-to-end grounded Q&A with citations and hallucination protection.

        When *db* is provided and the query contains dependency-signal keywords,
        graph context is looked up and prepended to the prompt so the LLM can
        ground its answer in real import relationships.
        """
        retrieved_chunks = self.search(
            repository_id=repository_id,
            query_text=query_text,
            top_k=5,
            filters=filters,
        )

        # ── Graph-aware context injection ──────────────────────────────────
        graph_context = ""
        if db is not None and self._is_dependency_query(query_text):
            try:
                from app.services.graph_service import graph_service  # noqa: PLC0415
                import asyncio
                # Extract file paths from retrieved chunks to focus the graph lookup
                file_paths = list({
                    chunk.file_path
                    for chunk, _ in retrieved_chunks
                    if chunk.file_path
                })
                repo_uuid = UUID(repository_id) if isinstance(repository_id, str) else repository_id
                # Run in current event loop or fall back silently
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We are inside an async context — schedule as a task
                    import concurrent.futures
                    future = asyncio.ensure_future(
                        graph_service.build_graph_context_text(repo_uuid, file_paths, db)
                    )
                    graph_context = ""
                else:
                    graph_context = loop.run_until_complete(
                        graph_service.build_graph_context_text(repo_uuid, file_paths, db)
                    )
            except Exception as exc:
                logger.debug("Graph context injection skipped", reason=str(exc))

        enriched_query = query_text
        if graph_context:
            enriched_query = f"{graph_context}\n\nUser Query: {query_text}"
            logger.info("Graph context injected into RAG prompt", chars=len(graph_context))

        return self.generator.generate_answer(enriched_query, retrieved_chunks)

    @staticmethod
    def _is_dependency_query(query: str) -> bool:
        """Lightweight keyword check to detect dependency-style questions."""
        q = query.lower()
        return any(kw in q for kw in _DEPENDENCY_KEYWORDS)


# Singleton instance
rag_pipeline = RAGPipeline()
