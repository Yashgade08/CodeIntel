"""
Tests for the Code Risk Intelligence module.
Covers feature extraction, Random Forest risk scoring, SHAP explainability,
and FastAPI endpoints.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_db_session
from app.main import app
from app.ml.risk.explainer import CodeRiskExplainer
from app.ml.risk.features import (
    CodeFeatures,
    extract_code_features,
)
from app.ml.risk.model import CodeRiskModel
from app.ml.risk.training import train_code_risk_model
from app.models.file import File
from app.models.repository import Repository


@pytest.fixture
def mock_db():
    """Mock AsyncSession fixture for risk endpoint testing."""
    session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session
    yield session
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_feature_extraction_python():
    """Test AST-based feature extraction for Python source code."""
    code = """
import os
import sys
from datetime import datetime

class AuthController:
    def __init__(self):
        self.retries = 0

    def validate_token(self, token: str) -> bool:
        if not token:
            return False
        if len(token) < 10:
            return False
        return True

    def login(self, username, password):
        for attempt in range(3):
            if username and password:
                return True
            elif not username:
                break
        return False
"""
    feats = extract_code_features(
        file_path="auth/controller.py",
        content=code,
        churn=120,
        commit_frequency=8,
        contributors=2,
        historical_issues=1,
    )

    assert feats.lines_of_code > 10
    assert feats.cyclomatic_complexity >= 5
    assert feats.number_of_functions == 3  # __init__, validate_token, login
    assert feats.number_of_classes == 1    # AuthController
    assert feats.number_of_imports >= 3    # os, sys, datetime
    assert feats.dependency_count >= 3
    assert feats.code_churn == 120
    assert feats.commit_frequency == 8
    assert feats.number_of_contributors == 2
    assert feats.historical_issue_count == 1


@pytest.mark.asyncio
async def test_feature_extraction_non_python():
    """Test regex pattern-matching feature extraction for TypeScript / JavaScript."""
    js_code = """
import React, { useState } from 'react';
import axios from 'axios';

export class UserProfile {
    render() {
        if (loading) {
            return <div>Loading</div>;
        } else if (error) {
            return <div>Error</div>;
        }
        for (let i = 0; i < items.length; i++) {
            console.log(items[i]);
        }
        return <div>Ready</div>;
    }
}
"""
    feats = extract_code_features(
        file_path="src/components/UserProfile.tsx",
        content=js_code,
        churn=50,
        commit_frequency=4,
        contributors=1,
    )

    assert feats.lines_of_code > 5
    assert feats.cyclomatic_complexity >= 3
    assert feats.number_of_classes >= 1
    assert feats.number_of_imports >= 2
    assert feats.code_churn == 50


@pytest.mark.asyncio
async def test_code_risk_model_training_and_prediction(tmp_path):
    """Test model training, serialization, and risk level mapping."""
    target_path = tmp_path / "test_risk_model.joblib"
    results = train_code_risk_model(model_path=target_path)

    assert results["status"] == "trained"
    assert target_path.exists()
    assert results["metrics"]["r2"] > 0.85

    # Load and test prediction
    model = CodeRiskModel(model_path=target_path)
    assert model.is_trained

    # High-risk profile: high LOC, high CC, high churn
    high_feats = CodeFeatures(
        lines_of_code=1400,
        cyclomatic_complexity=45,
        number_of_functions=30,
        number_of_classes=5,
        dependency_count=18,
        number_of_imports=20,
        code_churn=3000,
        commit_frequency=70,
        number_of_contributors=10,
        historical_issue_count=10,
    )
    score, level = model.predict(high_feats)
    assert 70 <= score <= 100
    assert level == "HIGH"

    # Low-risk profile: clean small utility
    low_feats = CodeFeatures(
        lines_of_code=35,
        cyclomatic_complexity=1,
        number_of_functions=2,
        number_of_classes=0,
        dependency_count=1,
        number_of_imports=1,
        code_churn=10,
        commit_frequency=2,
        number_of_contributors=1,
        historical_issue_count=0,
    )
    low_score, low_level = model.predict(low_feats)
    assert 0 <= low_score < 35
    assert low_level == "LOW"


@pytest.mark.asyncio
async def test_shap_explainer_top_factors():
    """Test SHAP TreeExplainer attributions and formatting."""
    model = CodeRiskModel()
    explainer = CodeRiskExplainer(model)

    high_feats = CodeFeatures(
        lines_of_code=1500,
        cyclomatic_complexity=50,
        number_of_functions=25,
        number_of_classes=4,
        dependency_count=15,
        number_of_imports=18,
        code_churn=2500,
        commit_frequency=60,
        number_of_contributors=8,
        historical_issue_count=7,
    )

    factors = explainer.explain(high_feats, top_n=3)
    assert len(factors) == 3

    for f in factors:
        assert "factor" in f
        assert "value" in f
        assert "shap_value" in f
        assert "impact" in f
        assert "description" in f
        assert len(f["description"]) > 10


@pytest.mark.asyncio
async def test_post_risk_analyze_endpoint(mock_db: AsyncMock):
    """Test POST /api/risk/analyze endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "file_path": "auth/service.py",
            "content": """
import os, sys, json

class AuthService:
    def verify(self, token):
        if not token:
            return False
        for char in token:
            if char == ' ':
                return False
        return True
""",
            "churn": 850,
            "commit_frequency": 25,
            "contributors": 4,
        }
        resp = await client.post("/api/risk/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["file"] == "auth/service.py"
        assert 0 <= data["risk_score"] <= 100
        assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
        assert len(data["top_factors"]) > 0
        assert "maintenance risk" in data["disclaimer"].lower()
        assert "not claim or identify security vulnerabilities" in data["disclaimer"].lower()


@pytest.mark.asyncio
async def test_get_repository_risk_dashboard_endpoint(mock_db: AsyncMock):
    """Test GET /api/repositories/{id}/risk endpoint."""
    repo_id = uuid.uuid4()
    mock_repo = Repository(
        id=repo_id,
        github_url="https://github.com/example/demo",
        owner="example",
        name="demo",
        ingestion_status="completed",
    )

    mock_file1 = File(
        id=uuid.uuid4(),
        repository_id=repo_id,
        path="src/utils.py",
        filename="utils.py",
        extension=".py",
        line_count=40,
        metadata_={
            "risk_assessment": {
                "file": "src/utils.py",
                "risk_score": 15,
                "risk_level": "LOW",
                "top_factors": [],
                "disclaimer": "Maintenance risk only.",
            }
        },
    )
    mock_file2 = File(
        id=uuid.uuid4(),
        repository_id=repo_id,
        path="src/legacy_engine.py",
        filename="legacy_engine.py",
        extension=".py",
        line_count=1200,
        metadata_={
            "risk_assessment": {
                "file": "src/legacy_engine.py",
                "risk_score": 85,
                "risk_level": "HIGH",
                "top_factors": [
                    {
                        "factor": "lines_of_code",
                        "value": 1200,
                        "shap_value": 5.4,
                        "impact": "+5.4",
                        "description": "High LOC",
                    }
                ],
                "disclaimer": "Maintenance risk only.",
            }
        },
    )

    mock_db.get.return_value = mock_repo
    mock_files_result = MagicMock()
    mock_files_result.scalars.return_value.all.return_value = [mock_file1, mock_file2]
    mock_db.execute.return_value = mock_files_result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/repositories/{repo_id}/risk")
        assert resp.status_code == 200
        data = resp.json()

        assert data["repository_id"] == str(repo_id)
        assert data["total_files_analyzed"] == 2
        assert data["high_risk_files_count"] == 1
        assert data["low_risk_files_count"] == 1
        assert data["average_risk_score"] == 50.0
        assert len(data["top_riskiest_files"]) == 2
        assert data["top_riskiest_files"][0]["file"] == "src/legacy_engine.py"
        assert data["top_riskiest_files"][0]["risk_level"] == "HIGH"
        assert "maintenance and structural risk" in data["disclaimer"].lower()


@pytest.mark.asyncio
async def test_get_repository_files_risk_endpoint(mock_db: AsyncMock):
    """Test GET /api/repositories/{id}/risk/files endpoint with filtering."""
    repo_id = uuid.uuid4()
    mock_repo = Repository(
        id=repo_id,
        github_url="https://github.com/example/demo2",
        owner="example",
        name="demo2",
        ingestion_status="completed",
    )

    mock_file = File(
        id=uuid.uuid4(),
        repository_id=repo_id,
        path="src/main.py",
        filename="main.py",
        extension=".py",
        line_count=80,
        metadata_={
            "risk_assessment": {
                "file": "src/main.py",
                "risk_score": 75,
                "risk_level": "HIGH",
                "top_factors": [],
                "disclaimer": "Maintenance risk only.",
            }
        },
    )

    mock_db.get.return_value = mock_repo
    mock_files_result = MagicMock()
    mock_files_result.scalars.return_value.all.return_value = [mock_file]
    mock_db.execute.return_value = mock_files_result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/repositories/{repo_id}/risk/files?risk_level=HIGH")
        assert resp.status_code == 200
        data = resp.json()

        assert data["repository_id"] == str(repo_id)
        assert len(data["files"]) == 1
        assert data["files"][0]["risk_level"] == "HIGH"

