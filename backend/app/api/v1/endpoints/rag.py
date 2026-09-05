"""
FastAPI endpoints for RAG hybrid search and grounded repository Q&A.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.rag.pipeline import rag_pipeline
from app.schemas import Citation
from app.services.repository_service import RepositoryService

logger = get_logger(__name__)

router = APIRouter(prefix="/repositories", tags=["rag"])


class SearchRequest(BaseModel):
    """Payload for code & document search."""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(5, ge=1, le=50)
    file_path: str | None = None
    language: str | None = None
    source_type: str | None = None  # code, readme, documentation, issue, pull_request
    symbol_name: str | None = None


class SearchResultItem(BaseModel):
    """A single retrieved code or document search result."""
    file_path: str
    start_line: int
    end_line: int
    content: str
    relevance_score: float
    source_type: str
    language: str | None = None
    symbol_name: str | None = None
    citation: str


class SearchResponse(BaseModel):
    """Response payload for code search."""
    repository_id: UUID
    query: str
    results: list[SearchResultItem]
    total_results: int


class ChatRequestPayload(BaseModel):
    """Payload for grounded Q&A chat."""
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: str | None = None


class ChatResponsePayload(BaseModel):
    """Payload for grounded Q&A response."""
    repository_id: UUID
    answer: str
    citations: list[Citation]
    confidence: float
    is_grounded: bool
    session_id: str | None = None


@router.post(
    "/{repo_id}/index-rag",
    status_code=status.HTTP_200_OK,
    summary="Trigger RAG indexing for a repository",
)
async def index_repository_rag(
    repo_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Index repository source code, documentation, and issues for RAG."""
    service = RepositoryService(db)
    repo = await service.get_repository(repo_id)
    if not repo:
        raise NotFoundException(f"Repository with ID '{repo_id}' not found.")

    total_chunks = await rag_pipeline.index_repository(repo_id, db)
    return {
        "repository_id": str(repo_id),
        "status": "indexed",
        "total_chunks": total_chunks,
    }


@router.post(
    "/{repo_id}/search",
    response_model=SearchResponse,
    summary="Hybrid code and document search with metadata filters",
)
async def search_repository(
    repo_id: UUID,
    payload: SearchRequest,
    db: AsyncSession = Depends(get_db_session),
) -> SearchResponse:
    """
    Search repository using Dense Vector + BM25 Hybrid Retrieval and Cross-Encoder Reranking.
    """
    service = RepositoryService(db)
    repo = await service.get_repository(repo_id)
    if not repo:
        raise NotFoundException(f"Repository with ID '{repo_id}' not found.")

    filters = {}
    if payload.file_path:
        filters["file_path"] = payload.file_path
    if payload.language:
        filters["language"] = payload.language
    if payload.source_type:
        filters["source_type"] = payload.source_type
    if payload.symbol_name:
        filters["symbol_name"] = payload.symbol_name

    results = rag_pipeline.search(
        repository_id=str(repo_id),
        query_text=payload.query,
        top_k=payload.top_k,
        filters=filters,
    )

    items = [
        SearchResultItem(
            file_path=chunk.file_path,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            content=chunk.content,
            relevance_score=round(score, 4),
            source_type=chunk.source_type,
            language=chunk.language,
            symbol_name=chunk.symbol_name,
            citation=chunk.citation_str,
        )
        for chunk, score in results
    ]

    return SearchResponse(
        repository_id=repo_id,
        query=payload.query,
        results=items,
        total_results=len(items),
    )


@router.post(
    "/{repo_id}/chat",
    response_model=ChatResponsePayload,
    summary="Grounded Q&A with hallucination protection and line citations",
)
async def chat_repository(
    repo_id: UUID,
    payload: ChatRequestPayload,
    db: AsyncSession = Depends(get_db_session),
) -> ChatResponsePayload:
    """
    Ask a question about a repository and receive a grounded answer with citations.
    Returns safeguard message if evidence is insufficient.
    """
    service = RepositoryService(db)
    repo = await service.get_repository(repo_id)
    if not repo:
        raise NotFoundException(f"Repository with ID '{repo_id}' not found.")

    res = rag_pipeline.ask_question(
        repository_id=str(repo_id),
        query_text=payload.message,
    )

    citations = [
        Citation(
            file_path=c["file_path"],
            start_line=c["start_line"],
            end_line=c["end_line"],
            content=c["content"],
            relevance_score=c["relevance_score"],
        )
        for c in res.get("citations", [])
    ]

    return ChatResponsePayload(
        repository_id=repo_id,
        answer=res["answer"],
        citations=citations,
        confidence=res["confidence"],
        is_grounded=res.get("is_grounded", False),
        session_id=payload.session_id,
    )
