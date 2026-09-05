"""
Redis connection manager.

Provides a singleton async Redis client that is initialised at
application startup and closed on shutdown.
"""

from __future__ import annotations

from typing import Any

from redis.asyncio import ConnectionPool, Redis

from app.core.logging import get_logger

logger = get_logger(__name__)


class InMemoryRedis:
    """Fallback in-memory key-value cache when real Redis server is unavailable."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    async def ping(self) -> bool:
        return True

    async def get(self, name: str) -> Any:
        return self._store.get(name)

    async def set(self, name: str, value: Any, ex: int | None = None, **kwargs: Any) -> bool:
        self._store[name] = value
        return True

    async def delete(self, *names: str) -> int:
        count = 0
        for n in names:
            if n in self._store:
                del self._store[n]
                count += 1
        return count

    async def flushdb(self) -> bool:
        self._store.clear()
        return True

    async def aclose(self) -> None:
        pass


class RedisManager:
    """Manages the async Redis connection pool with in-memory fallback."""

    def __init__(self) -> None:
        self._pool: ConnectionPool | None = None
        self._client: Any = None

    async def connect(self, url: str, max_connections: int = 20) -> None:
        """Create connection pool and client, falling back to in-memory cache if unreachable."""
        try:
            self._pool = ConnectionPool.from_url(
                url,
                max_connections=max_connections,
                decode_responses=True,
            )
            client = Redis(connection_pool=self._pool)
            await client.ping()
            self._client = client
            logger.info("Redis connected", url=url)
        except Exception as exc:
            logger.warning(
                "Redis server unavailable, using in-memory cache fallback",
                error=str(exc),
            )
            self._client = InMemoryRedis()

    async def disconnect(self) -> None:
        """Close the Redis connection pool."""
        if self._client and hasattr(self._client, "aclose"):
            await self._client.aclose()
        if self._pool:
            await self._pool.disconnect()
        self._client = None
        self._pool = None

    @property
    def client(self) -> Any:
        """Get active Redis client or in-memory fallback."""
        if self._client is None:
            self._client = InMemoryRedis()
        return self._client


# Singleton instance
redis_manager = RedisManager()
