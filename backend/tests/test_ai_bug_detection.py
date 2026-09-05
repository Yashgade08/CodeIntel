"""
Automated Test Suite for AI Bug Detection & RAG Pipeline

Verifies:
1. Source file scanning with exclusions and language detection.
2. Structure-aware code chunking with precise line numbers and deterministic IDs.
3. ChromaDB persistent storage and strict repository isolation.
4. Semantic code retrieval and multi-step expansion.
5. Hallucination control and evidence validation.
6. End-to-end bug detection on the deliberately buggy test repository.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.bug_detection.engine import BugDetectionEngine
from app.bug_detection.validator import validate_findings
from app.chunking.code_chunker import chunk_repository_files
from app.embeddings.factory import get_embedding_provider
from app.llm.base import LLMProvider
from app.main import app
from app.retrieval.code_retriever import CodeRetriever, RetrievedChunk
from app.scanner.source_scanner import scan_source_files
from app.vectorstore.chroma_store import ChromaVectorStore

client = TestClient(app)

BUGGY_REPO_DIR = Path(__file__).resolve().parent / "fixtures" / "buggy_repo"


def test_source_scanner_supported_files():
    """Verify source scanner finds supported code files and skips non-code."""
    files = scan_source_files(BUGGY_REPO_DIR)
    assert len(files) >= 3

    paths = [f.file_path for f in files]
    assert any("auth.py" in p for p in paths)
    assert any("calculator.py" in p for p in paths)
    assert any("db.py" in p for p in paths)

    for f in files:
        assert f.language == "python"
        assert f.extension == ".py"
        assert f.content
        assert f.size_bytes > 0


def test_code_chunker_deterministic():
    """Verify code chunker produces exact line numbers and deterministic chunk IDs."""
    files = scan_source_files(BUGGY_REPO_DIR)
    chunks_run1 = chunk_repository_files(files, "test_repo_123", "owner/repo")
    chunks_run2 = chunk_repository_files(files, "test_repo_123", "owner/repo")

    assert len(chunks_run1) > 0
    assert len(chunks_run1) == len(chunks_run2)

    # Verify deterministic IDs across runs
    ids_1 = [c.chunk_id for c in chunks_run1]
    ids_2 = [c.chunk_id for c in chunks_run2]
    assert ids_1 == ids_2

    # Verify line numbers
    for chunk in chunks_run1:
        assert chunk.start_line >= 1
        assert chunk.end_line >= chunk.start_line
        assert chunk.repository_id == "test_repo_123"
        assert chunk.file_path
        assert chunk.content.strip()


def test_chroma_store_upsert_and_isolation():
    """Verify ChromaDB stores chunks and enforces strict repository isolation."""
    vector_store = ChromaVectorStore()
    embedding_provider = get_embedding_provider()

    # Index Repo A (buggy repo)
    files = scan_source_files(BUGGY_REPO_DIR)
    chunks_a = chunk_repository_files(files, "isolation_repo_AAA", "test/repo_a")
    emb_a = embedding_provider.embed_documents([c.content for c in chunks_a])
    vector_store.upsert_chunks(chunks_a, emb_a)

    # Index Repo B (dummy)
    chunks_b = chunk_repository_files(files, "isolation_repo_BBB", "test/repo_b")
    emb_b = embedding_provider.embed_documents([c.content for c in chunks_b])
    vector_store.upsert_chunks(chunks_b, emb_b)

    # Query Repo A
    query_emb = embedding_provider.embed_query("division by zero calculation")
    res_a = vector_store.query(query_emb, repository_id="isolation_repo_AAA", top_k=5)

    assert len(res_a) > 0
    for r in res_a:
        assert r["repository_id"] == "isolation_repo_AAA"
        assert r["repository_id"] != "isolation_repo_BBB"

    # Query Repo B
    res_b = vector_store.query(query_emb, repository_id="isolation_repo_BBB", top_k=5)
    assert len(res_b) > 0
    for r in res_b:
        assert r["repository_id"] == "isolation_repo_BBB"
        assert r["repository_id"] != "isolation_repo_AAA"


def test_code_retriever_semantic_match():
    """Verify semantic retrieval finds the relevant file."""
    retriever = CodeRetriever()
    # Retrieve auth related code from indexed test repo
    results = retriever.retrieve(
        repository_id="test_buggy_repo_1000000000_000000",
        query="verify_token and user authentication bypass",
        top_k=3,
    )

    assert len(results) > 0
    top_file = results[0].file_path
    assert "auth.py" in top_file
    assert "token" in results[0].content


def test_hallucination_validator():
    """Verify validator drops or flags non-existent files and invalid line numbers."""
    dummy_chunks = [
        RetrievedChunk(
            chunk_id="chk1",
            repository_id="test_repo",
            repository="owner/repo",
            file_path="src/auth.py",
            language="python",
            start_line=1,
            end_line=20,
            content="def verify_token(token): pass",
            similarity=0.9,
        )
    ]

    test_findings = [
        # Valid finding
        {
            "title": "Token None bypass",
            "severity": "HIGH",
            "confidence": 0.9,
            "category": "security",
            "file_path": "src/auth.py",
            "start_line": 5,
            "end_line": 8,
            "description": "Returns True when token is None",
            "root_cause": "if token is None: return True",
            "impact": "Authentication bypass",
            "suggested_fix": "return False if token is None",
        },
        # Hallucinated file
        {
            "title": "Fake file bug",
            "severity": "HIGH",
            "confidence": 0.9,
            "category": "security",
            "file_path": "src/non_existent_file.py",
            "start_line": 1,
            "end_line": 10,
            "description": "Hallucinated",
            "root_cause": "N/A",
            "impact": "N/A",
            "suggested_fix": "N/A",
        },
        # Out of bounds line range
        {
            "title": "Out of bounds bug",
            "severity": "HIGH",
            "confidence": 0.9,
            "category": "logic_error",
            "file_path": "src/auth.py",
            "start_line": 99999,
            "end_line": 999999,
            "description": "Hallucinated line numbers",
            "root_cause": "N/A",
            "impact": "N/A",
            "suggested_fix": "N/A",
        },
    ]

    valid, rejected = validate_findings(test_findings, BUGGY_REPO_DIR, dummy_chunks)

    assert len(valid) == 1
    assert valid[0]["file_path"] == "src/auth.py"
    assert valid[0]["validation_status"] == "VERIFIED"

    assert len(rejected) == 2
    for rej in rejected:
        assert rej["validation_status"] == "INVALID_EVIDENCE"


class DeterministicBuggyLLM(LLMProvider):
    """Deterministic LLM for testing pipeline end-to-end without external API keys."""

    def generate_analysis(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> dict:
        return {
            "summary": "Identified critical division by zero flaw in calculator service.",
            "findings": [
                {
                    "title": "Division by Zero in divide function",
                    "severity": "HIGH",
                    "confidence": 0.95,
                    "category": "arithmetic_error",
                    "file_path": "src/calculator.py",
                    "start_line": 5,
                    "end_line": 8,
                    "description": "No check for zero divisor b.",
                    "root_cause": "divide(a, b) directly calculates a / b without checking if b == 0.",
                    "impact": "Causes ZeroDivisionError and service crash.",
                    "suggested_fix": "if b == 0: raise ValueError('Cannot divide by zero')\nreturn a / b",
                    "evidence": [{"file_path": "src/calculator.py", "start_line": 5, "end_line": 8}],
                }
            ],
        }


def test_end_to_end_deliberately_buggy_repo_analysis():
    """Verify full end-to-end RAG Bug Detection pipeline with evidence verification."""
    retriever = CodeRetriever()
    test_llm = DeterministicBuggyLLM()
    engine = BugDetectionEngine(retriever=retriever, llm_provider=test_llm)

    result = engine.analyze_repository_bugs(
        repository_id="test_buggy_repo_1000000000_000000",
        repo_directory=BUGGY_REPO_DIR,
        query="Find division by zero and calculation bugs",
    )

    assert result["success"] is True
    assert result["total_findings"] == 1
    assert result["retrieved_context_count"] > 0

    finding = result["findings"][0]
    assert finding["title"] == "Division by Zero in divide function"
    assert finding["severity"] == "HIGH"
    assert finding["file_path"] == "src/calculator.py"
    assert finding["start_line"] == 5
    assert finding["end_line"] == 8
    assert finding["validation_status"] == "VERIFIED"
    assert "ZeroDivisionError" in finding["impact"]
