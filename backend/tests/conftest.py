"""
Test configuration and shared fixtures.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    """Use asyncio as the async backend for tests."""
    return "asyncio"


@pytest.fixture
async def client():
    """
    Async HTTP test client for the FastAPI app.

    Note: This client does NOT initialize DB/Redis connections.
    For integration tests that need real connections, use
    a separate fixture with lifespan management.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
