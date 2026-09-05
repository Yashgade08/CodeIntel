"""
FastAPI endpoints for system evaluation metrics and benchmarks.
"""

from __future__ import annotations

from typing import Dict, Any

from fastapi import APIRouter, BackgroundTasks, status
from app.evaluation.runner import load_evaluation_results, run_full_evaluation

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get(
    "/metrics",
    summary="Get system evaluation benchmark metrics",
)
async def get_evaluation_metrics() -> Dict[str, Any]:
    """
    Returns latest calculated evaluation metrics for RAG, ML, LLM groundedness,
    and performance latencies.
    """
    return load_evaluation_results()


@router.post(
    "/run",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger evaluation experiment benchmark run",
)
async def trigger_evaluation_run(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """
    Triggers an asynchronous background run of the evaluation benchmark suite.
    """
    background_tasks.add_task(run_full_evaluation)
    return {
        "status": "QUEUED",
        "message": "Evaluation experiment suite runner task started in background.",
    }
