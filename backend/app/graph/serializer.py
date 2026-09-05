"""
Graph serializer — converts nx.DiGraph to React-Flow-compatible JSON
and lightweight summary dicts.
"""

from __future__ import annotations

from typing import Any

import networkx as nx


class GraphSerializer:
    """
    Serialize a NetworkX DiGraph for API responses and JSONB storage.

    The wire format is React-Flow compatible so the frontend can render it
    directly without any further transformation.
    """

    # ── Public methods ─────────────────────────────────────────────────────

    def to_dict(self, graph: nx.DiGraph) -> dict[str, Any]:
        """
        Full serialization: nodes + edges + summary statistics.

        Node schema::

            {
                "id": "auth/service.py",
                "type": "file",          # file | module | class | function
                "language": "python",
                "line_count": 120,
                "is_external": false,
                ...
            }

        Edge schema::

            {
                "id": "auth/service.py->db/session.py",
                "source": "auth/service.py",
                "target": "db/session.py",
                "type": "import",        # import | inheritance | call
                "is_external": false
            }
        """
        nodes = []
        for node_id, data in graph.nodes(data=True):
            node_dict: dict[str, Any] = {"id": node_id}
            node_dict.update(data)
            nodes.append(node_dict)

        edges = []
        for src, tgt, data in graph.edges(data=True):
            edge_dict: dict[str, Any] = {
                "id": f"{src}->{tgt}",
                "source": src,
                "target": tgt,
            }
            edge_dict.update(data)
            edges.append(edge_dict)

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": self._compute_stats(graph),
        }

    def to_summary_dict(self, graph: nx.DiGraph) -> dict[str, Any]:
        """
        Lightweight summary for embedding in repository.metadata_.

        Stores only aggregated statistics rather than the full node/edge list
        to keep the JSONB payload small.  The full graph is stored separately
        as ``dependency_graph_full``.
        """
        return {"stats": self._compute_stats(graph)}

    def to_storage_dict(self, graph: nx.DiGraph) -> dict[str, Any]:
        """
        Full serialization intended for JSONB persistence (metadata_ column).
        Same structure as :meth:`to_dict` but kept separate to make intent clear.
        """
        return self.to_dict(graph)

    # ── Deserialization ────────────────────────────────────────────────────

    @staticmethod
    def from_dict(data: dict[str, Any]) -> nx.DiGraph:
        """Reconstruct a DiGraph from a serialized dict produced by :meth:`to_dict`."""
        graph: nx.DiGraph = nx.DiGraph()

        for node in data.get("nodes", []):
            node_id = node.pop("id")
            graph.add_node(node_id, **node)

        for edge in data.get("edges", []):
            src = edge["source"]
            tgt = edge["target"]
            attrs = {k: v for k, v in edge.items() if k not in ("id", "source", "target")}
            graph.add_edge(src, tgt, **attrs)

        return graph

    # ── Statistics ─────────────────────────────────────────────────────────

    @staticmethod
    def _compute_stats(graph: nx.DiGraph) -> dict[str, Any]:
        file_nodes = [n for n, d in graph.nodes(data=True) if d.get("node_type") == "file"]
        module_nodes = [n for n, d in graph.nodes(data=True) if d.get("node_type") == "module"]
        class_nodes = [n for n, d in graph.nodes(data=True) if d.get("node_type") == "class"]
        func_nodes = [n for n, d in graph.nodes(data=True) if d.get("node_type") == "function"]

        # Language breakdown (file nodes only)
        languages: dict[str, int] = {}
        for n in file_nodes:
            lang = graph.nodes[n].get("language") or "unknown"
            languages[lang] = languages.get(lang, 0) + 1

        # Import edge count (file→file only)
        import_edges = sum(
            1 for _, _, d in graph.edges(data=True)
            if d.get("dependency_type") == "import" and not d.get("is_external", False)
        )

        return {
            "total_nodes": graph.number_of_nodes(),
            "total_edges": graph.number_of_edges(),
            "file_count": len(file_nodes),
            "external_module_count": len(module_nodes),
            "class_count": len(class_nodes),
            "function_count": len(func_nodes),
            "internal_import_edges": import_edges,
            "languages": languages,
        }
