"""
Chat service — manages ChatSession and ChatMessage persistence and history retrieval.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.chat import ChatMessage, ChatSession

logger = get_logger(__name__)


class ChatService:
    """Handles ChatSession and ChatMessage CRUD and history management."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_session(
        self,
        repository_id: UUID | str | None = None,
        title: str = "New Chat",
    ) -> ChatSession:
        """Create a new chat session."""
        repo_uuid = UUID(str(repository_id)) if repository_id else None
        session = ChatSession(
            repository_id=repo_uuid,
            title=title,
        )
        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)
        logger.info("ChatSession created", session_id=str(session.id), title=title)
        return session

    async def get_session(self, session_id: UUID) -> ChatSession | None:
        """Get a single chat session by ID with messages loaded."""
        result = await self._db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        repository_id: UUID | str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatSession]:
        """List chat sessions paginated."""
        stmt = select(ChatSession).order_by(ChatSession.updated_at.desc()).offset(offset).limit(limit)
        if repository_id:
            stmt = stmt.where(ChatSession.repository_id == UUID(str(repository_id)))

        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        citations: list[dict] | None = None,
        confidence: float = 0.0,
    ) -> ChatMessage:
        """Add user or assistant message to a session."""
        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            citations=citations or [],
            confidence=confidence,
        )
        self._db.add(msg)

        # Update session title if user message and session title is default
        session = await self.get_session(session_id)
        if session and role == "user" and session.title == "New Chat":
            session.title = content[:40].strip()
            self._db.add(session)

        await self._db.commit()
        await self._db.refresh(msg)
        return msg

    async def get_session_history(
        self,
        session_id: UUID,
        max_turns: int = 6,
    ) -> list[dict[str, str]]:
        """Retrieve recent conversation history formatted for LLM prompts."""
        session = await self.get_session(session_id)
        if not session or not session.messages:
            return []

        recent_msgs = session.messages[-max_turns:]
        return [
            {"role": m.role, "content": m.content}
            for m in recent_msgs
        ]
