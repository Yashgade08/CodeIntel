"""
File Internal Structure Parser & Mermaid Generator

Analyzes source code files (Python via standard library AST, JavaScript/TypeScript
and polyglot files via structure-aware regex/token parsing) to extract:
- Imports & external dependencies
- Classes, interfaces, structs with attributes and methods
- Standalone functions & route handlers (with decorators and parameter signatures)
- Internal function-to-function / method-to-function call-flow relationships
- Exact 1-indexed line numbers

Generates rich, dark-mode Mermaid.js diagrams (Flowchart TD and Class Diagrams).
"""

from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MethodSymbol:
    name: str
    parameters: list[str] = field(default_factory=list)
    return_type: str | None = None
    decorators: list[str] = field(default_factory=list)
    start_line: int = 1
    end_line: int = 1
    is_async: bool = False
    docstring: str | None = None
    calls: list[str] = field(default_factory=list)


@dataclass
class ClassSymbol:
    name: str
    bases: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    methods: list[MethodSymbol] = field(default_factory=list)
    start_line: int = 1
    end_line: int = 1
    docstring: str | None = None


@dataclass
class FunctionSymbol:
    name: str
    parameters: list[str] = field(default_factory=list)
    return_type: str | None = None
    decorators: list[str] = field(default_factory=list)
    start_line: int = 1
    end_line: int = 1
    is_async: bool = False
    docstring: str | None = None
    calls: list[str] = field(default_factory=list)


@dataclass
class ImportSymbol:
    module: str
    imported_names: list[str] = field(default_factory=list)
    is_from: bool = False
    line_number: int = 1


@dataclass
class FileStructureAnalysis:
    file_path: str
    language: str
    total_lines: int
    imports: list[ImportSymbol] = field(default_factory=list)
    classes: list[ClassSymbol] = field(default_factory=list)
    functions: list[FunctionSymbol] = field(default_factory=list)
    internal_calls: list[tuple[str, str]] = field(default_factory=list)
    flowchart_syntax: str = ""
    class_diagram_syntax: str = ""

    def to_dict(self) -> dict[str, Any]:
        total_methods = sum(len(c.methods) for c in self.classes)
        return {
            "file_path": self.file_path,
            "language": self.language,
            "total_lines": self.total_lines,
            "metrics": {
                "classes": len(self.classes),
                "methods": total_methods,
                "functions": len(self.functions),
                "imports": len(self.imports),
                "internal_calls": len(self.internal_calls),
            },
            "symbols": {
                "imports": [asdict(imp) for imp in self.imports],
                "classes": [asdict(cls) for cls in self.classes],
                "functions": [asdict(fn) for fn in self.functions],
            },
            "mermaid_syntax": self.flowchart_syntax,
            "class_diagram_syntax": self.class_diagram_syntax,
        }


def _sanitize_id(text: str) -> str:
    """Sanitize strings for valid Mermaid node identifiers."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", text)
    if clean and clean[0].isdigit():
        clean = f"n_{clean}"
    return clean or "node"


def _escape_mermaid_label(text: str) -> str:
    """Escape characters that break Mermaid node labels."""
    return (
        text.replace('"', "'")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("[", "&#91;")
        .replace("]", "&#93;")
        .replace("(", "&#40;")
        .replace(")", "&#41;")
        .replace("{", "&#123;")
        .replace("}", "&#125;")
    )


# ── Python AST Analyzer ───────────────────────────────────────────────────────

class _PythonCallCollector(ast.NodeVisitor):
    """Walks an AST subtree and collects local function/method calls."""

    def __init__(self, known_names: set[str]):
        self.known_names = known_names
        self.calls: set[str] = set()

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.known_names:
                self.calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # Check self.method(...) or cls.method(...) or helper(...)
            if node.func.attr in self.known_names:
                self.calls.add(node.func.attr)
        self.generic_visit(node)


def _format_py_arg(arg: ast.arg) -> str:
    """Format a Python AST arg with optional type annotation."""
    name = arg.arg
    if arg.annotation:
        try:
            name += f": {ast.unparse(arg.annotation)}"
        except Exception:
            pass
    return name


def _format_py_decorator(dec: ast.expr) -> str:
    """Format a Python decorator expression."""
    try:
        raw = ast.unparse(dec)
        return f"@{raw}"
    except Exception:
        if isinstance(dec, ast.Name):
            return f"@{dec.id}"
        return "@decorator"


def _analyze_python_ast(code: str, file_path: str) -> FileStructureAnalysis:
    """Parses Python source code using the standard library `ast` module."""
    lines = code.splitlines()
    total_lines = len(lines)

    try:
        tree = ast.parse(code)
    except Exception as e:
        # Fallback to regex-based analyzer if file has syntax errors
        return _analyze_regex_code(code, file_path, "python", syntax_err=str(e))

    imports: list[ImportSymbol] = []
    classes: list[ClassSymbol] = []
    functions: list[FunctionSymbol] = []

    # First pass: collect all top-level symbol names for call-graph resolution
    local_callable_names: set[str] = set()

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            local_callable_names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    local_callable_names.add(sub.name)

    # Second pass: extract detailed symbols
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    ImportSymbol(
                        module=alias.name,
                        imported_names=[alias.asname or alias.name],
                        is_from=False,
                        line_number=node.lineno,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            mod_name = node.module or ""
            names = [alias.asname or alias.name for alias in node.names]
            imports.append(
                ImportSymbol(
                    module=mod_name,
                    imported_names=names,
                    is_from=True,
                    line_number=node.lineno,
                )
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = [_format_py_arg(a) for a in node.args.args]
            ret_type = None
            if node.returns:
                try:
                    ret_type = ast.unparse(node.returns)
                except Exception:
                    pass
            decs = [_format_py_decorator(d) for d in node.decorator_list]
            doc = ast.get_docstring(node)

            collector = _PythonCallCollector(local_callable_names)
            for stmt in node.body:
                collector.visit(stmt)
            calls = sorted([c for c in collector.calls if c != node.name])

            functions.append(
                FunctionSymbol(
                    name=node.name,
                    parameters=params,
                    return_type=ret_type,
                    decorators=decs,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    docstring=doc,
                    calls=calls,
                )
            )
        elif isinstance(node, ast.ClassDef):
            bases = []
            for b in node.bases:
                try:
                    bases.append(ast.unparse(b))
                except Exception:
                    if isinstance(b, ast.Name):
                        bases.append(b.id)
            doc = ast.get_docstring(node)

            attributes: list[str] = []
            methods: list[MethodSymbol] = []

            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    params = [_format_py_arg(a) for a in sub.args.args if a.arg != "self"]
                    ret_type = None
                    if sub.returns:
                        try:
                            ret_type = ast.unparse(sub.returns)
                        except Exception:
                            pass
                    decs = [_format_py_decorator(d) for d in sub.decorator_list]
                    meth_doc = ast.get_docstring(sub)

                    collector = _PythonCallCollector(local_callable_names)
                    for stmt in sub.body:
                        collector.visit(stmt)
                    calls = sorted([c for c in collector.calls if c != sub.name])

                    methods.append(
                        MethodSymbol(
                            name=sub.name,
                            parameters=params,
                            return_type=ret_type,
                            decorators=decs,
                            start_line=sub.lineno,
                            end_line=getattr(sub, "end_lineno", sub.lineno),
                            is_async=isinstance(sub, ast.AsyncFunctionDef),
                            docstring=meth_doc,
                            calls=calls,
                        )
                    )
                elif isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                    attr_str = sub.target.id
                    try:
                        attr_str += f": {ast.unparse(sub.annotation)}"
                    except Exception:
                        pass
                    attributes.append(attr_str)
                elif isinstance(sub, ast.Assign):
                    for target in sub.targets:
                        if isinstance(target, ast.Name):
                            attributes.append(target.id)

            classes.append(
                ClassSymbol(
                    name=node.name,
                    bases=bases,
                    attributes=attributes[:10],
                    methods=methods,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    docstring=doc,
                )
            )

    # Compute internal calls (caller -> callee)
    internal_calls: list[tuple[str, str]] = []
    for fn in functions:
        for callee in fn.calls:
            internal_calls.append((fn.name, callee))
    for cls in classes:
        for m in cls.methods:
            for callee in m.calls:
                internal_calls.append((f"{cls.name}.{m.name}", callee))

    flowchart_syntax = _generate_mermaid_flowchart(
        file_path=file_path,
        language="python",
        imports=imports,
        classes=classes,
        functions=functions,
        internal_calls=internal_calls,
    )

    class_diagram_syntax = _generate_mermaid_class_diagram(
        file_path=file_path,
        classes=classes,
    )

    return FileStructureAnalysis(
        file_path=file_path,
        language="python",
        total_lines=total_lines,
        imports=imports,
        classes=classes,
        functions=functions,
        internal_calls=internal_calls,
        flowchart_syntax=flowchart_syntax,
        class_diagram_syntax=class_diagram_syntax,
    )


# ── Regex / Polyglot Analyzer (JS, TS, Go, Java, etc.) ───────────────────────

_JS_TS_IMPORT_RE = re.compile(
    r"import\s+(?:(?:\{([^}]+)\}|\*\s+as\s+([a-zA-Z0-9_$]+)|([a-zA-Z0-9_$]+))\s+from\s+)?['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)
_CLASS_RE = re.compile(
    r"^(?:export\s+)?(?:default\s+)?(?:abstract\s+)?(?:class|interface|struct)\s+([a-zA-Z0-9_$]+)(?:\s+extends\s+([a-zA-Z0-9_$,\s]+))?(?:\s+implements\s+([a-zA-Z0-9_$,\s]+))?",
    re.MULTILINE,
)
_JS_FUNC_RE = re.compile(
    r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(([^)]*)\)",
    re.MULTILINE,
)
_ARROW_FUNC_RE = re.compile(
    r"^(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)(?:\s*:\s*([^=]+))?\s*=>",
    re.MULTILINE,
)


def _analyze_regex_code(
    code: str,
    file_path: str,
    language: str,
    syntax_err: str | None = None,
) -> FileStructureAnalysis:
    """Structure-aware regex extraction for JS, TS, and general programming languages."""
    lines = code.splitlines()
    total_lines = len(lines)

    imports: list[ImportSymbol] = []
    classes: list[ClassSymbol] = []
    functions: list[FunctionSymbol] = []
    internal_calls: list[tuple[str, str]] = []

    # 1. Imports
    for match in _JS_TS_IMPORT_RE.finditer(code):
        named, star, default, module = match.groups()
        names = []
        if named:
            names.extend([n.strip().split(" as ")[0] for n in named.split(",") if n.strip()])
        if default:
            names.append(default.strip())
        if star:
            names.append(star.strip())
        line_no = code[: match.start()].count("\n") + 1
        imports.append(
            ImportSymbol(
                module=module,
                imported_names=names,
                is_from=bool(named or default or star),
                line_number=line_no,
            )
        )

    # 2. Functions (regular and arrow)
    known_callables: set[str] = set()

    for match in _JS_FUNC_RE.finditer(code):
        name, params = match.groups()
        if name in ("if", "for", "while", "switch", "catch"):
            continue
        line_no = code[: match.start()].count("\n") + 1
        param_list = [p.strip() for p in params.split(",") if p.strip()]
        known_callables.add(name)
        functions.append(
            FunctionSymbol(
                name=name,
                parameters=param_list,
                start_line=line_no,
                end_line=line_no,
            )
        )

    for match in _ARROW_FUNC_RE.finditer(code):
        name, params, ret_type = match.groups()
        line_no = code[: match.start()].count("\n") + 1
        param_list = [p.strip() for p in params.split(",") if p.strip()]
        known_callables.add(name)
        functions.append(
            FunctionSymbol(
                name=name,
                parameters=param_list,
                return_type=ret_type.strip() if ret_type else None,
                start_line=line_no,
                end_line=line_no,
            )
        )

    # 3. Classes
    for match in _CLASS_RE.finditer(code):
        name, extends_cls, implements_cls = match.groups()
        line_no = code[: match.start()].count("\n") + 1
        bases = []
        if extends_cls:
            bases.extend([b.strip() for b in extends_cls.split(",") if b.strip()])
        if implements_cls:
            bases.extend([b.strip() for b in implements_cls.split(",") if b.strip()])

        classes.append(
            ClassSymbol(
                name=name,
                bases=bases,
                start_line=line_no,
                end_line=line_no,
            )
        )

    # 4. Search for internal call relations (if function calls another known function)
    for fn in functions:
        fn_name = fn.name
        for other in known_callables:
            if other != fn_name and re.search(rf"\b{re.escape(other)}\s*\(", code):
                internal_calls.append((fn_name, other))
                fn.calls.append(other)

    flowchart_syntax = _generate_mermaid_flowchart(
        file_path=file_path,
        language=language,
        imports=imports[:20],
        classes=classes,
        functions=functions[:35],
        internal_calls=internal_calls[:25],
    )

    class_diagram_syntax = _generate_mermaid_class_diagram(
        file_path=file_path,
        classes=classes,
    )

    return FileStructureAnalysis(
        file_path=file_path,
        language=language,
        total_lines=total_lines,
        imports=imports,
        classes=classes,
        functions=functions,
        internal_calls=internal_calls,
        flowchart_syntax=flowchart_syntax,
        class_diagram_syntax=class_diagram_syntax,
    )


# ── Mermaid Syntax Generators ────────────────────────────────────────────────

def _generate_mermaid_flowchart(
    file_path: str,
    language: str,
    imports: list[ImportSymbol],
    classes: list[ClassSymbol],
    functions: list[FunctionSymbol],
    internal_calls: list[tuple[str, str]],
) -> str:
    """Generates an aesthetic, dark-mode Mermaid `flowchart TD` of the file."""
    lines = [
        "%%{init: {'theme': 'dark', 'themeVariables': { "
        "'primaryColor': '#0284c7', 'edgeLabelBackground':'#0f172a', "
        "'tertiaryColor': '#1e293b', 'primaryTextColor': '#f8fafc', "
        "'lineColor': '#38bdf8'}}}%%",
        "flowchart TD",
    ]

    base_name = Path(file_path).name
    file_id = f"FILE_{_sanitize_id(base_name)}"

    # File Root Header Node
    lang_badge = language.upper()
    lines.append(f'  {file_id}["📄 <strong>{_escape_mermaid_label(base_name)}</strong> <small>({lang_badge})</small>"]')
    lines.append(f"  style {file_id} fill:#0369a1,stroke:#38bdf8,stroke-width:2px,color:#ffffff")

    # Subgraph: Imports
    if imports:
        lines.append('  subgraph IMPORTS ["📦 Imports & External Modules"]')
        for idx, imp in enumerate(imports[:12]):
            imp_id = f"IMP_{idx}_{_sanitize_id(imp.module)}"
            if imp.imported_names:
                names_summary = ", ".join(imp.imported_names[:3])
                if len(imp.imported_names) > 3:
                    names_summary += f" +{len(imp.imported_names) - 3}"
                label = f"{imp.module} ({names_summary})"
            else:
                label = imp.module
            lines.append(f'    {imp_id}["📥 {_escape_mermaid_label(label)}"]')
            lines.append(f"    style {imp_id} fill:#0f172a,stroke:#334155,color:#94a3b8")
        if len(imports) > 12:
            lines.append(f'    IMP_MORE["... +{len(imports) - 12} more imports"]')
            lines.append("    style IMP_MORE fill:#0f172a,stroke:#334155,color:#64748b")
        lines.append("  end")
        lines.append(f"  {file_id} -.-> IMPORTS")

    # Subgraph: Classes
    if classes:
        lines.append('  subgraph CLASSES ["🏛️ Classes & Data Models"]')
        for c_idx, cls in enumerate(classes):
            cls_node_id = f"CLS_{_sanitize_id(cls.name)}"
            bases_str = f" : ({', '.join(cls.bases)})" if cls.bases else ""
            lines.append(f'    subgraph {cls_node_id} ["🏛️ class {cls.name}{bases_str}"]')

            # Attributes
            for a_idx, attr in enumerate(cls.attributes[:6]):
                attr_id = f"{cls_node_id}_attr_{a_idx}"
                lines.append(f'      {attr_id}["🔹 {_escape_mermaid_label(attr)}"]')
                lines.append(f"      style {attr_id} fill:#090e1a,stroke:#1e293b,color:#cbd5e1")

            # Methods
            for m_idx, meth in enumerate(cls.methods):
                meth_id = f"METH_{_sanitize_id(cls.name)}_{_sanitize_id(meth.name)}"
                dec_prefix = f"{meth.decorators[0]} " if meth.decorators else ""
                ret_str = f" ➔ {meth.return_type}" if meth.return_type else ""
                lines_span = f":L{meth.start_line}-{meth.end_line}"
                label = f"{dec_prefix}{meth.name}(){ret_str} {lines_span}"
                lines.append(f'      {meth_id}["⚙️ {_escape_mermaid_label(label)}"]')
                lines.append(f"      style {meth_id} fill:#1e1b4b,stroke:#6366f1,color:#e0e7ff")

            lines.append("    end")
            lines.append(f"    {file_id} --> {cls_node_id}")
        lines.append("  end")

    # Subgraph: Standalone Functions & Endpoints
    if functions:
        lines.append('  subgraph FUNCTIONS ["⚡ Standalone Functions & Endpoints"]')
        for f_idx, fn in enumerate(functions[:25]):
            fn_id = f"FN_{_sanitize_id(fn.name)}"
            icon = "🌐" if any("router" in d.lower() or "app" in d.lower() or "get" in d.lower() or "post" in d.lower() for d in fn.decorators) else "⚡"
            dec_prefix = f"{fn.decorators[0]} " if fn.decorators else ""
            ret_str = f" ➔ {fn.return_type}" if fn.return_type else ""
            lines_span = f":L{fn.start_line}-{fn.end_line}"
            label = f"{icon} {dec_prefix}{fn.name}(){ret_str} {lines_span}"
            lines.append(f'    {fn_id}["{_escape_mermaid_label(label)}"]')

            if icon == "🌐":
                lines.append(f"    style {fn_id} fill:#064e3b,stroke:#10b981,color:#a7f3d0")
            else:
                lines.append(f"    style {fn_id} fill:#0f172a,stroke:#38bdf8,color:#f0f9ff")

            lines.append(f"    {file_id} --> {fn_id}")

        if len(functions) > 25:
            lines.append(f'    FN_MORE["... +{len(functions) - 25} more functions"]')
        lines.append("  end")

    # Internal Calls Edges
    if internal_calls:
        seen_edges: set[tuple[str, str]] = set()
        for caller, callee in internal_calls[:25]:
            caller_id = f"FN_{_sanitize_id(caller)}" if "." not in caller else f"METH_{_sanitize_id(caller.split('.')[0])}_{_sanitize_id(caller.split('.')[1])}"
            callee_id = f"FN_{_sanitize_id(callee)}"
            edge_key = (caller_id, callee_id)
            if edge_key not in seen_edges and caller_id != callee_id:
                seen_edges.add(edge_key)
                lines.append(f"  {caller_id} ==>|calls| {callee_id}")

    return "\n".join(lines)


def _generate_mermaid_class_diagram(
    file_path: str,
    classes: list[ClassSymbol],
) -> str:
    """Generates a standard Mermaid `classDiagram` for files with classes."""
    if not classes:
        return ""

    lines = [
        "%%{init: {'theme': 'dark'}}%%",
        "classDiagram",
    ]

    for cls in classes:
        clean_name = _sanitize_id(cls.name)
        lines.append(f"    class {clean_name} {{")
        for attr in cls.attributes[:8]:
            lines.append(f"        +{_escape_mermaid_label(attr)}")
        for meth in cls.methods[:15]:
            ret = f" {meth.return_type}" if meth.return_type else ""
            lines.append(f"        +{meth.name}(){ret}")
        lines.append("    }")

        for base in cls.bases:
            clean_base = _sanitize_id(base)
            lines.append(f"    {clean_base} <|-- {clean_name}")

    return "\n".join(lines)


# ── Public Analyzer Entry Point ───────────────────────────────────────────────

def analyze_file_structure(file_path_obj: Path, relative_path: str) -> dict[str, Any]:
    """
    Reads the given source code file and extracts internal symbol structure
    and Mermaid.js diagram definitions.
    """
    if not file_path_obj.is_file():
        raise FileNotFoundError(f"File not found: {file_path_obj}")

    ext = file_path_obj.suffix.lower()
    try:
        content = file_path_obj.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise ValueError(f"Could not read source file {relative_path}: {e}")

    if ext in (".py", ".pyi"):
        analysis = _analyze_python_ast(content, relative_path)
    elif ext in (".js", ".jsx", ".ts", ".tsx"):
        lang = "typescript" if "ts" in ext else "javascript"
        analysis = _analyze_regex_code(content, relative_path, lang)
    else:
        analysis = _analyze_regex_code(content, relative_path, ext.lstrip("."))

    return analysis.to_dict()
