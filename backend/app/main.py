# CodeIntel FastAPI Application Entry Point (Provider: Groq)

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.api.github_validate import router as github_validate_router
from app.api.github_clone import router as github_clone_router
from app.api.github_files import router as github_files_router
from app.api.github_index import router as github_index_router
from app.api.github_bugs import router as github_bugs_router
from app.api.github_source import router as github_source_router
from app.api.github_graph import router as github_graph_router


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title="CodeIntel",
        version="0.1.0",
        description="GitHub Repository Intelligence & Codebase Copilot",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=ORJSONResponse,
    )

    # ── Middleware ────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ───────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Health check ─────────────────────────────────────────────────────
    @app.get("/api/health")
    async def health_check():
        return {"status": "ok", "service": "codeintel-backend"}

    # ── Endpoints ────────────────────────────────────────────────────────
    app.include_router(github_validate_router)
    app.include_router(github_clone_router)
    app.include_router(github_files_router)
    app.include_router(github_index_router)
    app.include_router(github_bugs_router)
    app.include_router(github_source_router)
    app.include_router(github_graph_router)

    return app


app = create_app()
