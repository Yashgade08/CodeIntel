"""
FastAPI application entry point for CodeIntel.

Configured with:
- CORS middleware
- Exception handlers
- Standalone GitHub validation endpoint (Step 1)
- Health check endpoint
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.api.github_validate import router as github_validate_router


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

    # ── Step 1: GitHub URL validation ────────────────────────────────────
    app.include_router(github_validate_router)

    return app


app = create_app()
