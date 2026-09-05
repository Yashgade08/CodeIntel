"""
Import and symbol analyzer for dependency graph construction.

Extracts:
- Import statements (file-to-file and file-to-external-module)
- Class definitions (name, base classes, line range)
- Function/method definitions (name, class context, line range)

Supports:
  Python      — ast.parse (full fidelity)
  JS / TS     — regex (import/require)
  Java        — regex (import statements)
  Go          — regex (import blocks)
  Rust        — regex (use statements)
  C / C++     — regex (#include)
  Fallback    — generic import/include patterns
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class ImportRecord:
    """A single import statement extracted from a file."""
    raw_import: str           # original import string as written
    resolved_module: str      # canonical dotted module or file path (best-effort)
    is_relative: bool = False
    is_external: bool = False  # True when we cannot resolve to a local file
    import_type: str = "import"  # "import" | "from_import" | "require" | "include"


@dataclass
class ClassRecord:
    """A class definition extracted from a file."""
    name: str
    bases: list[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0


@dataclass
class FunctionRecord:
    """A function or method definition extracted from a file."""
    name: str
    class_name: str | None = None   # set if method
    start_line: int = 0
    end_line: int = 0
    is_async: bool = False


@dataclass
class FileAnalysis:
    """Complete analysis result for a single source file."""
    file_path: str                          # relative path within repo
    language: str
    imports: list[ImportRecord] = field(default_factory=list)
    classes: list[ClassRecord] = field(default_factory=list)
    functions: list[FunctionRecord] = field(default_factory=list)
    parse_error: str | None = None


# ── Language detection ─────────────────────────────────────────────────────

_EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
}


def detect_language(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return _EXT_TO_LANG.get(ext, "unknown")


# ── Python AST analysis ────────────────────────────────────────────────────

def _analyse_python(file_path: str, source: str) -> FileAnalysis:
    result = FileAnalysis(file_path=file_path, language="python")
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as exc:
        result.parse_error = str(exc)
        # Fall back to regex on syntax error
        return _regex_fallback_python(file_path, source, result)

    # Import visitor
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.imports.append(ImportRecord(
                    raw_import=alias.name,
                    resolved_module=alias.name,
                    is_relative=False,
                    import_type="import",
                ))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = node.level or 0
            raw = ("." * level) + module
            result.imports.append(ImportRecord(
                raw_import=raw,
                resolved_module=module,
                is_relative=level > 0,
                import_type="from_import",
            ))

    # Class definitions
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    bases.append(b.id)
                elif isinstance(b, ast.Attribute):
                    bases.append(f"{ast.unparse(b)}")
            end_line = max((getattr(n, "lineno", node.lineno) for n in ast.walk(node)), default=node.lineno)
            result.classes.append(ClassRecord(
                name=node.name,
                bases=bases,
                start_line=node.lineno,
                end_line=end_line,
            ))

    # Function / method definitions (top-level + class methods)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_line = max((getattr(n, "lineno", node.lineno) for n in ast.walk(node)), default=node.lineno)
            result.functions.append(FunctionRecord(
                name=node.name,
                start_line=node.lineno,
                end_line=end_line,
                is_async=isinstance(node, ast.AsyncFunctionDef),
            ))

    return result


def _regex_fallback_python(file_path: str, source: str, result: FileAnalysis) -> FileAnalysis:
    """Minimal regex-based Python import extraction when AST fails."""
    for m in re.finditer(r"^import\s+([\w.,\s]+)", source, re.MULTILINE):
        for mod in m.group(1).split(","):
            mod = mod.strip().split(" as ")[0].strip()
            if mod:
                result.imports.append(ImportRecord(raw_import=mod, resolved_module=mod))
    for m in re.finditer(r"^from\s+(\.+[\w.]*|[\w.]+)\s+import", source, re.MULTILINE):
        raw = m.group(1)
        result.imports.append(ImportRecord(raw_import=raw, resolved_module=raw.lstrip(".")))
    return result


# ── JavaScript / TypeScript ────────────────────────────────────────────────

_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+.*?from\s+['"](?P<esm>[^'"]+)['"]|"""
    r"""require\s*\(\s*['"](?P<cjs>[^'"]+)['"]\s*\))""",
    re.MULTILINE,
)
_JS_EXPORT_RE = re.compile(r"export\s+(?:default\s+)?(?:class|function)\s+(\w+)", re.MULTILINE)
_JS_CLASS_RE  = re.compile(r"class\s+(\w+)(?:\s+extends\s+(\w+))?", re.MULTILINE)
_JS_FUNC_RE   = re.compile(
    r"(?:(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\()",
    re.MULTILINE,
)


def _analyse_js(file_path: str, source: str) -> FileAnalysis:
    result = FileAnalysis(file_path=file_path, language=detect_language(file_path))
    for m in _JS_IMPORT_RE.finditer(source):
        raw = m.group("esm") or m.group("cjs") or ""
        imp_type = "import" if m.group("esm") else "require"
        result.imports.append(ImportRecord(
            raw_import=raw,
            resolved_module=raw,
            is_relative=raw.startswith("."),
            import_type=imp_type,
        ))
    for m in _JS_CLASS_RE.finditer(source):
        result.classes.append(ClassRecord(
            name=m.group(1),
            bases=[m.group(2)] if m.group(2) else [],
        ))
    for m in _JS_FUNC_RE.finditer(source):
        name = m.group(1) or m.group(2)
        if name:
            result.functions.append(FunctionRecord(name=name))
    return result


# ── Java ──────────────────────────────────────────────────────────────────────

_JAVA_IMPORT_RE = re.compile(r"^import\s+(?:static\s+)?([\w.]+)(?:\.\*)?;", re.MULTILINE)
_JAVA_CLASS_RE  = re.compile(r"(?:public|private|protected|abstract|final)?\s*class\s+(\w+)(?:\s+extends\s+(\w+))?", re.MULTILINE)
_JAVA_METHOD_RE = re.compile(
    r"(?:public|private|protected|static|final|abstract|synchronized|native)[\w\s<>\[\]@]+\s+(\w+)\s*\(", re.MULTILINE
)


def _analyse_java(file_path: str, source: str) -> FileAnalysis:
    result = FileAnalysis(file_path=file_path, language="java")
    for m in _JAVA_IMPORT_RE.finditer(source):
        raw = m.group(1)
        result.imports.append(ImportRecord(raw_import=raw, resolved_module=raw))
    for m in _JAVA_CLASS_RE.finditer(source):
        result.classes.append(ClassRecord(
            name=m.group(1),
            bases=[m.group(2)] if m.group(2) else [],
        ))
    return result


# ── Go ────────────────────────────────────────────────────────────────────────

_GO_IMPORT_SINGLE_RE = re.compile(r'^import\s+"([^"]+)"', re.MULTILINE)
_GO_IMPORT_BLOCK_RE  = re.compile(r'"([^"]+)"', re.MULTILINE)
_GO_IMPORT_GROUP_RE  = re.compile(r"import\s+\(([^)]+)\)", re.DOTALL)
_GO_FUNC_RE          = re.compile(r"^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(", re.MULTILINE)


def _analyse_go(file_path: str, source: str) -> FileAnalysis:
    result = FileAnalysis(file_path=file_path, language="go")
    for m in _GO_IMPORT_SINGLE_RE.finditer(source):
        result.imports.append(ImportRecord(raw_import=m.group(1), resolved_module=m.group(1)))
    for block_m in _GO_IMPORT_GROUP_RE.finditer(source):
        block = block_m.group(1)
        for m in _GO_IMPORT_BLOCK_RE.finditer(block):
            result.imports.append(ImportRecord(raw_import=m.group(1), resolved_module=m.group(1)))
    for m in _GO_FUNC_RE.finditer(source):
        result.functions.append(FunctionRecord(name=m.group(1)))
    return result


# ── Rust ──────────────────────────────────────────────────────────────────────

_RUST_USE_RE  = re.compile(r"^use\s+([\w::{},\s*]+);", re.MULTILINE)
_RUST_FN_RE   = re.compile(r"^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)", re.MULTILINE)
_RUST_STRUCT_RE = re.compile(r"^(?:pub\s+)?struct\s+(\w+)", re.MULTILINE)


def _analyse_rust(file_path: str, source: str) -> FileAnalysis:
    result = FileAnalysis(file_path=file_path, language="rust")
    for m in _RUST_USE_RE.finditer(source):
        raw = m.group(1).strip()
        # Resolve top-level crate name
        module = raw.split("::")[0].strip()
        result.imports.append(ImportRecord(raw_import=raw, resolved_module=module))
    for m in _RUST_FN_RE.finditer(source):
        result.functions.append(FunctionRecord(name=m.group(1)))
    for m in _RUST_STRUCT_RE.finditer(source):
        result.classes.append(ClassRecord(name=m.group(1)))
    return result


# ── C / C++ ───────────────────────────────────────────────────────────────────

_C_INCLUDE_RE = re.compile(r'#include\s+[<"]([^>"]+)[>"]', re.MULTILINE)


def _analyse_c(file_path: str, source: str) -> FileAnalysis:
    result = FileAnalysis(file_path=file_path, language=detect_language(file_path))
    for m in _C_INCLUDE_RE.finditer(source):
        raw = m.group(1)
        result.imports.append(ImportRecord(
            raw_import=raw,
            resolved_module=raw,
            import_type="include",
        ))
    return result


# ── Generic fallback ──────────────────────────────────────────────────────────

_GENERIC_IMPORT_RE = re.compile(
    r"^(?:import|require|include|use|from)\s+['\"]?([^\s;'\"]+)['\"]?",
    re.MULTILINE | re.IGNORECASE,
)


def _analyse_generic(file_path: str, source: str) -> FileAnalysis:
    result = FileAnalysis(file_path=file_path, language=detect_language(file_path))
    for m in _GENERIC_IMPORT_RE.finditer(source):
        raw = m.group(1)
        result.imports.append(ImportRecord(raw_import=raw, resolved_module=raw))
    return result


# ── Main dispatcher ───────────────────────────────────────────────────────────

_ANALYSERS = {
    "python":     _analyse_python,
    "javascript": _analyse_js,
    "typescript": _analyse_js,
    "java":       _analyse_java,
    "go":         _analyse_go,
    "rust":       _analyse_rust,
    "c":          _analyse_c,
    "cpp":        _analyse_c,
}


class ImportAnalyzer:
    """
    Analyse source files to extract import relationships and symbol definitions.

    Usage::

        analyzer = ImportAnalyzer()
        analysis = analyzer.analyze_file("auth/service.py", source_code)
        for imp in analysis.imports:
            print(imp.resolved_module)
    """

    def analyze_file(self, file_path: str, source: str) -> FileAnalysis:
        """Analyse a single file. Returns FileAnalysis; never raises."""
        lang = detect_language(file_path)
        analyser_fn = _ANALYSERS.get(lang, _analyse_generic)
        try:
            return analyser_fn(file_path, source)
        except Exception as exc:
            logger.warning("Import analysis failed", file=file_path, error=str(exc))
            return FileAnalysis(file_path=file_path, language=lang, parse_error=str(exc))

    def analyze_directory(
        self, repo_path: str, file_paths: list[str], source_map: dict[str, str]
    ) -> list[FileAnalysis]:
        """
        Analyse all files in a list.

        Args:
            repo_path:  Absolute root of the repository on disk.
            file_paths: Relative paths within the repo.
            source_map: Map of relative_path → source_code.
        """
        results: list[FileAnalysis] = []
        for rel_path in file_paths:
            source = source_map.get(rel_path, "")
            results.append(self.analyze_file(rel_path, source))
        return results

    # ── Import path resolution ────────────────────────────────────────────

    def resolve_local_path(
        self,
        import_record: ImportRecord,
        source_file: str,
        all_file_paths: set[str],
        *,
        package_sep: str = ".",
    ) -> str | None:
        """
        Try to resolve an import to a concrete local file path.

        Returns the matched relative path or None if the import appears external.
        """
        if import_record.is_external:
            return None

        raw = import_record.resolved_module.replace(".", "/")

        # Direct hit (e.g. "auth/service" → "auth/service.py")
        for ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ""):
            candidate = raw + ext
            if candidate in all_file_paths:
                return candidate

        # Relative import — resolve against source file directory
        if import_record.is_relative:
            base = str(Path(source_file).parent)
            for ext in (".py", ".js", ".ts", ".jsx", ".tsx", ""):
                candidate = str(Path(base) / (raw + ext)).replace("\\", "/")
                if candidate in all_file_paths:
                    return candidate

        return None
