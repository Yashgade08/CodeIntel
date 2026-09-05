"""
Pydantic schemas for API request/response validation.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Repository Schemas ───────────────────────────────────────────────────────

class RepositoryCreate(BaseModel):
    """Request body for ingesting a new repository."""
    github_url: str = Field(
        ...,
        examples=["https://github.com/facebook/react"],
        description="Public GitHub repository URL"
    )


class RepositoryResponse(BaseModel):
    """Response schema for a basic repository summary."""
    id: uuid.UUID
    github_url: str
    owner: str
    name: str
    description: str | None = None
    default_branch: str = "main"
    languages: dict | None = None
    topics: list[str] | None = None
    star_count: int = 0
    fork_count: int = 0
    open_issues_count: int = 0
    ingestion_status: str
    ingestion_progress: float = 0.0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RepositoryDetailResponse(RepositoryResponse):
    """Detailed response schema for a single repository including statistics."""
    total_files: int = 0
    total_size_bytes: int = 0
    readme_path: str | None = None


class RepositoryListResponse(BaseModel):
    """Paginated list of repositories."""
    repositories: list[RepositoryResponse]
    total: int


class IngestionStatusResponse(BaseModel):
    """Ingestion job progress response."""
    repository_id: uuid.UUID
    status: str
    progress: float
    steps_completed: list[str] = []
    error_message: str | None = None


# ── Chat & Copilot Schemas ───────────────────────────────────────────────────

class Citation(BaseModel):
    """A code citation backing an answer."""
    file_path: str
    start_line: int
    end_line: int
    content: str
    relevance_score: float = 0.0


class ChatRequest(BaseModel):
    """Chat request payload."""
    message: str = Field(..., min_length=1, max_length=5000, description="User query or instruction")
    repository_id: uuid.UUID | None = Field(None, description="Optional target repository UUID")
    session_id: uuid.UUID | None = Field(None, description="Optional existing session UUID")
    stream: bool = Field(False, description="Enable Server-Sent Events (SSE) token streaming")


class ChatResponse(BaseModel):
    """Grounded chat response with citations."""
    session_id: uuid.UUID
    answer: str
    citations: list[Citation] = []
    confidence: float = 0.0
    is_grounded: bool = True


class ChatMessageResponse(BaseModel):
    """A single chat message in a session history."""
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    citations: list[Citation] = []
    confidence: float = 0.0
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    """Chat session header and message history."""
    id: uuid.UUID
    repository_id: uuid.UUID | None = None
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse] = []

    model_config = {"from_attributes": True}


class ChatSessionListResponse(BaseModel):
    """List of chat sessions."""
    sessions: list[ChatSessionResponse]
    total: int


# ── Issue Intelligence & ML Schemas ─────────────────────────────────────────

class DuplicateCandidate(BaseModel):
    """Potential duplicate issue candidate."""
    issue_id: str
    github_issue_number: int | None = None
    title: str
    similarity_score: float
    confidence: str  # HIGH, MEDIUM, LOW


class IssueAnalysisRequest(BaseModel):
    """Request payload for ML issue analysis."""
    title: str = Field(..., min_length=1, max_length=1000, description="Issue title")
    body: str | None = Field(None, description="Issue description or markdown content")
    comment_count: int = Field(0, ge=0, description="Number of issue comments")
    issue_id: uuid.UUID | None = Field(None, description="Optional existing issue UUID to analyze and persist")


class IssueAnalysisResponse(BaseModel):
    """ML predictions output for an issue."""
    issue_type: str
    type_confidence: float
    severity: str
    severity_confidence: float
    duplicate_candidates: list[DuplicateCandidate] = []
    model_version: str
    models_status: dict[str, bool] = {}


class IssuePredictionResponse(BaseModel):
    """Stored ML prediction record."""
    predicted_type: str | None = None
    type_confidence: float | None = None
    predicted_severity: str | None = None
    severity_confidence: float | None = None
    model_version: str

    model_config = {"from_attributes": True}


class IssueResponse(BaseModel):
    """A GitHub issue record with predictions."""
    id: uuid.UUID
    repository_id: uuid.UUID
    github_issue_number: int
    title: str
    body: str | None = None
    state: str = "open"
    author: str | None = None
    labels: list[str] | None = None
    comment_count: int | None = 0
    predictions: list[IssuePredictionResponse] = []
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class IssueListResponse(BaseModel):
    """Paginated list of issues."""
    issues: list[IssueResponse]
    total: int


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    timestamp: str


# ── Code Risk Intelligence Schemas ───────────────────────────────────────────

class RiskFactor(BaseModel):
    """An individual software engineering risk factor explained via SHAP."""
    factor: str
    value: float | int
    shap_value: float
    impact: str
    description: str


class FileRiskAnalyzeRequest(BaseModel):
    """Request payload for analyzing file risk."""
    file_path: str = Field(..., examples=["auth/service.py"], description="Source file path")
    content: str | None = Field(None, description="Source code text. If omitted, file will be read from repository storage.")
    repository_id: uuid.UUID | None = Field(None, description="Optional repository ID context")
    file_id: uuid.UUID | None = Field(None, description="Optional database File ID")
    churn: int | None = Field(None, description="Optional code churn override (lines added + deleted)")
    commit_frequency: int | None = Field(None, description="Optional commit count override")
    contributors: int | None = Field(None, description="Optional contributor count override")


class FileRiskAssessment(BaseModel):
    """Risk score, tier, and SHAP top factors for a source file."""
    file: str
    risk_score: int = Field(..., ge=0, le=100, description="Numerical risk score from 0 to 100")
    risk_level: str = Field(..., description="Risk category: LOW, MEDIUM, or HIGH")
    top_factors: list[RiskFactor] = []
    features: dict[str, Any] | None = None
    model_version: str = "code-risk-rf-v1.0.0"
    disclaimer: str = (
        "This assessment estimates code and maintenance risk (structural complexity, churn, "
        "defect proneness, and maintainability overhead). It does NOT claim or identify security vulnerabilities."
    )


class RepositoryRiskSummary(BaseModel):
    """Repository-wide code risk dashboard summary."""
    repository_id: uuid.UUID
    average_risk_score: float
    risk_distribution: dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    total_files_analyzed: int = 0
    high_risk_files_count: int = 0
    medium_risk_files_count: int = 0
    low_risk_files_count: int = 0
    top_riskiest_files: list[FileRiskAssessment] = []
    disclaimer: str = (
        "This dashboard reports maintenance and structural risk. High risk files require refactoring "
        "or higher test coverage and do not inherently signify security vulnerabilities."
    )


class FileRiskListResponse(BaseModel):
    """Paginated list of file risk assessments for a repository."""
    repository_id: uuid.UUID
    files: list[FileRiskAssessment] = []
    total: int = 0


# ── Dependency Graph Schemas ──────────────────────────────────────────────────

class GraphNode(BaseModel):
    """A node in the dependency graph (file, module, class, or function)."""
    id: str
    node_type: str = Field(..., description="file | module | class | function")
    language: str | None = None
    path: str | None = None
    line_count: int = 0
    size_bytes: int = 0
    is_external: bool = False
    parse_error: str | None = None


class GraphEdge(BaseModel):
    """A directed edge in the dependency graph."""
    id: str
    source: str
    target: str
    dependency_type: str = Field(..., description="import | inheritance | call")
    source_symbol: str | None = None
    target_symbol: str | None = None
    is_external: bool = False


class GraphStats(BaseModel):
    """Aggregate statistics for a dependency graph."""
    total_nodes: int = 0
    total_edges: int = 0
    file_count: int = 0
    external_module_count: int = 0
    class_count: int = 0
    function_count: int = 0
    internal_import_edges: int = 0
    languages: dict[str, int] = {}


class RepositoryGraphResponse(BaseModel):
    """Full serialized dependency graph for a repository."""
    repository_id: uuid.UUID
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    stats: GraphStats = Field(default_factory=GraphStats)
    built_at: str | None = None


class GraphDependencyItem(BaseModel):
    """A single dependency or dependent file/module entry."""
    path: str
    node_id: str
    node_type: str = "file"
    language: str | None = None
    depth: int = 1
    dependency_type: str = "import"
    is_external: bool = False


class GraphFileResponse(BaseModel):
    """Dependencies or dependents of a single file."""
    file_path: str
    repository_id: str
    direction: str = Field(..., description="dependencies | dependents")
    depth: int = 1
    results: list[GraphDependencyItem] = []
    total: int = 0
    # Only present for dependents direction:
    impact_set: list[str] = []
    impact_count: int = 0
    message: str | None = None
