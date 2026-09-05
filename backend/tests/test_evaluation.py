"""
Tests for the CodeIntel Evaluation Framework.
"""

import pytest
from app.evaluation.dataset import RAG_TEST_CASES, ISSUE_TEST_CASES, RISK_TEST_CASES
from app.evaluation.rag_evaluator import (
    calculate_recall_at_k,
    calculate_precision_at_k,
    calculate_reciprocal_rank,
    calculate_context_relevance,
    calculate_answer_relevance,
    calculate_faithfulness,
    RAGEvaluator,
)
from app.evaluation.ml_evaluator import (
    calculate_accuracy,
    calculate_brier_score,
    calculate_confusion_matrix,
    MLEvaluator,
)
from app.evaluation.llm_evaluator import LLMEvaluator, extract_cited_files
from app.evaluation.runner import run_full_evaluation, load_evaluation_results


def test_rag_recall_precision_mrr():
    expected = ["app/graph/builder.py", "app/graph/analyzer.py"]
    retrieved = ["app/graph/builder.py", "app/models/database.py", "app/graph/analyzer.py"]

    rec_1 = calculate_recall_at_k(retrieved, expected, 1)
    assert rec_1 == 0.5

    rec_3 = calculate_recall_at_k(retrieved, expected, 3)
    assert rec_3 == 1.0

    prec_1 = calculate_precision_at_k(retrieved, expected, 1)
    assert prec_1 == 1.0

    prec_2 = calculate_precision_at_k(retrieved, expected, 2)
    assert prec_2 == 0.5

    mrr = calculate_reciprocal_rank(retrieved, expected)
    assert mrr == 1.0


def test_context_relevance_and_faithfulness():
    concepts = ["NetworkX", "AST parsing"]
    snippets = ["Class GraphBuilder utilizes NetworkX DiGraph for AST parsing and import resolution."]
    rel = calculate_context_relevance(snippets, concepts)
    assert rel == 1.0

    answer = "The graph builder uses NetworkX DiGraph for AST parsing."
    faith = calculate_faithfulness(answer, snippets)
    assert faith > 0.5


def test_ml_evaluator_metrics():
    y_true = ["Bug", "Feature Request", "Bug"]
    y_pred = ["Bug", "Feature Request", "Bug"]

    acc = calculate_accuracy(y_true, y_pred)
    assert acc == 1.0

    brier = calculate_brier_score([1, 0, 1], [0.9, 0.1, 0.8])
    assert brier < 0.1

    cm = calculate_confusion_matrix(y_true, y_pred, ["Bug", "Feature Request"])
    assert cm["matrix"]["Bug"]["Bug"] == 2


def test_llm_citation_and_groundedness():
    answer = "The AST graph builder is in [`app/graph/builder.py`]."
    cited = extract_cited_files(answer)
    assert "app/graph/builder.py" in cited

    cit_score = LLMEvaluator.evaluate_citation_correctness(answer, ["app/graph/builder.py"])
    assert cit_score == 1.0

    gh = LLMEvaluator.evaluate_groundedness_and_hallucination(answer, ["AST graph builder is in app/graph/builder.py"])
    assert gh["groundedness"] > 0.0
    assert gh["hallucination_rate"] <= 1.0


def test_full_evaluation_runner():
    report = run_full_evaluation()
    assert report["status"] == "COMPLETED"
    assert "rag_metrics" in report
    assert "ml_metrics" in report
    assert "llm_metrics" in report
    assert "performance_latency" in report
    assert report["rag_metrics"]["recall_at_3"] > 0.0
    assert report["ml_metrics"]["code_risk"]["brier_score_calibration"] >= 0.0
