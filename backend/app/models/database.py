"""
SQLAlchemy async engine and session management.

Uses the session-manager pattern for clean startup / shutdown lifecycle.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


class DatabaseSessionManager:
    """
    Manages the async SQLAlchemy engine and session factory.

    Usage:
        sessionmanager.init(database_url)   # at startup
        async with sessionmanager.session() as session:
            ...
        await sessionmanager.close()        # at shutdown
    """

    def __init__(self) -> None:
        self._engine = None
        self._sessionmaker = None

    def init(self, database_url: str) -> None:
        """Create the async engine and session factory."""
        engine_kwargs: dict = {
            "pool_pre_ping": True,
            "echo": False,
        }
        if "sqlite" not in database_url:
            engine_kwargs["pool_size"] = 20
            engine_kwargs["max_overflow"] = 10

        self._engine = create_async_engine(
            database_url,
            **engine_kwargs,
        )
        self._sessionmaker = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def close(self) -> None:
        """Dispose of the engine and release all connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a transactional async session scope."""
        if self._sessionmaker is None:
            raise RuntimeError("DatabaseSessionManager is not initialized. Call init() first.")

        session = self._sessionmaker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Singleton instance
sessionmanager = DatabaseSessionManager()
