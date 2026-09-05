"""
GraphService — orchestrates import analysis, graph construction,
serialization, and persistence for a repository's dependency graph.

The service answers three types of questions:

  1. What does file X import?          → get_file_dependencies()
  2. What imports file X?              → get_file_dependents()
  3. What files are affected if X changes? → get_impact_analysis()
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import UUID

import networkx as nx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.graph.builder import DependencyGraphBuilder, FileRecord
from app.graph.serializer import GraphSerializer
from app.graph.store import GraphStore
from app.models.file import File

logger = get_logger(__name__)

_builder = DependencyGraphBuilder()
_serializer = GraphSerializer()
_store = GraphStore()

# Configurable limits
_MAX_SOURCE_SIZE_BYTES = int(os.getenv("GRAPH_MAX_FILE_BYTES", str(512 * 1024)))  # 512 KB
_SKIP_EXTENSIONS = {
    ".min.js", ".min.css", ".map", ".lock", ".sum",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".zip", ".gz", ".tar",
}
_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", "vendor",
}


def _should_skip(path: str) -> bool:
    parts = Path(path).parts
    for part in parts[:-1]:
        if part in _SKIP_DIRS:
            return True
    return Path(path).suffix.lower() in _SKIP_EXTENSIONS


class GraphService:
    """High-level service for building and querying repository dependency graphs."""

    # ── Build ──────────────────────────────────────────────────────────────

    async def build_and_store(
        self,
        repository_id: UUID,
        repo_path: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Build the dependency graph from files on disk and persist it.

        Reads source files from the database (for metadata) and from disk
        (for content). Returns the serialized graph dict.
        """
        logger.info("Building dependency graph", repo_id=str(repository_id))

        # Load file records from DB
        result = await db.execute(
            select(File).where(File.repository_id == repository_id)
        )
        db_files: list[File] = list(result.scalars().all())

        file_records: list[FileRecord] = []
        source_map: dict[str, str] = {}

        for f in db_files:
            if _should_skip(f.path):
                continue
            file_records.append(FileRecord(
                path=f.path,
                language=f.language,
                line_count=f.line_count,
                size_bytes=f.size_bytes,
            ))

            # Read source from disk with strict path traversal check
            abs_path = os.path.join(repo_path, f.path)
            try:
                resolved_abs = Path(abs_path).resolve()
                resolved_root = Path(repo_path).resolve()
                if not resolved_abs.is_relative_to(resolved_root):
                    logger.warning("Path traversal attempt blocked in graph file reader", path=f.path)
                    continue

                if os.path.isfile(abs_path) and os.path.getsize(abs_path) <= _MAX_SOURCE_SIZE_BYTES:
                    with open(abs_path, encoding="utf-8", errors="replace") as fh:
                        source_map[f.path] = fh.read()
            except OSError:
                pass  # graph will still have the node, just with no edges

        if not file_records:
            logger.warning("No eligible files for graph construction", repo_id=str(repository_id))
            return {"stats": {}, "nodes": [], "edges": []}

        graph = _builder.build(repo_path, file_records, source_map)
        graph_dict = _serializer.to_storage_dict(graph)

        await _store.save(repository_id, graph, db)
        logger.info("Dependency graph built and stored", repo_id=str(repository_id))
        return graph_dict

    # ── Load / query ───────────────────────────────────────────────────────

    async def get_graph(
        self,
        repository_id: UUID,
        db: AsyncSession,
    ) -> nx.DiGraph | None:
        """Load the persisted graph. Returns None if not yet built."""
        return await _store.load(repository_id, db)

    async def get_graph_dict(
        self,
        repository_id: UUID,
        db: AsyncSession,
    ) -> dict[str, Any] | None:
        """Return the full serialized graph dict, or None."""
        graph = await self.get_graph(repository_id, db)
        if graph is None:
            return None
        return _serializer.to_dict(graph)

    async def get_file_dependencies(
        self,
        repository_id: UUID,
        file_path: str,
        db: AsyncSession,
        depth: int = 2,
        include_external: bool = False,
    ) -> dict[str, Any]:
        """
        Return what *file_path* imports (direct + transitive up to *depth* hops).
        """
        graph = await _store.load(repository_id, db)
        if graph is None:
            return _empty_file_response(file_path, "Graph not yet built for this repository.")

        deps = _builder.get_dependencies(graph, file_path, depth=depth, include_external=include_external)
        return {
            "file_path": file_path,
            "repository_id": str(repository_id),
            "direction": "dependencies",
            "depth": depth,
            "results": deps,
            "total": len(deps),
        }

    async def get_file_dependents(
        self,
        repository_id: UUID,
        file_path: str,
        db: AsyncSession,
        depth: int = 2,
    ) -> dict[str, Any]:
        """
        Return what imports *file_path* (reverse edges, up to *depth* hops).
        Also includes a transitive impact set.
        """
        graph = await _store.load(repository_id, db)
        if graph is None:
            return _empty_file_response(file_path, "Graph not yet built for this repository.")

        dependents = _builder.get_dependents(graph, file_path, depth=depth)
        impact_set = _builder.get_impact_set(graph, file_path, depth=5)

        return {
            "file_path": file_path,
            "repository_id": str(repository_id),
            "direction": "dependents",
            "depth": depth,
            "results": dependents,
            "total": len(dependents),
            "impact_set": impact_set,
            "impact_count": len(impact_set),
        }

    async def get_impact_analysis(
        self,
        repository_id: UUID,
        file_path: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Full impact analysis: dependencies + dependents + transitive impact set.
        Used by the RAG pipeline for graph-aware context injection.
        """
        graph = await _store.load(repository_id, db)
        if graph is None:
            return {}

        deps = _builder.get_dependencies(graph, file_path, depth=2)
        dependents = _builder.get_dependents(graph, file_path, depth=2)
        impact_set = _builder.get_impact_set(graph, file_path, depth=5)

        return {
            "file_path": file_path,
            "dependencies": [d["path"] for d in deps if not d.get("is_external")],
            "dependents": [d["path"] for d in dependents],
            "impact_set": impact_set,
        }

    # ── Graph context summary (for RAG prompt injection) ───────────────────

    async def build_graph_context_text(
        self,
        repository_id: UUID,
        file_paths: list[str],
        db: AsyncSession,
    ) -> str:
        """
        Build a plain-text dependency context block for injection into
        the LLM prompt.  Called by the RAG pipeline when dependency-style
        queries are detected.

        Returns empty string if no graph is available.
        """
        graph = await _store.load(repository_id, db)
        if graph is None:
            return ""

        lines: list[str] = ["[Dependency Context]"]
        for fp in file_paths[:5]:  # limit to avoid huge prompts
            deps = [d["path"] for d in _builder.get_dependencies(graph, fp, depth=1) if not d.get("is_external")]
            dependents = [d["path"] for d in _builder.get_dependents(graph, fp, depth=1)]

            if deps or dependents:
                lines.append(f"\n{fp}:")
                if deps:
                    lines.append(f"  imports: {', '.join(deps)}")
                if dependents:
                    lines.append(f"  imported by: {', '.join(dependents)}")

        if len(lines) == 1:
            return ""  # nothing useful to add
        return "\n".join(lines)


def _empty_file_response(file_path: str, message: str) -> dict[str, Any]:
    return {
        "file_path": file_path,
        "direction": "unknown",
        "depth": 0,
        "results": [],
        "total": 0,
        "message": message,
    }


# Singleton
graph_service = GraphService()
