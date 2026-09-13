"""
Unit and Integration Tests for Internal File Structure Parsing and Mermaid Diagrams
"""

import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.parser.file_structure_parser import analyze_file_structure

client = TestClient(app)

SAMPLE_PYTHON_CODE = '''"""Sample module for testing AST parsing."""

import os
import sys
from typing import List, Optional
from pydantic import BaseModel

class UserModel(BaseModel):
    """User data model."""
    username: str
    email: Optional[str] = None

    def get_display_name(self) -> str:
        return self.username

    def format_card(self) -> str:
        name = self.get_display_name()
        return helper_sanitize(name)

def helper_sanitize(text: str) -> str:
    return text.strip().lower()

def calculate_score(user: UserModel, points: int) -> int:
    clean_name = helper_sanitize(user.username)
    return len(clean_name) * points
'''

SAMPLE_TS_CODE = '''import React, { useState } from 'react';
import axios from 'axios';

export interface UserProps {
    id: string;
    name: string;
}

export class UserService {
    private token: string;
    constructor(token: string) {
        this.token = token;
    }

    public async fetchUser(id: string): Promise<UserProps> {
        return axios.get(`/users/${id}`);
    }
}

export const renderHeader = (title: string): string => {
    return `<h1>${title}</h1>`;
};
'''


def test_python_ast_parsing():
    """Verify that Python AST extracts classes, methods, functions, calls, and Mermaid syntax."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(SAMPLE_PYTHON_CODE)
        tmp_path = Path(tmp.name)

    try:
        data = analyze_file_structure(tmp_path, "sample.py")
        assert data["language"] == "python"
        metrics = data["metrics"]
        assert metrics["classes"] == 1
        assert metrics["methods"] == 2
        assert metrics["functions"] == 2
        assert metrics["imports"] == 4
        assert metrics["internal_calls"] >= 2

        # Verify Mermaid Flowchart Syntax
        flowchart = data["mermaid_syntax"]
        assert "flowchart TD" in flowchart
        assert "UserModel" in flowchart
        assert "helper_sanitize" in flowchart
        assert "calculate_score" in flowchart
        assert "==>|calls|" in flowchart

        # Verify Mermaid Class Diagram Syntax
        class_diag = data["class_diagram_syntax"]
        assert "classDiagram" in class_diag
        assert "UserModel" in class_diag
        assert "get_display_name" in class_diag
    finally:
        tmp_path.unlink(missing_ok=True)


def test_typescript_parsing():
    """Verify regex/polyglot parsing on TypeScript files."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False, encoding="utf-8") as tmp:
        tmp.write(SAMPLE_TS_CODE)
        tmp_path = Path(tmp.name)

    try:
        data = analyze_file_structure(tmp_path, "sample.ts")
        assert data["language"] == "typescript"
        metrics = data["metrics"]
        assert metrics["classes"] >= 1
        assert metrics["functions"] >= 1
        assert metrics["imports"] >= 1

        flowchart = data["mermaid_syntax"]
        assert "flowchart TD" in flowchart
        assert "UserService" in flowchart
        assert "renderHeader" in flowchart
    finally:
        tmp_path.unlink(missing_ok=True)


def test_api_security_path_traversal():
    """Verify security controls on the file-structure API."""
    # 1. Illegal characters in repository identifier
    res = client.get("/api/github/repositories/bad*repo!/file-structure?path=main.py")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_REPOSITORY_ID"

    # 2. Path traversal in file path
    res = client.get("/api/github/repositories/valid_repo/file-structure?path=../../etc/passwd")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] in ("INVALID_FILE_PATH", "PATH_TRAVERSAL_DETECTED")


def test_api_nonexistent_workspace():
    """Verify clean structured error when repository workspace does not exist."""
    res = client.get("/api/github/repositories/nonexistent_repo_999999/file-structure?path=main.py")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "REPOSITORY_NOT_FOUND"
