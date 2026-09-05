"""
Graph persistence — save and load the serialized dependency graph
inside the repository's JSONB metadata_ column.

This avoids any new schema migration: the graph is stored under:
    repository.metadata_["dependency_graph"]

For very large repositories (> ~50 k nodes/edges) a separate table
can be added in a future migration.
"""

from __future__ import annotations

import datetime
from uuid import UUID

import networkx as nx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.graph.serializer import GraphSerializer
from app.models.repository import Repository

logger = get_logger(__name__)

_GRAPH_KEY = "dependency_graph"
_serializer = GraphSerializer()


class GraphStore:
    """Async persistence layer for repository dependency graphs."""

    async def save(
        self,
        repository_id: UUID,
        graph: nx.DiGraph,
        db: AsyncSession,
    ) -> None:
        """
        Serialise *graph* and upsert it into ``repositories.metadata_``.

        The operation is a JSON merge: existing metadata_ keys are preserved.
        """
        graph_dict = _serializer.to_storage_dict(graph)
        graph_dict["built_at"] = datetime.datetime.utcnow().isoformat() + "Z"

        # Fetch current metadata_ so we can merge rather than overwrite
        result = await db.execute(
            select(Repository.metadata_).where(Repository.id == repository_id)
        )
        row = result.scalar_one_or_none()
        existing_meta: dict = dict(row) if row else {}
        existing_meta[_GRAPH_KEY] = graph_dict

        await db.execute(
            update(Repository)
            .where(Repository.id == repository_id)
            .values(metadata_=existing_meta)
        )
        await db.commit()
        logger.info(
            "Dependency graph persisted",
            repo_id=str(repository_id),
            nodes=graph.number_of_nodes(),
            edges=graph.number_of_edges(),
        )

    async def load(
        self,
        repository_id: UUID,
        db: AsyncSession,
    ) -> nx.DiGraph | None:
        """
        Load and deserialise the dependency graph for *repository_id*.

        Returns ``None`` if no graph has been built yet.
        """
        result = await db.execute(
            select(Repository.metadata_).where(Repository.id == repository_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None

        meta: dict = dict(row) if row else {}
        graph_dict = meta.get(_GRAPH_KEY)
        if not graph_dict:
            return None

        try:
            return GraphSerializer.from_dict(graph_dict)
        except Exception as exc:
            logger.error("Failed to deserialise dependency graph", error=str(exc))
            return None

    async def get_stats(
        self,
        repository_id: UUID,
        db: AsyncSession,
    ) -> dict | None:
        """Return only the stats portion of the stored graph without loading the full DiGraph."""
        result = await db.execute(
            select(Repository.metadata_).where(Repository.id == repository_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        meta: dict = dict(row) if row else {}
        graph_dict = meta.get(_GRAPH_KEY)
        return graph_dict.get("stats") if graph_dict else None
