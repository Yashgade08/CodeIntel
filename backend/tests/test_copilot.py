"""
Unit and integration test suite for Codebase Copilot and LLM provider layer.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
import uuid
import pytest
from httpx import AsyncClient

from app.api.deps import get_db_session
from app.llm.prompts.templates import build_copilot_prompt
from app.llm.providers.factory import get_llm_provider
from app.llm.providers.mock_provider import MockLLMProvider
from app.llm.providers.openai_provider import OpenAIProvider
from app.main import app
from app.models.chat import ChatMessage, ChatSession
from app.rag.chunker import DocumentChunk
from app.services.chat_service import ChatService


@pytest.fixture
def mock_db():
    """Mock AsyncSession fixture for chat endpoint testing."""
    session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session
    yield session
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_llm_provider_factory():
    """Test LLM provider selection factory."""
    provider_mock = get_llm_provider("mock")
    assert isinstance(provider_mock, MockLLMProvider)

    res = await provider_mock.generate("Explain auth flow", "System Prompt")
    assert "Implementation Details" in res or "I couldn't find" in res


def test_prompt_template_formatting():
    """Test copilot prompt template formatting with citations and structure."""
    chunk = DocumentChunk(
        id="c1",
        repository_id="repo1",
        file_path="auth/service.py",
        start_line=42,
        end_line=78,
        content="def authenticate_user(): pass",
        source_type="code",
    )

    prompt = build_copilot_prompt(
        user_query="Explain auth flow",
        retrieved_chunks=[(chunk, 0.95)],
        repo_structure="backend/\n  app/",
        dependencies="auth/service.py -> core/config.py",
        conversation_history=[{"role": "user", "content": "Hi"}],
    )

    assert "Explain auth flow" in prompt
    assert "[auth/service.py:42-78]" in prompt
    assert "backend/" in prompt
    assert "core/config.py" in prompt


@pytest.mark.anyio
async def test_chat_service_session_crud():
    """Test ChatService session creation and message addition."""
    db = AsyncMock()
    db.add = lambda obj: None
    service = ChatService(db)

    # Mock DB query results
    session_id = uuid.uuid4()
    mock_session = ChatSession(id=session_id, title="Test Chat")
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = lambda: mock_session
    db.execute.return_value = mock_result

    sess = await service.create_session(title="Test Chat")
    assert sess.title == "Test Chat"

    msg = await service.add_message(
        session_id=session_id,
        role="user",
        content="Where is payment logic?",
    )
    assert msg.role == "user"
    assert msg.content == "Where is payment logic?"


@pytest.mark.anyio
async def test_chat_endpoint_creation(client: AsyncClient, mock_db: AsyncMock):
    """Test POST /api/chat returns grounded response."""
    session_id = uuid.uuid4()
    mock_session = ChatSession(id=session_id, title="Where is payment logic?")
    
    with patch("app.services.chat_service.ChatService.create_session", new_callable=AsyncMock) as mock_create_sess, \
         patch("app.services.chat_service.ChatService.add_message", new_callable=AsyncMock) as mock_add_msg, \
         patch("app.services.chat_service.ChatService.get_session_history", new_callable=AsyncMock) as mock_hist:
        
        mock_create_sess.return_value = mock_session
        mock_hist.return_value = []

        response = await client.post(
            "/api/chat",
            json={"message": "Where is payment logic?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "answer" in data


@pytest.mark.anyio
async def test_chat_sessions_list(client: AsyncClient, mock_db: AsyncMock):
    """Test GET /api/chat/sessions returns session list."""
    with patch("app.services.chat_service.ChatService.list_sessions", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = []

        mock_result = AsyncMock()
        mock_result.scalar_one = lambda: 0
        mock_db.execute.return_value = mock_result

        response = await client.get("/api/chat/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["total"] == 0
