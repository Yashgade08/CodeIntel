"""
API integration tests for repository endpoints.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
import uuid
import pytest
from httpx import AsyncClient

from app.api.deps import get_db_session
from app.main import app


@pytest.fixture
def mock_db():
    """Mock AsyncSession fixture for endpoint testing."""
    session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session
    yield session
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_list_repositories_empty(client: AsyncClient, mock_db: AsyncMock):
    """Test GET /api/v1/repositories returns empty list when no repositories exist."""
    with patch("app.services.repository_service.RepositoryService.list_repositories", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = []
        
        # Mock scalar_one for total count query (scalar_one is synchronous on ChunkedIteratorResult)
        mock_result = AsyncMock()
        mock_result.scalar_one = lambda: 0
        mock_db.execute.return_value = mock_result

        response = await client.get("/api/v1/repositories")
        assert response.status_code == 200
        data = response.json()
        assert data["repositories"] == []
        assert data["total"] == 0


@pytest.mark.anyio
async def test_create_repository_invalid_url(client: AsyncClient, mock_db: AsyncMock):
    """Test POST /api/v1/repositories with invalid URL returns 400 Bad Request."""
    response = await client.post(
        "/api/v1/repositories",
        json={"github_url": "invalid-url"},
    )
    assert response.status_code == 400
    assert "Invalid GitHub repository URL" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_nonexistent_repository(client: AsyncClient, mock_db: AsyncMock):
    """Test GET /api/v1/repositories/{id} returns 404 for unknown UUID."""
    random_id = str(uuid.uuid4())
    with patch("app.services.repository_service.RepositoryService.get_repository", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        response = await client.get(f"/api/v1/repositories/{random_id}")
        assert response.status_code == 404
        assert f"Repository with ID '{random_id}' not found." in response.json()["detail"]
