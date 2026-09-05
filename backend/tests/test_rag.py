"""
Comprehensive unit and integration test suite for CodeIntel RAG pipeline.
"""

from __future__ import annotations

import uuid
import pytest

from app.llm.generator import SAFEGUARD_FALLBACK_TEXT, GroundedAnswerGenerator
from app.rag.bm25 import BM25Index, tokenize_code_and_text
from app.rag.chunker import DocumentChunk, SemanticChunker
from app.rag.embeddings import EmbeddingManager
from app.rag.reranker import CrossEncoderReranker
from app.rag.retriever import HybridRetriever
from app.rag.vector_store import VectorStore


def test_semantic_chunker_code():
    """Test line-level semantic code chunking and citation string generation."""
    chunker = SemanticChunker(chunk_size=100, chunk_overlap=10)
    repo_id = str(uuid.uuid4())
    code = (
        "def authenticate_user(username, password):\n"
        "    if not username or not password:\n"
        "        return False\n"
        "    return True\n"
    )

    chunks = chunker.chunk_source_code(code, "auth/service.py", repo_id, language="Python")
    assert len(chunks) > 0
    c0 = chunks[0]
    assert c0.file_path == "auth/service.py"
    assert c0.start_line == 1
    assert c0.end_line == 4
    assert c0.symbol_name == "authenticate_user"
    assert c0.citation_str == "auth/service.py:1-4"


def test_semantic_chunker_markdown_and_issue():
    """Test chunking markdown docs and GitHub issues."""
    chunker = SemanticChunker()
    repo_id = str(uuid.uuid4())

    md_content = "# Overview\nThis is system documentation.\n## Setup\nRun docker compose up.\n"
    md_chunks = chunker.chunk_markdown(md_content, "docs/setup.md", repo_id)
    assert len(md_chunks) >= 1
    assert md_chunks[0].source_type == "documentation"

    issue_data = {
        "github_issue_number": 42,
        "title": "Auth token expiration bug",
        "body": "Tokens expire prematurely.",
        "author": "dev",
        "state": "open",
        "labels": ["bug"],
        "is_pull_request": False,
    }
    issue_chunks = chunker.chunk_issue(issue_data, repo_id)
    assert len(issue_chunks) == 1
    assert issue_chunks[0].source_type == "issue"
    assert issue_chunks[0].citation_str == "issues/issue_42.md:1-4"


def test_bm25_tokenization_and_search():
    """Test code-aware tokenization and BM25 keyword matching."""
    tokens = tokenize_code_and_text("def authenticateUser_v2(user_name): pass")
    assert "authenticateuser" in tokens or "user" in tokens
    assert "name" in tokens or "user_name" in tokens

    bm25 = BM25Index()
    repo_id = str(uuid.uuid4())
    chunk1 = DocumentChunk(
        id="c1",
        repository_id=repo_id,
        file_path="auth.py",
        start_line=1,
        end_line=10,
        content="def authenticate_user(): pass",
        source_type="code",
    )
    chunk2 = DocumentChunk(
        id="c2",
        repository_id=repo_id,
        file_path="db.py",
        start_line=1,
        end_line=10,
        content="def connect_database(): pass",
        source_type="code",
    )

    bm25.index_chunks(repo_id, [chunk1, chunk2])
    results = bm25.query_bm25(repo_id, "authenticate_user")
    assert len(results) >= 1
    assert results[0][0].id == "c1"


def test_vector_store_and_embeddings():
    """Test vector storage, cosine similarity search, and metadata filtering."""
    store = VectorStore()
    repo_id = str(uuid.uuid4())
    embedder = EmbeddingManager()

    chunk1 = DocumentChunk(
        id="c1",
        repository_id=repo_id,
        file_path="auth.py",
        start_line=1,
        end_line=10,
        content="def authenticate_user(): pass",
        source_type="code",
        language="Python",
    )
    chunk2 = DocumentChunk(
        id="c2",
        repository_id=repo_id,
        file_path="docs.md",
        start_line=1,
        end_line=5,
        content="Documentation about deployment.",
        source_type="documentation",
        language="Markdown",
    )

    embeddings = embedder.embed_texts([chunk1.content, chunk2.content])
    store.add_chunks(repo_id, [chunk1, chunk2], embeddings)

    # Filter by source_type='code'
    q_vector = embedder.embed_query("authenticate")
    res = store.query_vectors(repo_id, q_vector, top_k=5, filters={"source_type": "code"})
    assert len(res) == 1
    assert res[0][0].file_path == "auth.py"


def test_hybrid_retrieval_and_rrf():
    """Test hybrid dense + BM25 retrieval with RRF rank fusion."""
    store = VectorStore()
    bm25 = BM25Index()
    embedder = EmbeddingManager()
    repo_id = str(uuid.uuid4())

    chunk = DocumentChunk(
        id="c1",
        repository_id=repo_id,
        file_path="api.py",
        start_line=1,
        end_line=5,
        content="fastapi endpoint handler",
        source_type="code",
    )
    embeddings = embedder.embed_texts([chunk.content])
    store.add_chunks(repo_id, [chunk], embeddings)
    bm25.index_chunks(repo_id, [chunk])

    retriever = HybridRetriever(store, bm25, embedder)
    results = retriever.retrieve(repo_id, "fastapi endpoint")
    assert len(results) >= 1
    assert results[0][0].id == "c1"


def test_hallucination_protection_safeguard():
    """Test hallucination safeguard when retrieval confidence is below SIMILARITY_THRESHOLD."""
    generator = GroundedAnswerGenerator(threshold=0.85)

    # 1. Empty retrieval results
    res_empty = generator.generate_answer("What is X?", [])
    assert res_empty["answer"] == SAFEGUARD_FALLBACK_TEXT
    assert res_empty["confidence"] == 0.0
    assert not res_empty["is_grounded"]

    # 2. Low confidence retrieval result (below 0.85 threshold)
    low_chunk = DocumentChunk(
        id="c1",
        repository_id="repo1",
        file_path="unrelated.py",
        start_line=1,
        end_line=5,
        content="print('unrelated')",
        source_type="code",
    )
    res_low = generator.generate_answer("What is X?", [(low_chunk, 0.20)])
    assert res_low["answer"] == SAFEGUARD_FALLBACK_TEXT
    assert res_low["confidence"] == 0.20
    assert not res_low["is_grounded"]


def test_citation_preservation_and_formatting():
    """Test citation formatting preservation [auth/service.py:42-78]."""
    generator = GroundedAnswerGenerator(threshold=0.10)
    chunk = DocumentChunk(
        id="c1",
        repository_id="repo1",
        file_path="auth/service.py",
        start_line=42,
        end_line=78,
        content="def refresh_jwt_token(): pass",
        source_type="code",
    )

    res = generator.generate_answer("refresh jwt token", [(chunk, 0.95)])
    assert res["is_grounded"]
    assert len(res["citations"]) == 1
    assert res["citations"][0]["citation"] == "auth/service.py:42-78"
    assert "auth/service.py:42-78" in res["answer"]
