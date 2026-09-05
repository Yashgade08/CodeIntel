"""
FastAPI dependency injection providers.

Provides database sessions, Redis client, and service instances
to endpoint functions via FastAPI's Depends() mechanism.
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.models.database import sessionmanager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional database session."""
    async with sessionmanager.session() as session:
        yield session


async def get_redis():  # noqa: ANN201
    """Get the active Redis client."""
    return redis_manager.client
