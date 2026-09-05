"""
Feature extraction module for Code Risk Intelligence.
Calculates software engineering complexity, size, dependencies, and VCS historical metrics.
Implemented separately from model training.
"""

from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


FEATURE_NAMES = [
    "lines_of_code",
    "cyclomatic_complexity",
    "number_of_functions",
    "number_of_classes",
    "dependency_count",
    "number_of_imports",
    "code_churn",
    "commit_frequency",
    "number_of_contributors",
    "historical_issue_count",
]


@dataclass
class CodeFeatures:
    """Extracted software engineering metrics for a source file."""
    lines_of_code: int
    cyclomatic_complexity: int
    number_of_functions: int
    number_of_classes: int
    dependency_count: int
    number_of_imports: int
    code_churn: int
    commit_frequency: int
    number_of_contributors: int
    historical_issue_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_vector(self) -> list[float]:
        return [
            float(self.lines_of_code),
            float(self.cyclomatic_complexity),
            float(self.number_of_functions),
            float(self.number_of_classes),
            float(self.dependency_count),
            float(self.number_of_imports),
            float(self.code_churn),
            float(self.commit_frequency),
            float(self.number_of_contributors),
            float(self.historical_issue_count),
        ]


def calculate_cyclomatic_complexity_python(code: str) -> tuple[int, int, int, int, int]:
    """
    Parse Python code via AST to extract:
    (cyclomatic_complexity, num_functions, num_classes, num_imports, num_dependencies)
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return _regex_fallback_analysis(code)

    complexity = 1
    num_functions = 0
    num_classes = 0
    num_imports = 0
    dependencies: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            num_functions += 1
        elif isinstance(node, ast.ClassDef):
            num_classes += 1
        elif isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler, ast.With, ast.AsyncWith, ast.Assert)):
            complexity += 1
        elif isinstance(node, ast.IfExp):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
        elif isinstance(node, ast.Import):
            num_imports += 1
            for alias in node.names:
                dependencies.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            num_imports += 1
            if node.module:
                dependencies.add(node.module.split(".")[0])

    return complexity, num_functions, num_classes, num_imports, len(dependencies)


def _regex_fallback_analysis(code: str) -> tuple[int, int, int, int, int]:
    """
    Polyglot pattern-matching fallback for non-Python or unparseable source files.
    """
    complexity = 1
    # Control flow keywords
    branch_pattern = re.compile(r"\b(if|elif|else if|while|for|catch|case|switch)\b|&&|\|\||\?")
    complexity += len(branch_pattern.findall(code))

    # Function declarations
    fn_pattern = re.compile(
        r"(?:(?:def|function|fn|func)\s+\w+)|(?:\b\w+\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)|(?:(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*\{)",
        re.MULTILINE,
    )
    num_functions = len(fn_pattern.findall(code))

    # Class / Interface / Struct declarations
    class_pattern = re.compile(r"\b(?:class|interface|struct|enum|type\s+\w+\s+struct)\s+\w+", re.MULTILINE)
    num_classes = len(class_pattern.findall(code))

    # Imports / Includes
    import_pattern = re.compile(
        r"^(?:\s*import\s+.+|\s*from\s+.+\s+import\s+.+|#include\s+[<\"].+[>\"]|\s*const\s+.*=\s*require\(.+\)|\s*use\s+.+;)",
        re.MULTILINE,
    )
    import_matches = import_pattern.findall(code)
    num_imports = len(import_matches)

    # Approximate distinct dependencies from import statements
    dependencies: set[str] = set()
    for imp in import_matches:
        parts = re.findall(r"['\"]([^'\"]+)['\"]", imp)
        for part in parts:
            pkg = part.split("/")[0].replace("@", "")
            dependencies.add(pkg)
    num_deps = max(len(dependencies), min(num_imports, 10))

    return complexity, num_functions, num_classes, num_imports, num_deps


def extract_git_metrics(file_path: str, repo_root: Path | None = None) -> tuple[int, int, int]:
    """
    Extract (code_churn, commit_frequency, number_of_contributors) from git history if available.
    Falls back cleanly to baseline defaults if git is unavailable or path is not a repo.
    """
    if not repo_root or not (repo_root / ".git").exists():
        return 0, 1, 1

    try:
        import subprocess
        # Get commit count & authors
        result = subprocess.run(
            ["git", "log", "--follow", "--format=%an", "--", file_path],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            authors = set(result.stdout.strip().splitlines())
            commit_freq = len(result.stdout.strip().splitlines())
            num_authors = max(1, len(authors))
        else:
            commit_freq, num_authors = 1, 1

        # Get churn (lines added + lines deleted)
        diff_result = subprocess.run(
            ["git", "log", "--follow", "--numstat", "--format=", "--", file_path],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        churn = 0
        if diff_result.returncode == 0 and diff_result.stdout.strip():
            for line in diff_result.stdout.strip().splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                    churn += int(parts[0]) + int(parts[1])

        return churn, commit_freq, num_authors
    except Exception:
        return 0, 1, 1


def extract_code_features(
    file_path: str,
    content: str,
    repo_root: Path | None = None,
    churn: int | None = None,
    commit_frequency: int | None = None,
    contributors: int | None = None,
    historical_issues: int = 0,
) -> CodeFeatures:
    """
    Main feature extraction entry point.
    Calculates code complexity, AST statistics, and VCS history for a source file.
    """
    lines = content.splitlines()
    loc = len([line for line in lines if line.strip() and not line.strip().startswith(("#", "//", "/*", "*"))])
    if loc == 0:
        loc = max(1, len(lines))

    # Detect language by extension
    is_python = file_path.endswith((".py", ".pyw"))

    if is_python:
        cc, n_funcs, n_classes, n_imports, n_deps = calculate_cyclomatic_complexity_python(content)
    else:
        cc, n_funcs, n_classes, n_imports, n_deps = _regex_fallback_analysis(content)

    # Git metrics: prioritize explicit inputs if provided, else attempt git repo discovery
    if churn is not None and commit_frequency is not None and contributors is not None:
        g_churn, g_freq, g_contrib = churn, commit_frequency, contributors
    else:
        g_churn, g_freq, g_contrib = extract_git_metrics(file_path, repo_root)
        if churn is not None:
            g_churn = churn
        if commit_frequency is not None:
            g_freq = commit_frequency
        if contributors is not None:
            g_contrib = contributors

    return CodeFeatures(
        lines_of_code=loc,
        cyclomatic_complexity=max(1, cc),
        number_of_functions=n_funcs,
        number_of_classes=n_classes,
        dependency_count=n_deps,
        number_of_imports=n_imports,
        code_churn=max(0, g_churn),
        commit_frequency=max(1, g_freq),
        number_of_contributors=max(1, g_contrib),
        historical_issue_count=max(0, historical_issues),
    )
