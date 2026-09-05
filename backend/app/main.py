"""
FastAPI application entry point.

Creates and configures the FastAPI app with:
- CORS middleware
- Lifespan event handlers (DB, Redis init/teardown)
- Exception handlers
- API v1 router
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import get_settings
from app.core.events import lifespan
from app.core.exceptions import register_exception_handlers
from app.api.v1.router import router as v1_router
from app.api.github_validate import router as github_validate_router


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="GitHub Repository Intelligence & Codebase Copilot",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
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

    # ── Routers ──────────────────────────────────────────────────────────
    app.include_router(v1_router, prefix=settings.API_V1_PREFIX)
    app.include_router(v1_router, prefix="/api")

    # ── GitHub URL validation (standalone, no DB/token required) ─────────
    app.include_router(github_validate_router)

    return app


app = create_app()
