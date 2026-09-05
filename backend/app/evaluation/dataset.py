"""
Curated Ground-Truth Evaluation Dataset for CodeIntel.

Contains manually verified test samples for:
1. RAG Q&A retrieval and answer accuracy
2. ML Issue Classification (7 classes)
3. Issue Severity Prediction (4 levels)
4. Duplicate Issue Detection
5. Code Risk & Maintainability Scoring
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class RAGTestCase:
    id: str
    query: str
    expected_files: List[str]
    expected_concepts: List[str]
    ground_truth_answer: str


@dataclass
class IssueTestCase:
    id: str
    title: str
    body: str
    ground_truth_category: str
    ground_truth_severity: str


@dataclass
class DuplicateTestCase:
    id: str
    issue_a_title: str
    issue_a_body: str
    issue_b_title: str
    issue_b_body: str
    is_duplicate: bool


@dataclass
class RiskTestCase:
    id: str
    file_path: str
    line_count: int
    cyclomatic_complexity: int
    dependency_count: int
    num_contributors: int
    commit_frequency: int
    ground_truth_risk_level: str
    ground_truth_risk_score: float


# Ground truth RAG test suite
RAG_TEST_CASES: List[RAGTestCase] = [
    RAGTestCase(
        id="rag-01",
        query="How does CodeIntel construct the NetworkX repository dependency graph?",
        expected_files=["app/graph/builder.py", "app/graph/analyzer.py"],
        expected_concepts=["NetworkX", "DiGraph", "AST parsing", "import extraction", "builder"],
        ground_truth_answer=(
            "CodeIntel extracts AST import structures and function/class symbols from source files "
            "using AST parsers (in analyzer.py), then builds a directed graph (DiGraph) using NetworkX "
            "inside app/graph/builder.py where nodes represent files/modules and edges represent imports."
        ),
    ),
    RAGTestCase(
        id="rag-02",
        query="Where is the ML model for GitHub issue classification implemented?",
        expected_files=["app/services/issue_service.py", "app/ml/issue_classifier.py"],
        expected_concepts=["LogisticRegression", "TfidfVectorizer", "issue classification", "scikit-learn"],
        ground_truth_answer=(
            "GitHub issue classification uses a TF-IDF vectorizer paired with a Logistic Regression model "
            "trained to classify issue titles and bodies into 7 categories (Bug, Feature Request, Documentation, "
            "Question, Enhancement, Performance, Security) inside app/services/issue_service.py and app/ml/issue_classifier.py."
        ),
    ),
    RAGTestCase(
        id="rag-03",
        query="How does CodeIntel calculate file risk scores and SHAP explainability?",
        expected_files=["app/services/risk_service.py", "app/ml/risk_model.py"],
        expected_concepts=["XGBoost", "SHAP", "cyclomatic complexity", "code churn", "risk score"],
        ground_truth_answer=(
            "CodeIntel computes software complexity features including lines of code, cyclomatic complexity, "
            "dependency count, commit frequency, and contributor count, then evaluates an XGBoost/RandomForest model "
            "with SHAP feature attribution to output a score from 0-100 and top contributing factors."
        ),
    ),
    RAGTestCase(
        id="rag-04",
        query="What API endpoint triggers background GitHub repository cloning and ingestion?",
        expected_files=["app/api/v1/endpoints/repositories.py", "app/ingestion/pipeline.py"],
        expected_concepts=["POST /repositories", "BackgroundTasks", "IngestionPipeline", "parse_github_url"],
        ground_truth_answer=(
            "The POST /api/v1/repositories endpoint receives a GitHub URL, validates it via parse_github_url, "
            "creates a database repository record, and triggers the async IngestionPipeline background task."
        ),
    ),
]


# Ground truth ML Issue Test Samples
ISSUE_TEST_CASES: List[IssueTestCase] = [
    IssueTestCase(
        id="iss-eval-01",
        title="High memory consumption during large file vector embedding batch ingest",
        body="When cloning and vectorizing repositories > 500MB, PyTorch CUDA cache leaks memory.",
        ground_truth_category="Performance",
        ground_truth_severity="HIGH",
    ),
    IssueTestCase(
        id="iss-eval-02",
        title="Add support for Tree-Sitter Go & Rust parser in dependency graph builder",
        body="Feature request to extend AST analysis beyond Python into Go interfaces.",
        ground_truth_category="Feature Request",
        ground_truth_severity="MEDIUM",
    ),
    IssueTestCase(
        id="iss-eval-03",
        title="Unauthenticated API endpoint exposes repository list metadata",
        body="Security audit identified missing JWT bearer token enforcement on endpoints.",
        ground_truth_category="Security",
        ground_truth_severity="CRITICAL",
    ),
    IssueTestCase(
        id="iss-eval-04",
        title="Update API documentation for RAG streaming endpoint",
        body="The OpenAPI schema lacks definitions for SSE events emitted by /api/v1/rag/chat.",
        ground_truth_category="Documentation",
        ground_truth_severity="LOW",
    ),
    IssueTestCase(
        id="iss-eval-05",
        title="Uncaught AttributeError in get_file_content when path does not exist",
        body="Traceback shows AttributeError on NoneType file record during file view request.",
        ground_truth_category="Bug",
        ground_truth_severity="HIGH",
    ),
    IssueTestCase(
        id="iss-eval-06",
        title="How do I configure the Redis cache TTL for vector search?",
        body="Is there a configuration setting in settings.py to adjust cache expiration time?",
        ground_truth_category="Question",
        ground_truth_severity="LOW",
    ),
    IssueTestCase(
        id="iss-eval-07",
        title="Refactor graph serializer to reduce response size by 40%",
        body="Optimization proposal to compress Node and Edge JSON payload schema.",
        ground_truth_category="Enhancement",
        ground_truth_severity="MEDIUM",
    ),
]


# Ground truth Duplicate Pair Test Cases
DUPLICATE_TEST_CASES: List[DuplicateTestCase] = [
    DuplicateTestCase(
        id="dup-01",
        issue_a_title="Memory leak in chunk embedding pipeline",
        issue_a_body="Worker process RAM spikes during vector embedding generation.",
        issue_b_title="High memory consumption during large file vector embedding batch ingest",
        issue_b_body="PyTorch CUDA cache holds unreleased tensors when embedding large batches.",
        is_duplicate=True,
    ),
    DuplicateTestCase(
        id="dup-02",
        issue_a_title="Add support for Go language parser",
        issue_a_body="Support tree-sitter for Go AST analysis.",
        issue_b_title="Unauthenticated API endpoint exposes repository list",
        issue_b_body="Security issue on endpoints missing bearer token validation.",
        is_duplicate=False,
    ),
]


# Ground truth Code Risk Test Cases
RISK_TEST_CASES: List[RiskTestCase] = [
    RiskTestCase(
        id="risk-01",
        file_path="app/rag/pipeline.py",
        line_count=420,
        cyclomatic_complexity=28,
        dependency_count=14,
        num_contributors=6,
        commit_frequency=34,
        ground_truth_risk_level="HIGH",
        ground_truth_risk_score=84.0,
    ),
    RiskTestCase(
        id="risk-02",
        file_path="app/graph/builder.py",
        line_count=380,
        cyclomatic_complexity=22,
        dependency_count=11,
        num_contributors=4,
        commit_frequency=22,
        ground_truth_risk_level="HIGH",
        ground_truth_risk_score=76.0,
    ),
    RiskTestCase(
        id="risk-03",
        file_path="app/ingestion/cloner.py",
        line_count=240,
        cyclomatic_complexity=16,
        dependency_count=8,
        num_contributors=3,
        commit_frequency=18,
        ground_truth_risk_level="MEDIUM",
        ground_truth_risk_score=68.0,
    ),
    RiskTestCase(
        id="risk-04",
        file_path="app/models/database.py",
        line_count=120,
        cyclomatic_complexity=6,
        dependency_count=4,
        num_contributors=2,
        commit_frequency=8,
        ground_truth_risk_level="LOW",
        ground_truth_risk_score=25.0,
    ),
]
