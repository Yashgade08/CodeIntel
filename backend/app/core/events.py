"""
Application lifecycle events: startup & shutdown hooks.

Manages connections to PostgreSQL, Redis, and ChromaDB.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.models.database import sessionmanager
from app.core.redis import redis_manager

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.

    - On startup: initialize logging, DB engine, Redis pool.
    - On shutdown: close all connections gracefully.
    """
    settings = get_settings()

    # ── Startup ──────────────────────────────────────────────────────────
    setup_logging(debug=settings.DEBUG)
    logger.info(
        "Starting CodeIntel",
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
    )

    # Initialize database
    try:
        sessionmanager.init(str(settings.DATABASE_URL))
        # Test connection if postgresql
        if "postgresql" in str(settings.DATABASE_URL):
            from sqlalchemy import text
            async with sessionmanager._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        logger.info("Database connection pool initialized")
    except Exception as exc:
        logger.warning(
            "PostgreSQL database unavailable, falling back to local SQLite",
            error=str(exc),
        )
        import os
        os.makedirs("./storage", exist_ok=True)
        sqlite_url = "sqlite+aiosqlite:///./storage/codeintel.db"
        sessionmanager.init(sqlite_url)
        from app.models.database import Base
        async with sessionmanager._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite database initialized at ./storage/codeintel.db")

    # If SQLite was requested directly, ensure tables are created
    if "sqlite" in str(settings.DATABASE_URL):
        from app.models.database import Base
        async with sessionmanager._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Initialize Redis (with in-memory fallback)
    await redis_manager.connect(str(settings.REDIS_URL))
    logger.info("Redis manager initialized")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    logger.info("Shutting down CodeIntel...")

    await redis_manager.disconnect()
    logger.info("Redis connection closed")

    await sessionmanager.close()
    logger.info("Database connections closed")

    logger.info("Shutdown complete")
