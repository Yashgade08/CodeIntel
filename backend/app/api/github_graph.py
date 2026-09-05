"""
GET /api/github/repositories/{repository_id}/structure-graph

Generates a structured, beautiful Mermaid.js diagram representing the repository's
framework architecture, module relationships, and directory hierarchy.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/github", tags=["github-graph"])

WORKSPACE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "workspace"

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
}


def _detect_frameworks(repo_dir: Path) -> list[str]:
    """Detect key frameworks and technologies present in the repository."""
    detected = []

    # Check for Python frameworks
    pyproject = repo_dir / "pyproject.toml"
    reqs = repo_dir / "requirements.txt"
    all_py_text = ""
    if pyproject.exists():
        all_py_text += pyproject.read_text(encoding="utf-8", errors="ignore")
    if reqs.exists():
        all_py_text += reqs.read_text(encoding="utf-8", errors="ignore")

    all_py_lower = all_py_text.lower()
    if "fastapi" in all_py_lower:
        detected.append("FastAPI")
    elif "flask" in all_py_lower:
        detected.append("Flask")
    elif "django" in all_py_lower:
        detected.append("Django")

    # Check for JS/TS frameworks
    pkg_json = repo_dir / "package.json"
    frontend_pkg = repo_dir / "frontend" / "package.json"
    js_text = ""
    if pkg_json.exists():
        js_text += pkg_json.read_text(encoding="utf-8", errors="ignore")
    if frontend_pkg.exists():
        js_text += frontend_pkg.read_text(encoding="utf-8", errors="ignore")

    js_lower = js_text.lower()
    if "react" in js_lower:
        detected.append("React")
    if "next" in js_lower:
        detected.append("Next.js")
    if "vue" in js_lower:
        detected.append("Vue")
    if "vite" in js_lower:
        detected.append("Vite")

    # Check for other languages
    if (repo_dir / "go.mod").exists():
        detected.append("Go")
    if (repo_dir / "Cargo.toml").exists():
        detected.append("Rust")
    if (repo_dir / "pom.xml").exists() or (repo_dir / "build.gradle").exists():
        detected.append("Java")

    return detected or ["Generic Project"]


def _sanitize_id(name: str) -> str:
    """Sanitize strings for Mermaid node IDs."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)


def generate_mermaid_structure(repo_dir: Path, repo_name: str) -> dict[str, Any]:
    """
    Scans the repository directory and generates a Mermaid diagram syntax
    visualizing the architectural modules and project layout.
    """
    frameworks = _detect_frameworks(repo_dir)

    # Collect top-level folders and significant second-level folders
    top_items = []
    sub_modules: dict[str, list[str]] = {}

    for item in repo_dir.iterdir():
        if item.name.startswith(".") or item.name.lower() in EXCLUDED_DIRS:
            continue

        if item.is_dir():
            top_items.append(item.name)
            sub_items = []
            try:
                for sub in item.iterdir():
                    if not sub.name.startswith(".") and sub.name.lower() not in EXCLUDED_DIRS:
                        sub_items.append(sub.name)
            except Exception:
                pass
            sub_modules[item.name] = sorted(sub_items)[:12]  # Cap at top 12 children
        else:
            top_items.append(item.name)

    # Build Mermaid syntax
    root_id = _sanitize_id(repo_name)
    lines = [
        "%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#0284c7', 'edgeLabelBackground':'#0f172a', 'tertiaryColor': '#1e293b'}}}%%",
        "flowchart TD",
        f'  ROOT(["📦 {repo_name}"])',
        '  style ROOT fill:#0369a1,stroke:#38bdf8,stroke-width:2px,color:#ffffff',
    ]

    # Add primary subgraphs or nodes
    for idx, folder in enumerate(sorted(sub_modules.keys())):
        node_id = f"SUB_{_sanitize_id(folder)}"
        children = sub_modules[folder]

        # Categorize icon
        icon = "📁"
        lower_f = folder.lower()
        if "backend" in lower_f or "api" in lower_f or "server" in lower_f:
            icon = "⚡"
        elif "frontend" in lower_f or "ui" in lower_f or "client" in lower_f or "web" in lower_f:
            icon = "🌐"
        elif "test" in lower_f:
            icon = "🧪"
        elif "doc" in lower_f:
            icon = "📖"
        elif "core" in lower_f or "util" in lower_f:
            icon = "⚙️"
        elif "db" in lower_f or "model" in lower_f or "storage" in lower_f:
            icon = "🗄️"

        if children:
            lines.append(f'  subgraph {node_id} ["{icon} {folder}"]')
            for c_idx, child in enumerate(children[:6]):
                c_id = f"{node_id}_{_sanitize_id(child)}"
                c_icon = "📁" if (repo_dir / folder / child).is_dir() else "📄"
                lines.append(f'    {c_id}["{c_icon} {child}"]')
            lines.append("  end")
            lines.append(f"  ROOT --> {node_id}")
        else:
            lines.append(f'  {node_id}["{icon} {folder}"]')
            lines.append(f"  ROOT --> {node_id}")

    # Connect top-level standalone files (e.g. README.md, docker-compose.yml, package.json)
    root_files = [f for f in top_items if (repo_dir / f).is_file() and f.lower() in ("readme.md", "docker-compose.yml", "package.json", "pyproject.toml", "makefile", ".env.example")]
    if root_files:
        lines.append('  subgraph CONFIG ["⚙️ Root Config & Specs"]')
        for rf in root_files[:5]:
            rf_id = f"ROOT_FILE_{_sanitize_id(rf)}"
            lines.append(f'    {rf_id}["📄 {rf}"]')
        lines.append("  end")
        lines.append("  ROOT -.-> CONFIG")

    mermaid_syntax = "\n".join(lines)

    return {
        "frameworks": frameworks,
        "mermaid_syntax": mermaid_syntax,
        "top_modules": sorted(sub_modules.keys()),
    }


@router.get("/repositories/{repository_id}/structure-graph")
def get_repository_structure_graph(repository_id: str) -> dict:
    """
    Returns Mermaid graph definition representing the structure and framework
    of the cloned repository.
    """
    clean_id = (repository_id or "").strip()
    if not clean_id or not re.match(r"^[a-zA-Z0-9_\-\.]+$", clean_id) or ".." in clean_id:
        return {
            "success": False,
            "error": {
                "code": "INVALID_REPOSITORY_ID",
                "layer": "graph",
                "message": "Invalid repository workspace identifier.",
                "root_cause": "Repository identifier contains invalid characters or path traversal.",
                "fix": "Provide a valid repository identifier.",
            },
        }

    resolved_base = WORKSPACE_BASE_DIR.resolve()
    target_dir = (resolved_base / clean_id).resolve()

    if target_dir.parent != resolved_base:
        return {
            "success": False,
            "error": {
                "code": "INVALID_REPOSITORY_ID",
                "layer": "graph",
                "message": "Path traversal attempt detected.",
                "root_cause": "The requested repository path escapes the designated workspace directory.",
                "fix": "Only access repositories managed inside the application workspace.",
            },
        }

    if not target_dir.exists() or not target_dir.is_dir():
        return {
            "success": False,
            "error": {
                "code": "REPOSITORY_NOT_FOUND",
                "layer": "graph",
                "message": f"Repository workspace '{clean_id}' was not found.",
                "root_cause": f"No cloned directory exists at: {target_dir}",
                "fix": "Clone the repository before generating its structure graph.",
            },
        }

    try:
        parts = clean_id.split("_")
        repo_display = f"{parts[0]}/{parts[1]}" if len(parts) >= 2 else clean_id
        graph_data = generate_mermaid_structure(target_dir, repo_display)
        return {
            "success": True,
            "repository_id": clean_id,
            "repository_name": repo_display,
            "frameworks": graph_data["frameworks"],
            "top_modules": graph_data["top_modules"],
            "mermaid_syntax": graph_data["mermaid_syntax"],
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "GRAPH_GENERATION_FAILED",
                "layer": "graph",
                "message": "Failed to generate project structure graph.",
                "root_cause": str(e),
                "fix": "Check repository file permissions.",
            },
        }


@router.get("/workspaces")
def list_cloned_workspaces() -> dict:
    """
    Returns a list of all currently cloned repository workspaces.
    """
    resolved_base = WORKSPACE_BASE_DIR.resolve()
    if not resolved_base.exists():
        return {"success": True, "workspaces": []}

    workspaces = []
    for item in resolved_base.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            parts = item.name.split("_")
            repo_display = f"{parts[0]}/{parts[1]}" if len(parts) >= 2 else item.name
            try:
                frameworks = _detect_frameworks(item)
                mtime = item.stat().st_mtime
            except Exception:
                frameworks = ["Generic Project"]
                mtime = 0

            workspaces.append({
                "workspace_id": item.name,
                "repository_name": repo_display,
                "frameworks": frameworks,
                "created_at": mtime,
            })

    workspaces.sort(key=lambda w: w["created_at"], reverse=True)
    return {"success": True, "workspaces": workspaces}

