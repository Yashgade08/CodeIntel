"""
Dependency Graph API endpoints.

GET /api/repositories/{id}/graph
    Full serialized dependency graph (nodes + edges + stats).

GET /api/repositories/{id}/dependencies/{file_path}
    What does this file import? (direct + transitive)

GET /api/repositories/{id}/dependents/{file_path}
    What imports this file? + transitive impact set.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.api.deps import get_db_session
from app.schemas import GraphFileResponse, GraphNode, GraphEdge, GraphStats, RepositoryGraphResponse
from app.services.graph_service import graph_service

logger = get_logger(__name__)

router = APIRouter(prefix="/repositories", tags=["Dependency Graph"])


# ── GET /repositories/{id}/graph ───────────────────────────────────────────────

@router.get(
    "/{repository_id}/graph",
    response_model=RepositoryGraphResponse,
    summary="Full dependency graph for a repository",
    description=(
        "Returns the complete directed dependency graph built from static "
        "import analysis. Nodes represent files, external modules, classes, "
        "and functions. Edges represent import / inheritance relationships."
    ),
)
async def get_repository_graph(
    repository_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> RepositoryGraphResponse:
    graph_dict = await graph_service.get_graph_dict(repository_id, db)

    if graph_dict is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Dependency graph has not been built yet for this repository. "
                "Trigger ingestion first to generate the graph."
            ),
        )

    # Coerce raw dicts to Pydantic models (extra fields are ignored)
    nodes = [GraphNode(**n) for n in graph_dict.get("nodes", [])]
    edges = [GraphEdge(**e) for e in graph_dict.get("edges", [])]
    stats_dict = graph_dict.get("stats", {})
    stats = GraphStats(**stats_dict)

    return RepositoryGraphResponse(
        repository_id=repository_id,
        nodes=nodes,
        edges=edges,
        stats=stats,
        built_at=graph_dict.get("built_at"),
    )


# ── GET /repositories/{id}/dependencies/{file_path} ────────────────────────────

@router.get(
    "/{repository_id}/dependencies/{file_path:path}",
    response_model=GraphFileResponse,
    summary="What does this file depend on?",
    description=(
        "Returns files and modules that the given file imports, "
        "up to the specified traversal depth."
    ),
)
async def get_file_dependencies(
    repository_id: UUID,
    file_path: str,
    depth: int = Query(default=2, ge=1, le=10, description="Traversal depth (hops)"),
    include_external: bool = Query(default=False, description="Include external package nodes"),
    db: AsyncSession = Depends(get_db_session),
) -> GraphFileResponse:
    logger.info(
        "Fetching file dependencies",
        repo_id=str(repository_id),
        file=file_path,
        depth=depth,
    )
    result = await graph_service.get_file_dependencies(
        repository_id, file_path, db, depth=depth, include_external=include_external
    )

    message = result.get("message")
    if message and not result["results"]:
        logger.warning("No dependency graph available", file=file_path, message=message)

    return GraphFileResponse(**result)


# ── GET /repositories/{id}/dependents/{file_path} ──────────────────────────────

@router.get(
    "/{repository_id}/dependents/{file_path:path}",
    response_model=GraphFileResponse,
    summary="What depends on this file?",
    description=(
        "Returns files that import the given file (reverse dependency direction). "
        "Also returns the full transitive impact set — all files that could be "
        "affected if this file changes."
    ),
)
async def get_file_dependents(
    repository_id: UUID,
    file_path: str,
    depth: int = Query(default=2, ge=1, le=10, description="Traversal depth (hops)"),
    db: AsyncSession = Depends(get_db_session),
) -> GraphFileResponse:
    logger.info(
        "Fetching file dependents",
        repo_id=str(repository_id),
        file=file_path,
        depth=depth,
    )
    result = await graph_service.get_file_dependents(
        repository_id, file_path, db, depth=depth
    )
    return GraphFileResponse(**result)
