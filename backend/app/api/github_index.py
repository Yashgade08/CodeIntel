"""
POST /api/github/repositories/{repository_id}/index

Indexes all relevant source code files of a cloned repository into ChromaDB
using structure-aware chunking and deterministic embeddings.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.chunking.code_chunker import chunk_repository_files
from app.embeddings.factory import get_embedding_provider
from app.scanner.source_scanner import scan_source_files
from app.vectorstore.chroma_store import get_vector_store

router = APIRouter(prefix="/api/github", tags=["github-indexing"])

WORKSPACE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "workspace"


class IndexResponse(BaseModel):
    success: bool
    repository_id: str | None = None
    status: str | None = None
    files_processed: int = 0
    chunks_created: int = 0
    embeddings_created: int = 0
    error: dict | None = None


@router.post("/repositories/{repository_id}/index")
def index_repository(repository_id: str) -> dict:
    """
    Index cloned repository source files into ChromaDB vector database.
    """
    clean_id = (repository_id or "").strip()
    if not clean_id or not re.match(r"^[a-zA-Z0-9_\-\.]+$", clean_id) or ".." in clean_id:
        return {
            "success": False,
            "error": {
                "code": "INVALID_REPOSITORY_ID",
                "layer": "indexing",
                "message": "Invalid repository workspace identifier.",
                "root_cause": f"Repository identifier '{clean_id}' contains illegal characters or path traversal elements.",
                "fix": "Provide a valid repository identifier returned from the clone operation.",
            },
        }

    resolved_base = WORKSPACE_BASE_DIR.resolve()
    target_dir = (resolved_base / clean_id).resolve()

    if target_dir.parent != resolved_base:
        return {
            "success": False,
            "error": {
                "code": "INVALID_REPOSITORY_ID",
                "layer": "indexing",
                "message": "Path traversal attempt detected.",
                "root_cause": "The requested repository path escapes the designated workspace directory.",
                "fix": "Only access repositories managed inside the application workspace.",
            },
        }

    if not target_dir.exists() or not target_dir.is_dir():
        return {
            "success": False,
            "error": {
                "code": "CLONE_DIRECTORY_NOT_FOUND",
                "layer": "indexing",
                "message": f"Cloned repository directory '{clean_id}' does not exist.",
                "root_cause": f"No cloned directory exists at workspace path: {target_dir}",
                "fix": "Ensure the repository has been cloned before attempting indexing.",
            },
        }

    # ── Step 1: Scan Source Files ─────────────────────────────────────────
    try:
        source_files = scan_source_files(target_dir)
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "FILESYSTEM_READ_ERROR",
                "layer": "scanner",
                "message": "Failed to scan repository source files.",
                "root_cause": str(e),
                "fix": "Check filesystem read permissions for the workspace directory.",
            },
        }

    if not source_files:
        return {
            "success": True,
            "repository_id": clean_id,
            "status": "COMPLETED",
            "files_processed": 0,
            "chunks_created": 0,
            "embeddings_created": 0,
            "message": "No supported source code files found to index.",
        }

    # ── Step 2: Structure-Aware Chunking ──────────────────────────────────
    repo_name = clean_id
    try:
        chunks = chunk_repository_files(source_files, clean_id, repo_name)
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "CHUNKING_FAILED",
                "layer": "chunker",
                "message": "Failed to chunk repository source code.",
                "root_cause": str(e),
                "fix": "Verify that the source files are valid text files.",
            },
        }

    if not chunks:
        return {
            "success": True,
            "repository_id": clean_id,
            "status": "COMPLETED",
            "files_processed": len(source_files),
            "chunks_created": 0,
            "embeddings_created": 0,
        }

    # ── Step 3: Generate Embeddings ───────────────────────────────────────
    try:
        embedding_provider = get_embedding_provider()
        chunk_texts = [c.content for c in chunks]
        embeddings = embedding_provider.embed_documents(chunk_texts)
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "EMBEDDING_FAILED",
                "layer": "embeddings",
                "message": "Failed to generate vector embeddings for code chunks.",
                "root_cause": str(e),
                "fix": "Check embedding provider configuration and model availability.",
            },
        }

    # ── Step 4: Persist in ChromaDB ───────────────────────────────────────
    try:
        vector_store = get_vector_store()
        upserted_count = vector_store.upsert_chunks(chunks, embeddings)
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "CHROMADB_PERSISTENCE_FAILED",
                "layer": "vectorstore",
                "message": "Failed to store vectors in ChromaDB.",
                "root_cause": str(e),
                "fix": "Check ChromaDB persistence directory and write permissions.",
            },
        }

    return {
        "success": True,
        "repository_id": clean_id,
        "status": "COMPLETED",
        "files_processed": len(source_files),
        "chunks_created": len(chunks),
        "embeddings_created": upserted_count,
    }
