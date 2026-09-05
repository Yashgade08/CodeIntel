"""
FastAPI endpoints for Codebase Copilot Chat Q&A and session history.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.llm.generator import SAFEGUARD_FALLBACK_TEXT
from app.llm.prompts.templates import COPILOT_SYSTEM_PROMPT, build_copilot_prompt
from app.llm.providers.factory import get_llm_provider
from app.models.chat import ChatSession
from app.rag.pipeline import rag_pipeline
from app.schemas import (
    Citation,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from app.services.chat_service import ChatService

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Send a chat message to Codebase Copilot (supports streaming SSE)",
)
async def chat(
    payload: ChatRequest,
    accept: str | None = Header(None),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Chat endpoint for Codebase Copilot.
    Grounds answers in RAG evidence, provides citations, supports streaming SSE.
    """
    chat_service = ChatService(db)

    # 1. Get or Create Session
    session_id = payload.session_id
    if not session_id:
        session = await chat_service.create_session(
            repository_id=payload.repository_id,
            title=payload.message[:40].strip(),
        )
        session_id = session.id
    else:
        session = await chat_service.get_session(session_id)
        if not session:
            raise NotFoundException(f"ChatSession with ID '{session_id}' not found.")

    # 2. Persist User Message
    await chat_service.add_message(
        session_id=session_id,
        role="user",
        content=payload.message,
    )

    # 3. Retrieve RAG Evidence Chunks
    retrieved_chunks = []
    repo_id_str = str(payload.repository_id) if payload.repository_id else (
        str(session.repository_id) if session.repository_id else None
    )

    if repo_id_str:
        retrieved_chunks = rag_pipeline.search(
            repository_id=repo_id_str,
            query_text=payload.message,
            top_k=5,
        )

    # Evaluate confidence & hallucination threshold
    top_score = retrieved_chunks[0][1] if retrieved_chunks else 0.0
    threshold = rag_pipeline.generator.threshold

    # If repo_id was provided but confidence is below threshold, return safeguard fallback
    if repo_id_str and top_score < threshold:
        logger.info("Confidence below threshold, returning safeguard answer", score=top_score)
        answer = SAFEGUARD_FALLBACK_TEXT
        citations_list = []
        
        await chat_service.add_message(
            session_id=session_id,
            role="assistant",
            content=answer,
            citations=citations_list,
            confidence=top_score,
        )

        return ChatResponse(
            session_id=session_id,
            answer=answer,
            citations=[],
            confidence=top_score,
            is_grounded=False,
        )

    # Build Citations
    citations_data = []
    citations_list = []
    for chunk_tuple in retrieved_chunks:
        chunk, score = chunk_tuple
        c_dict = {
            "file_path": chunk.file_path,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "content": chunk.content[:300],
            "relevance_score": round(score, 4),
        }
        citations_data.append(c_dict)
        citations_list.append(Citation(**c_dict))

    # Retrieve history for prompt context
    history = await chat_service.get_session_history(session_id, max_turns=6)

    # Build Prompt
    full_prompt = build_copilot_prompt(
        user_query=payload.message,
        retrieved_chunks=retrieved_chunks,
        conversation_history=history,
    )

    provider = get_llm_provider()

    # ── Check Streaming Request (SSE) ────────────────────────────────────────
    is_stream = payload.stream or (accept and "text/event-stream" in accept)

    if is_stream:
        async def event_stream() -> AsyncGenerator[str, None]:
            accumulated_tokens = []
            async for token in provider.generate_stream(full_prompt, COPILOT_SYSTEM_PROMPT):
                accumulated_tokens.append(token)
                event_data = json.dumps({"token": token, "session_id": str(session_id)})
                yield f"data: {event_data}\n\n"

            # Persist assistant answer after streaming completes
            full_response = "".join(accumulated_tokens)
            await chat_service.add_message(
                session_id=session_id,
                role="assistant",
                content=full_response,
                citations=citations_data,
                confidence=top_score,
            )
            yield f"data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # Standard JSON Response
    answer = await provider.generate(full_prompt, COPILOT_SYSTEM_PROMPT)

    await chat_service.add_message(
        session_id=session_id,
        role="assistant",
        content=answer,
        citations=citations_data,
        confidence=top_score,
    )

    return ChatResponse(
        session_id=session_id,
        answer=answer,
        citations=citations_list,
        confidence=top_score,
        is_grounded=True,
    )


@router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
    summary="List all chat sessions",
)
async def list_chat_sessions(
    repository_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> ChatSessionListResponse:
    """Retrieve paginated chat sessions."""
    chat_service = ChatService(db)
    sessions = await chat_service.list_sessions(repository_id=repository_id, limit=limit, offset=offset)

    stmt = select(func.count(ChatSession.id))
    if repository_id:
        stmt = stmt.where(ChatSession.repository_id == repository_id)
    total_query = await db.execute(stmt)
    total = total_query.scalar_one()

    return ChatSessionListResponse(
        sessions=[ChatSessionResponse.model_validate(s) for s in sessions],
        total=total,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    summary="Get chat session details and message history",
)
async def get_chat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ChatSessionResponse:
    """Get chat session and message history by session ID."""
    chat_service = ChatService(db)
    session = await chat_service.get_session(session_id)
    if not session:
        raise NotFoundException(f"ChatSession with ID '{session_id}' not found.")

    return ChatSessionResponse.model_validate(session)
