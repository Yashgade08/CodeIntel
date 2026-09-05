"""
Health check endpoints.

Provides liveness and readiness probes for Docker / Kubernetes
health monitoring.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_redis
from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Basic liveness probe — confirms the API process is running."""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    """
    Readiness probe — verifies all backing services are accessible.

    Checks: PostgreSQL, Redis.
    """
    checks: dict[str, dict] = {}

    # PostgreSQL
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        checks["postgres"] = {"status": "connected"}
    except Exception as e:
        checks["postgres"] = {"status": "error", "detail": str(e)}

    # Redis
    try:
        pong = await redis.ping()
        checks["redis"] = {"status": "connected" if pong else "error"}
    except Exception as e:
        checks["redis"] = {"status": "error", "detail": str(e)}

    all_healthy = all(c["status"] == "connected" for c in checks.values())

    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
