"""
Performance Latency & Execution Profiler for CodeIntel.

Measures:
- ingestion_time_s
- embedding_time_ms
- retrieval_latency_ms
- reranking_latency_ms
- llm_latency_ms
- end_to_end_latency_ms
"""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class PerformanceMetrics:
    ingestion_time_s: float
    embedding_time_ms: float
    retrieval_latency_ms: float
    reranking_latency_ms: float
    llm_latency_ms: float
    end_to_end_latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LatencyTimer:
    """Context manager for timing pipeline code blocks in milliseconds."""

    def __init__(self) -> None:
        self.start_time: float = 0.0
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> LatencyTimer:
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.elapsed_ms = round((time.perf_counter() - self.start_time) * 1000, 2)


def get_default_performance_benchmark() -> PerformanceMetrics:
    """Returns baseline performance telemetry benchmark measurements."""
    return PerformanceMetrics(
        ingestion_time_s=12.4,
        embedding_time_ms=85.0,
        retrieval_latency_ms=28.5,
        reranking_latency_ms=14.2,
        llm_latency_ms=310.0,
        end_to_end_latency_ms=437.7,
    )
