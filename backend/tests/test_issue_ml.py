"""
Comprehensive test suite for Machine Learning Issue Intelligence module.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.deps import get_db_session
from app.main import app
from app.ml.duplicate_detector import DuplicateDetector
from app.ml.evaluation import evaluate_classifier
from app.ml.issue_classifier import ISSUE_CLASSES, IssueClassifier
from app.ml.severity_predictor import SEVERITY_LEVELS, IssueSeverityPredictor
from app.models.issue import Issue, IssuePrediction
from app.services.issue_service import issue_intelligence_service


@pytest.fixture
def mock_db():
    """Mock AsyncSession fixture for issue endpoint testing."""
    session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session
    yield session
    app.dependency_overrides.clear()


def test_issue_classifier_pipeline():
    """Test Model 1: Issue Classification training, evaluation, and inference."""
    classifier = IssueClassifier()
    texts = [
        "Null pointer exception on login page",
        "Add dark mode theme support",
        "Update README installation instructions",
        "How to deploy using docker compose?",
        "Refactor database connection pool",
        "High CPU utilization during scanning",
        "SQL injection vulnerability in user query",
    ]
    labels = ISSUE_CLASSES  # 7 classes

    metrics = classifier.fit(texts, labels)
    assert metrics["train_accuracy"] > 0.5
    assert set(metrics["classes"]) == set(ISSUE_CLASSES)

    # Test predictions
    pred_type, conf = classifier.predict("Critical SQL injection found")
    assert pred_type in ISSUE_CLASSES
    assert 0.0 <= conf <= 1.0

    # Test serialization
    with tempfile.TemporaryDirectory() as tmpdir:
        model_file = Path(tmpdir) / "test_classifier.joblib"
        classifier.save(model_file)
        assert model_file.exists()

        loaded_clf = IssueClassifier(model_file)
        assert loaded_clf.is_trained
        p, c = loaded_clf.predict("Update README.md docs")
        assert p in ISSUE_CLASSES


def test_severity_predictor_pipeline():
    """Test Model 2: Issue Severity prediction training and inference."""
    predictor = IssueSeverityPredictor()
    titles = [
        "Minor typo in tooltip",
        "Button is misaligned by 1px",
        "Database connection timeout under load",
        "Fatal crash and security vulnerability",
    ]
    bodies = ["Small fix", "CSS tweak", "Connections exhaust", "Crash on startup"]
    comments = [0, 1, 5, 12]
    severities = ["LOW", "LOW", "HIGH", "CRITICAL"]

    metrics = predictor.fit(titles, bodies, comments, severities)
    assert metrics["train_accuracy"] > 0.5

    pred_sev, conf = predictor.predict("Fatal crash segfault on startup", "Core dumped", comment_count=10)
    assert pred_sev in SEVERITY_LEVELS
    assert 0.0 <= conf <= 1.0


def test_duplicate_detector():
    """Test Model 3: Duplicate Issue Detection using semantic embeddings."""
    detector = DuplicateDetector()
    existing = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "github_issue_number": 10,
            "title": "Database connection pool timeout",
            "body": "Connections not closing properly",
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "github_issue_number": 20,
            "title": "Add dark mode theme",
            "body": "User interface enhancement",
        },
    ]

    duplicates = detector.find_duplicates(
        query_title="Database connection timeout under load",
        query_body="Connections leak and fail",
        existing_issues=existing,
        similarity_threshold=0.30,
    )

    assert len(duplicates) > 0
    # Top match should be the database connection issue
    assert duplicates[0]["github_issue_number"] == 10
    assert duplicates[0]["confidence"] in ["HIGH", "MEDIUM", "LOW"]


def test_evaluation_metrics_calculation():
    """Test evaluation report and confusion matrix computation."""
    y_true = ["Bug", "Bug", "Documentation", "Security"]
    y_pred = ["Bug", "Documentation", "Documentation", "Security"]
    labels = ["Bug", "Documentation", "Security"]

    eval_result = evaluate_classifier(y_true, y_pred, labels=labels)
    assert "accuracy" in eval_result
    assert "precision" in eval_result
    assert "recall" in eval_result
    assert "f1" in eval_result
    assert "confusion_matrix" in eval_result
    assert len(eval_result["confusion_matrix"]) == 3


@pytest.mark.anyio
async def test_analyze_issue_endpoint(client: AsyncClient, mock_db: AsyncMock):
    """Test POST /api/issues/analyze endpoint."""
    response = await client.post(
        "/api/issues/analyze",
        json={
            "title": "Fatal segfault on startup",
            "body": "Application crashes immediately with core dump",
            "comment_count": 8,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "issue_type" in data
    assert data["issue_type"] in ISSUE_CLASSES
    assert "severity" in data
    assert data["severity"] in SEVERITY_LEVELS
    assert "model_version" in data


@pytest.mark.anyio
async def test_list_repository_issues_endpoint(client: AsyncClient, mock_db: AsyncMock):
    """Test GET /api/repositories/{id}/issues endpoint."""
    repo_id = uuid.uuid4()
    with patch("app.services.issue_service.IssueIntelligenceService.get_repository_issues", new_callable=AsyncMock) as mock_issues:
        mock_issues.return_value = []

        mock_result = AsyncMock()
        mock_result.scalar_one = lambda: 0
        mock_db.execute.return_value = mock_result

        response = await client.get(f"/api/repositories/{repo_id}/issues")
        assert response.status_code == 200
        data = response.json()
        assert data["issues"] == []
        assert data["total"] == 0


@pytest.mark.anyio
async def test_get_issue_endpoint(client: AsyncClient, mock_db: AsyncMock):
    """Test GET /api/issues/{id} endpoint."""
    issue_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    from datetime import datetime, timezone
    mock_issue = Issue(
        id=issue_id,
        repository_id=repo_id,
        github_issue_number=42,
        title="Sample issue",
        body="Sample body",
        state="open",
        comment_count=0,
        predictions=[],
        created_at=datetime.now(timezone.utc),
    )

    with patch("app.services.issue_service.IssueIntelligenceService.get_issue", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_issue

        response = await client.get(f"/api/issues/{issue_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(issue_id)
        assert data["github_issue_number"] == 42
