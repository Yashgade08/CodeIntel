"""
V1 API router — aggregates all endpoint routers.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import chat, health, issues, rag, repositories, risk, graph, evaluation

router = APIRouter()

# Health checks (no prefix — mounted at /api/v1/health)
router.include_router(health.router)

# Resource endpoints
router.include_router(repositories.router)
router.include_router(rag.router)
router.include_router(chat.router)
router.include_router(issues.router)
router.include_router(risk.router)
router.include_router(graph.router)
router.include_router(evaluation.router)
