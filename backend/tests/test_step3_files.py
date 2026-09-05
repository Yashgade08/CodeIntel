"""
Step 3 Test Suite: File Scanner & Repository Isolation

Tests:
1. File scanning endpoint on cloned repositories:
   - https://github.com/psf/requests
   - https://github.com/fastapi/fastapi
   - https://github.com/pallets/flask
2. File discovery, directory counting, language summary.
3. Path exclusion tests (.git, __pycache__, node_modules, etc.).
4. Security & Path Traversal prevention.
5. Error responses for non-existent repositories.
6. Mandatory Cross-Repository Isolation:
   - Clone Repo A -> Scan Repo A -> Record files
   - Clone Repo B -> Scan Repo B -> Verify only Repo B files
   - Re-scan Repo A -> Verify only Repo A files remain
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_invalid_repository_id_security():
    """Security: verify path traversal and illegal identifiers are rejected."""
    # 1. Illegal characters in identifier
    res = client.get("/api/github/repositories/invalid*name/files")
    assert res.status_code in (200, 400, 422)
    if res.status_code == 200:
        data = res.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_REPOSITORY_ID"

    # 2. Path traversal attempts
    res_encoded = client.get("/api/github/repositories/..%2F..%2Fetc/files")
    assert res_encoded.status_code in (200, 404)
    if res_encoded.status_code == 200:
        data = res_encoded.json()
        assert data["success"] is False

    # 3. Double dot in identifier
    res_dot = client.get("/api/github/repositories/..workspace/files")
    assert res_dot.status_code in (200, 404)
    if res_dot.status_code == 200:
        data = res_dot.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_REPOSITORY_ID"


def test_nonexistent_repository_id():
    """Verify clean structured error when repository workspace does not exist."""
    res = client.get("/api/github/repositories/nonexistent_repo_9999999_abcdef/files")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "REPOSITORY_NOT_FOUND"
    assert data["error"]["layer"] == "file_scanner"
    assert "not found" in data["error"]["message"].lower()


@pytest.mark.parametrize(
    "repo_url,expected_owner,expected_name",
    [
        ("https://github.com/psf/requests", "psf", "requests"),
        ("https://github.com/fastapi/fastapi", "fastapi", "fastapi"),
        ("https://github.com/pallets/flask", "pallets", "flask"),
    ],
)
def test_clone_and_scan_repositories(repo_url, expected_owner, expected_name):
    """
    Test cloning and scanning:
    - psf/requests
    - fastapi/fastapi
    - pallets/flask
    """
    # 1. Clone repository
    clone_res = client.post("/api/github/clone", json={"url": repo_url})
    clone_data = clone_res.json()
    assert clone_data["success"] is True, f"Failed to clone {repo_url}: {clone_data}"

    workspace_id = clone_data["clone"]["workspace_id"]
    assert workspace_id
    assert clone_data["repository"]["owner"].lower() == expected_owner.lower()
    assert clone_data["repository"]["name"].lower() == expected_name.lower()

    # 2. Scan repository files
    files_res = client.get(f"/api/github/repositories/{workspace_id}/files")
    files_data = files_res.json()

    assert files_data["success"] is True
    assert files_data["repository"]["workspace_id"] == workspace_id
    assert files_data["repository"]["owner"].lower() == expected_owner.lower()
    assert files_data["repository"]["name"].lower() == expected_name.lower()

    # 3. File discovery assertions
    files = files_data["files"]
    assert files["total"] > 0
    assert files["directories"] > 0
    assert len(files["items"]) == files["total"]
    assert isinstance(files["summary"], dict)
    assert len(files["summary"]) > 0

    # 4. Exclusion checks: NO .git/, NO node_modules/, NO __pycache__/
    for item in files["items"]:
        path_lower = item["path"].lower()
        assert not path_lower.startswith(".git/"), f".git was not excluded: {item['path']}"
        assert not path_lower.startswith(".git\\"), f".git was not excluded: {item['path']}"
        assert not path_lower.startswith("node_modules/"), f"node_modules was not excluded: {item['path']}"
        assert "__pycache__" not in path_lower, f"__pycache__ was not excluded: {item['path']}"
        assert ".pytest_cache" not in path_lower, f".pytest_cache was not excluded: {item['path']}"
        assert item["type"] == "file"
        assert isinstance(item["size"], int)
        assert item["size"] >= 0


def test_cross_repository_isolation():
    """
    MANDATORY CROSS-REPOSITORY TEST:
    1. Clone Repository A (psf/requests).
    2. Scan Repository A. Record its files.
    3. Then clone Repository B (pallets/flask).
    4. Scan Repository B. Verify that the response contains ONLY Repository B files.
    5. Then scan Repository A again. Verify that Repository A still returns ONLY Repository A files.
    """
    # ── Step 1 & 2: Clone & Scan Repo A (psf/requests) ──────────────────
    res_a_clone = client.post("/api/github/clone", json={"url": "https://github.com/psf/requests"})
    data_a_clone = res_a_clone.json()
    assert data_a_clone["success"] is True
    workspace_a = data_a_clone["clone"]["workspace_id"]

    res_a_scan1 = client.get(f"/api/github/repositories/{workspace_a}/files")
    data_a_scan1 = res_a_scan1.json()
    assert data_a_scan1["success"] is True

    files_a_scan1 = {item["path"] for item in data_a_scan1["files"]["items"]}
    total_a_scan1 = data_a_scan1["files"]["total"]
    assert total_a_scan1 > 0

    # Verify Repo A contains requests core package files
    assert any("src/requests/" in p for p in files_a_scan1) or any("requests/" in p for p in files_a_scan1)

    # ── Step 3 & 4: Clone & Scan Repo B (pallets/flask) ─────────────────
    res_b_clone = client.post("/api/github/clone", json={"url": "https://github.com/pallets/flask"})
    data_b_clone = res_b_clone.json()
    assert data_b_clone["success"] is True
    workspace_b = data_b_clone["clone"]["workspace_id"]
    assert workspace_a != workspace_b

    res_b_scan = client.get(f"/api/github/repositories/{workspace_b}/files")
    data_b_scan = res_b_scan.json()
    assert data_b_scan["success"] is True

    files_b_scan = {item["path"] for item in data_b_scan["files"]["items"]}
    total_b_scan = data_b_scan["files"]["total"]
    assert total_b_scan > 0

    # Verify Repo B has its own specific files (e.g. src/flask/app.py)
    # and Repo B does NOT contain Repo A core files
    assert any("src/flask/app.py" in p for p in files_b_scan) or any("flask/app.py" in p for p in files_b_scan)
    assert not any("src/requests/sessions.py" in p for p in files_b_scan)
    assert not any("src/requests/api.py" in p for p in files_b_scan)

    # ── Step 5: Re-scan Repo A ──────────────────────────────────────────
    res_a_scan2 = client.get(f"/api/github/repositories/{workspace_a}/files")
    data_a_scan2 = res_a_scan2.json()
    assert data_a_scan2["success"] is True

    files_a_scan2 = {item["path"] for item in data_a_scan2["files"]["items"]}
    total_a_scan2 = data_a_scan2["files"]["total"]

    # Verify Repo A is completely identical and isolated
    assert total_a_scan1 == total_a_scan2
    assert files_a_scan1 == files_a_scan2
    assert not any("src/flask/app.py" in p for p in files_a_scan2)
    assert not any("src/flask/blueprints.py" in p for p in files_a_scan2)
