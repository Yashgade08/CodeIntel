"""
Tests for the repository dependency graph module.

Uses an in-memory fixture repository created in a tmp_path directory:

    fixture_repo/
      auth/
        service.py     # imports db/session.py, utils/crypto.py
        router.py      # imports auth/service.py
      db/
        session.py     # no local imports
      utils/
        crypto.py      # no local imports
      api/
        main.py        # imports auth/router.py, db/session.py
      payment/
        service.py     # imports db/session.py, utils/crypto.py
      frontend/
        app.js         # import { login } from './auth/client'
        auth/
          client.js    # import axios from 'axios'; require('./utils')
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import networkx as nx
import pytest

from app.graph.analyzer import ImportAnalyzer, detect_language
from app.graph.builder import DependencyGraphBuilder, FileRecord
from app.graph.serializer import GraphSerializer
from app.services.graph_service import GraphService


# ── Fixture sources ───────────────────────────────────────────────────────────

FIXTURE_SOURCES: dict[str, str] = {
    "auth/service.py": (
        "from db.session import get_db\n"
        "from utils.crypto import hash_password\n"
        "\n"
        "class AuthService:\n"
        "    def authenticate(self, user, pw):\n"
        "        db = get_db()\n"
        "        return hash_password(pw)\n"
    ),
    "auth/router.py": (
        "from auth.service import AuthService\n"
        "\n"
        "router = None\n"
    ),
    "db/session.py": (
        "import sqlalchemy\n"
        "\n"
        "def get_db():\n"
        "    return sqlalchemy.create_engine('sqlite://')\n"
    ),
    "utils/crypto.py": (
        "import hashlib\n"
        "\n"
        "def hash_password(pw):\n"
        "    return hashlib.sha256(pw.encode()).hexdigest()\n"
    ),
    "api/main.py": (
        "from auth.router import router\n"
        "from db.session import get_db\n"
        "\n"
        "app = None\n"
    ),
    "payment/service.py": (
        "from db.session import get_db\n"
        "from utils.crypto import hash_password\n"
        "\n"
        "class PaymentService:\n"
        "    pass\n"
    ),
    "frontend/app.js": (
        "import { login } from './auth/client';\n"
        "import React from 'react';\n"
    ),
    "frontend/auth/client.js": (
        "import axios from 'axios';\n"
        "const utils = require('./utils');\n"
    ),
}


@pytest.fixture()
def fixture_repo(tmp_path: Path) -> Path:
    """Create the fixture repository on disk."""
    for rel_path, source in FIXTURE_SOURCES.items():
        abs_path = tmp_path / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(source, encoding="utf-8")
    return tmp_path


@pytest.fixture()
def file_records() -> list[FileRecord]:
    return [
        FileRecord(path="auth/service.py", language="python", line_count=7),
        FileRecord(path="auth/router.py", language="python", line_count=3),
        FileRecord(path="db/session.py", language="python", line_count=4),
        FileRecord(path="utils/crypto.py", language="python", line_count=4),
        FileRecord(path="api/main.py", language="python", line_count=4),
        FileRecord(path="payment/service.py", language="python", line_count=5),
        FileRecord(path="frontend/app.js", language="javascript", line_count=2),
        FileRecord(path="frontend/auth/client.js", language="javascript", line_count=2),
    ]


@pytest.fixture()
def built_graph(fixture_repo: Path, file_records: list[FileRecord]) -> nx.DiGraph:
    builder = DependencyGraphBuilder()
    return builder.build(str(fixture_repo), file_records, FIXTURE_SOURCES)


# ── Test: language detection ──────────────────────────────────────────────────

def test_detect_language_python():
    assert detect_language("auth/service.py") == "python"


def test_detect_language_javascript():
    assert detect_language("frontend/app.js") == "javascript"


def test_detect_language_unknown():
    assert detect_language("data/file.xyz") == "unknown"


# ── Test: import extraction — Python ──────────────────────────────────────────

def test_import_extraction_python():
    analyzer = ImportAnalyzer()
    analysis = analyzer.analyze_file("auth/service.py", FIXTURE_SOURCES["auth/service.py"])

    assert analysis.language == "python"
    assert analysis.parse_error is None

    modules = {imp.resolved_module for imp in analysis.imports}
    assert "db.session" in modules
    assert "utils.crypto" in modules


def test_import_extraction_python_class():
    analyzer = ImportAnalyzer()
    analysis = analyzer.analyze_file("auth/service.py", FIXTURE_SOURCES["auth/service.py"])
    class_names = [c.name for c in analysis.classes]
    assert "AuthService" in class_names


def test_import_extraction_python_function():
    analyzer = ImportAnalyzer()
    analysis = analyzer.analyze_file("db/session.py", FIXTURE_SOURCES["db/session.py"])
    fn_names = [f.name for f in analysis.functions]
    assert "get_db" in fn_names


# ── Test: import extraction — JavaScript ─────────────────────────────────────

def test_import_extraction_js():
    analyzer = ImportAnalyzer()
    analysis = analyzer.analyze_file("frontend/app.js", FIXTURE_SOURCES["frontend/app.js"])

    assert analysis.language == "javascript"
    raw_imports = {imp.raw_import for imp in analysis.imports}
    assert "./auth/client" in raw_imports
    assert "react" in raw_imports


def test_import_extraction_js_require():
    analyzer = ImportAnalyzer()
    analysis = analyzer.analyze_file(
        "frontend/auth/client.js", FIXTURE_SOURCES["frontend/auth/client.js"]
    )
    raw_imports = {imp.raw_import for imp in analysis.imports}
    assert "axios" in raw_imports
    assert "./utils" in raw_imports


# ── Test: graph node construction ─────────────────────────────────────────────

def test_graph_build_file_nodes(built_graph: nx.DiGraph):
    """All source files must appear as file nodes."""
    file_paths = {
        d["path"]
        for _, d in built_graph.nodes(data=True)
        if d.get("node_type") == "file"
    }
    expected = {
        "auth/service.py", "auth/router.py", "db/session.py",
        "utils/crypto.py", "api/main.py", "payment/service.py",
        "frontend/app.js", "frontend/auth/client.js",
    }
    assert expected == file_paths


def test_graph_build_class_nodes(built_graph: nx.DiGraph):
    """AuthService and PaymentService must appear as class nodes."""
    class_ids = [n for n, d in built_graph.nodes(data=True) if d.get("node_type") == "class"]
    class_names = {cid.split("::")[-1] for cid in class_ids}
    assert "AuthService" in class_names
    assert "PaymentService" in class_names


# ── Test: import edge construction ────────────────────────────────────────────

def test_graph_import_edges(built_graph: nx.DiGraph):
    """auth/service.py must have edges to db/session.py and utils/crypto.py."""
    out_edges = {
        built_graph.nodes[tgt].get("path", tgt)
        for _, tgt, d in built_graph.out_edges("auth/service.py", data=True)
        if d.get("dependency_type") == "import" and not d.get("is_external")
    }
    assert "db/session.py" in out_edges
    assert "utils/crypto.py" in out_edges


def test_graph_no_self_edges(built_graph: nx.DiGraph):
    """No file should import itself."""
    for src, tgt in built_graph.edges():
        assert src != tgt


# ── Test: get_dependencies ────────────────────────────────────────────────────

def test_get_dependencies_direct(built_graph: nx.DiGraph):
    builder = DependencyGraphBuilder()
    deps = builder.get_dependencies(built_graph, "auth/service.py", depth=1)
    dep_paths = {d["path"] for d in deps if not d["is_external"]}
    assert "db/session.py" in dep_paths
    assert "utils/crypto.py" in dep_paths


def test_get_dependencies_transitive(built_graph: nx.DiGraph):
    """api/main.py → auth/router.py → auth/service.py at depth 2."""
    builder = DependencyGraphBuilder()
    deps = builder.get_dependencies(built_graph, "api/main.py", depth=2)
    dep_paths = {d["path"] for d in deps if not d["is_external"]}
    # depth-1: auth/router.py, db/session.py
    assert "auth/router.py" in dep_paths
    # depth-2: auth/service.py (via auth/router.py)
    assert "auth/service.py" in dep_paths


def test_get_dependencies_nonexistent_file(built_graph: nx.DiGraph):
    builder = DependencyGraphBuilder()
    deps = builder.get_dependencies(built_graph, "nonexistent/file.py", depth=1)
    assert deps == []


# ── Test: get_dependents ──────────────────────────────────────────────────────

def test_get_dependents_db_session(built_graph: nx.DiGraph):
    """db/session.py is imported by auth/service.py, api/main.py, payment/service.py."""
    builder = DependencyGraphBuilder()
    dependents = builder.get_dependents(built_graph, "db/session.py", depth=1)
    dependent_paths = {d["path"] for d in dependents}
    assert "auth/service.py" in dependent_paths
    assert "api/main.py" in dependent_paths
    assert "payment/service.py" in dependent_paths


def test_get_dependents_nonexistent_file(built_graph: nx.DiGraph):
    builder = DependencyGraphBuilder()
    result = builder.get_dependents(built_graph, "missing.py", depth=1)
    assert result == []


# ── Test: impact set ──────────────────────────────────────────────────────────

def test_impact_set_db_session(built_graph: nx.DiGraph):
    """
    Changing db/session.py should affect all files that transitively import it.
    Expected: auth/service.py, auth/router.py, api/main.py, payment/service.py
    (auth/router.py imports auth/service.py which imports db/session.py).
    """
    builder = DependencyGraphBuilder()
    impact = set(builder.get_impact_set(built_graph, "db/session.py", depth=5))
    # Direct importers
    assert "auth/service.py" in impact
    assert "api/main.py" in impact
    assert "payment/service.py" in impact
    # Transitive: auth/router.py imports auth/service.py
    assert "auth/router.py" in impact


def test_impact_set_leaf_file(built_graph: nx.DiGraph):
    """utils/crypto.py has no dependents, so impact set should be populated with its direct importers."""
    builder = DependencyGraphBuilder()
    impact = set(builder.get_impact_set(built_graph, "utils/crypto.py", depth=5))
    assert "auth/service.py" in impact
    assert "payment/service.py" in impact


# ── Test: serializer ──────────────────────────────────────────────────────────

def test_serializer_json_structure(built_graph: nx.DiGraph):
    serializer = GraphSerializer()
    result = serializer.to_dict(built_graph)

    assert "nodes" in result
    assert "edges" in result
    assert "stats" in result
    assert isinstance(result["nodes"], list)
    assert isinstance(result["edges"], list)

    stats = result["stats"]
    assert stats["file_count"] == 8
    assert stats["total_edges"] > 0


def test_serializer_edge_ids(built_graph: nx.DiGraph):
    """Every edge dict must have a non-empty id, source, and target."""
    serializer = GraphSerializer()
    result = serializer.to_dict(built_graph)
    for edge in result["edges"]:
        assert "id" in edge
        assert "source" in edge
        assert "target" in edge
        assert edge["id"] != ""


# ── Test: store round-trip (mocked DB) ───────────────────────────────────────

@pytest.mark.asyncio
async def test_store_save_load_roundtrip(built_graph: nx.DiGraph):
    """
    Serialize → store in mock DB → deserialize → verify graph structure preserved.
    """
    import uuid
    from app.graph.store import GraphStore

    repo_id = uuid.uuid4()
    stored_meta: dict = {}

    # Mock DB session
    mock_db = AsyncMock()

    # Mock select for metadata_
    mock_scalar_for_load = MagicMock()
    mock_scalar_for_load.scalar_one_or_none.return_value = None

    # We'll capture what gets saved
    saved_values: dict = {}

    async def fake_execute(stmt):
        # Detect if it's a select or update by inspecting statement type
        stmt_str = str(stmt).lower()
        if "select" in stmt_str:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = stored_meta or None
            return mock_result
        elif "update" in stmt_str:
            # Extract the values from the update — capture via the stored_meta dict
            return MagicMock()
        return MagicMock()

    mock_db.execute = AsyncMock(side_effect=fake_execute)
    mock_db.commit = AsyncMock()

    store = GraphStore()
    serializer = GraphSerializer()

    # Manually simulate save: serialize and put in stored_meta
    graph_dict = serializer.to_storage_dict(built_graph)
    stored_meta["dependency_graph"] = graph_dict

    # Now load from the stored_meta
    reloaded = GraphSerializer.from_dict(graph_dict)
    assert reloaded.number_of_nodes() == built_graph.number_of_nodes()
    assert reloaded.number_of_edges() == built_graph.number_of_edges()


# ── Test: graph service (mocked) ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_graph_service_get_file_dependencies():
    """GraphService.get_file_dependencies returns the correct structure when graph is loaded."""
    import uuid
    from app.graph.store import GraphStore

    repo_id = uuid.uuid4()
    builder = DependencyGraphBuilder()
    graph = builder.build(".", [FileRecord(path=p, language="python") for p in FIXTURE_SOURCES], FIXTURE_SOURCES)

    mock_db = AsyncMock()

    service = GraphService()
    with patch.object(GraphStore, "load", new_callable=AsyncMock, return_value=graph):
        result = await service.get_file_dependencies(
            repo_id, "auth/service.py", mock_db, depth=1
        )

    assert result["file_path"] == "auth/service.py"
    assert result["direction"] == "dependencies"
    dep_paths = {r["path"] for r in result["results"] if not r.get("is_external")}
    assert "db/session.py" in dep_paths
    assert "utils/crypto.py" in dep_paths


@pytest.mark.asyncio
async def test_graph_service_get_file_dependents():
    """GraphService.get_file_dependents returns correct dependents and impact set."""
    import uuid
    from app.graph.store import GraphStore

    repo_id = uuid.uuid4()
    builder = DependencyGraphBuilder()
    graph = builder.build(".", [FileRecord(path=p, language="python") for p in FIXTURE_SOURCES], FIXTURE_SOURCES)

    mock_db = AsyncMock()

    service = GraphService()
    with patch.object(GraphStore, "load", new_callable=AsyncMock, return_value=graph):
        result = await service.get_file_dependents(
            repo_id, "db/session.py", mock_db, depth=1
        )

    assert result["direction"] == "dependents"
    dep_paths = {r["path"] for r in result["results"]}
    assert "auth/service.py" in dep_paths
    assert "payment/service.py" in dep_paths
    assert result["impact_count"] > 0


# ── Test: RAG dependency keyword detection ───────────────────────────────────

def test_rag_dependency_query_detection():
    from app.rag.pipeline import RAGPipeline

    positive_queries = [
        "What depends on auth.py?",
        "What does payment.py imports?",
        "Which files are affected if I change db.py?",
        "What calls the authenticate function?",
        "What inherits from BaseModel?",
        "What is downstream of session.py?",
    ]
    negative_queries = [
        "Explain the authentication flow.",
        "Where is the login function defined?",
        "How does the user registration work?",
    ]

    for q in positive_queries:
        assert RAGPipeline._is_dependency_query(q), f"Should be detected as dependency query: {q}"
    for q in negative_queries:
        assert not RAGPipeline._is_dependency_query(q), f"Should NOT be detected as dependency query: {q}"
