"""
NetworkX-based dependency graph builder.

Constructs a directed graph where nodes are files, modules, classes, or
functions, and edges represent import / inheritance / (best-effort) call
relationships.

Node id conventions
-------------------
  file       →  relative path, e.g. "auth/service.py"
  module     →  "module:<name>", e.g. "module:sqlalchemy"
  class      →  "class:<file>::<ClassName>"
  function   →  "func:<file>::<ClassName>.<fn>" or "func:<file>::<fn>"

Edge attributes
---------------
  dependency_type: "import" | "inheritance" | "call"
  source_symbol:   optional qualified symbol name in the source
  target_symbol:   optional qualified symbol name in the target
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx

from app.core.logging import get_logger
from app.graph.analyzer import FileAnalysis, ImportAnalyzer

logger = get_logger(__name__)


# ── Node / edge constructors ──────────────────────────────────────────────────

def _file_node(path: str) -> str:
    return path


def _module_node(name: str) -> str:
    return f"module:{name}"


def _class_node(file_path: str, class_name: str) -> str:
    return f"class:{file_path}::{class_name}"


def _func_node(file_path: str, fn_name: str, class_name: str | None = None) -> str:
    qual = f"{class_name}.{fn_name}" if class_name else fn_name
    return f"func:{file_path}::{qual}"


# ── Graph builder ─────────────────────────────────────────────────────────────

@dataclass
class FileRecord:
    """Minimal file descriptor passed to the builder."""
    path: str            # relative path within the repo
    language: str | None = None
    line_count: int = 0
    size_bytes: int = 0


class DependencyGraphBuilder:
    """
    Build a directed dependency graph for a repository.

    Usage::

        builder = DependencyGraphBuilder()
        graph = builder.build(repo_path, file_records, source_map)
        deps = builder.get_dependencies(graph, "auth/service.py")
    """

    def __init__(self) -> None:
        self._analyzer = ImportAnalyzer()

    # ── Main build entry point ─────────────────────────────────────────────

    def build(
        self,
        repo_path: str,
        file_records: list[FileRecord],
        source_map: dict[str, str],
    ) -> nx.DiGraph:
        """
        Analyse all files and build the dependency graph.

        Returns a :class:`networkx.DiGraph` populated with file, module,
        class, and function nodes plus import/inheritance edges.
        """
        graph: nx.DiGraph = nx.DiGraph()
        all_paths: set[str] = {fr.path for fr in file_records}

        # ── Step 1: Analyse every file ────────────────────────────────────
        analyses: list[FileAnalysis] = []
        for fr in file_records:
            source = source_map.get(fr.path, "")
            analysis = self._analyzer.analyze_file(fr.path, source)
            analyses.append(analysis)

            # Add file node
            graph.add_node(
                _file_node(fr.path),
                node_type="file",
                language=fr.language or analysis.language,
                line_count=fr.line_count,
                size_bytes=fr.size_bytes,
                path=fr.path,
                parse_error=analysis.parse_error,
            )

            # Add class nodes
            for cls in analysis.classes:
                cid = _class_node(fr.path, cls.name)
                graph.add_node(cid, node_type="class", file=fr.path,
                               start_line=cls.start_line, end_line=cls.end_line)

            # Add function nodes
            for fn in analysis.functions:
                fid = _func_node(fr.path, fn.name, fn.class_name)
                graph.add_node(fid, node_type="function", file=fr.path,
                               start_line=fn.start_line, end_line=fn.end_line,
                               is_async=fn.is_async)

        # ── Step 2: Resolve import edges ──────────────────────────────────
        for analysis in analyses:
            for imp in analysis.imports:
                local_target = self._analyzer.resolve_local_path(
                    imp, analysis.file_path, all_paths
                )

                if local_target:
                    # File → File import edge
                    graph.add_edge(
                        _file_node(analysis.file_path),
                        _file_node(local_target),
                        dependency_type="import",
                        source_symbol=None,
                        target_symbol=imp.raw_import,
                        is_external=False,
                    )
                else:
                    # File → External module edge
                    top_level = imp.resolved_module.split(".")[0] or imp.resolved_module
                    if not top_level or top_level.startswith("__"):
                        continue
                    mod_id = _module_node(top_level)
                    if mod_id not in graph:
                        graph.add_node(mod_id, node_type="module",
                                       is_external=True, name=top_level)
                    graph.add_edge(
                        _file_node(analysis.file_path),
                        mod_id,
                        dependency_type="import",
                        source_symbol=None,
                        target_symbol=imp.raw_import,
                        is_external=True,
                    )

        # ── Step 3: Inheritance edges ─────────────────────────────────────
        # Build a class-name → node-id lookup
        class_lookup: dict[str, str] = {}
        for node_id, data in graph.nodes(data=True):
            if data.get("node_type") == "class":
                short_name = node_id.split("::")[-1]
                class_lookup[short_name] = node_id

        for analysis in analyses:
            for cls in analysis.classes:
                src_id = _class_node(analysis.file_path, cls.name)
                for base in cls.bases:
                    tgt_id = class_lookup.get(base)
                    if tgt_id and tgt_id != src_id:
                        graph.add_edge(
                            src_id, tgt_id,
                            dependency_type="inheritance",
                            source_symbol=cls.name,
                            target_symbol=base,
                            is_external=False,
                        )

        logger.info(
            "Dependency graph built",
            nodes=graph.number_of_nodes(),
            edges=graph.number_of_edges(),
        )
        return graph

    # ── Query helpers ──────────────────────────────────────────────────────

    @staticmethod
    def get_dependencies(
        graph: nx.DiGraph,
        file_path: str,
        depth: int = 1,
        *,
        include_external: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Return files (and modules) that *file_path* directly or transitively
        imports, up to *depth* hops.

        Returns a list of dicts: {path, node_type, depth, dependency_type}.
        """
        source = _file_node(file_path)
        if source not in graph:
            return []

        results: list[dict[str, Any]] = []
        visited: set[str] = {source}
        frontier: list[tuple[str, int]] = [(source, 0)]

        while frontier:
            current, current_depth = frontier.pop(0)
            if current_depth >= depth:
                continue
            for _, tgt, edge_data in graph.out_edges(current, data=True):
                if tgt in visited:
                    continue
                visited.add(tgt)
                tgt_data = graph.nodes[tgt]
                is_external = tgt_data.get("is_external", False)
                if is_external and not include_external:
                    continue
                results.append({
                    "path": tgt_data.get("path", tgt),
                    "node_id": tgt,
                    "node_type": tgt_data.get("node_type", "file"),
                    "language": tgt_data.get("language"),
                    "depth": current_depth + 1,
                    "dependency_type": edge_data.get("dependency_type", "import"),
                    "is_external": is_external,
                })
                frontier.append((tgt, current_depth + 1))

        return results

    @staticmethod
    def get_dependents(
        graph: nx.DiGraph,
        file_path: str,
        depth: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Return files that import *file_path* (i.e. reverse edges),
        up to *depth* hops.
        """
        target = _file_node(file_path)
        if target not in graph:
            return []

        results: list[dict[str, Any]] = []
        visited: set[str] = {target}
        frontier: list[tuple[str, int]] = [(target, 0)]

        while frontier:
            current, current_depth = frontier.pop(0)
            if current_depth >= depth:
                continue
            for src, _, edge_data in graph.in_edges(current, data=True):
                if src in visited:
                    continue
                visited.add(src)
                src_data = graph.nodes[src]
                if src_data.get("node_type") != "file":
                    continue
                results.append({
                    "path": src_data.get("path", src),
                    "node_id": src,
                    "node_type": "file",
                    "language": src_data.get("language"),
                    "depth": current_depth + 1,
                    "dependency_type": edge_data.get("dependency_type", "import"),
                    "is_external": False,
                })
                frontier.append((src, current_depth + 1))

        return results

    @staticmethod
    def get_impact_set(
        graph: nx.DiGraph,
        file_path: str,
        depth: int = 5,
    ) -> list[str]:
        """
        Return *all* file paths transitively affected if *file_path* changes —
        i.e. the full set of reverse-reachable file nodes up to *depth* hops.
        """
        target = _file_node(file_path)
        if target not in graph:
            return []

        # Reverse graph to follow "who depends on me" edges
        rev = graph.reverse(copy=False)
        affected: set[str] = set()

        for node in nx.bfs_tree(rev, target, depth_limit=depth).nodes():
            if node == target:
                continue
            data = graph.nodes.get(node, {})
            if data.get("node_type") == "file":
                path = data.get("path", node)
                affected.add(path)

        return sorted(affected)

    @staticmethod
    def get_subgraph(
        graph: nx.DiGraph,
        file_path: str,
        depth: int = 2,
    ) -> nx.DiGraph:
        """
        Return a subgraph centred on *file_path*, including both its
        dependencies and its dependents within *depth* hops.
        """
        source = _file_node(file_path)
        if source not in graph:
            return nx.DiGraph()

        nodes_to_include: set[str] = {source}

        # Forward BFS (dependencies)
        for node in nx.bfs_tree(graph, source, depth_limit=depth).nodes():
            nodes_to_include.add(node)

        # Reverse BFS (dependents)
        rev = graph.reverse(copy=False)
        for node in nx.bfs_tree(rev, source, depth_limit=depth).nodes():
            nodes_to_include.add(node)

        return graph.subgraph(nodes_to_include).copy()
