"""
RAG Retrieval & Generation Quality Evaluator.

Computes metrics:
- Recall@K (K=1, 3, 5)
- Precision@K (K=1, 3, 5)
- Mean Reciprocal Rank (MRR)
- Context Relevance
- Answer Relevance
- Faithfulness
"""

from __future__ import annotations

import math
from typing import List, Dict, Any, Set
from app.evaluation.dataset import RAGTestCase, RAG_TEST_CASES


def calculate_recall_at_k(retrieved_files: List[str], expected_files: List[str], k: int) -> float:
    """Calculates Recall@K for a single query."""
    if not expected_files:
        return 1.0
    retrieved_top_k = set(retrieved_files[:k])
    expected_set = set(expected_files)
    hits = retrieved_top_k.intersection(expected_set)
    return len(hits) / len(expected_set)


def calculate_precision_at_k(retrieved_files: List[str], expected_files: List[str], k: int) -> float:
    """Calculates Precision@K for a single query."""
    if k <= 0:
        return 0.0
    retrieved_top_k = retrieved_files[:k]
    expected_set = set(expected_files)
    hits = [f for f in retrieved_top_k if f in expected_set]
    return len(hits) / k


def calculate_reciprocal_rank(retrieved_files: List[str], expected_files: List[str]) -> float:
    """Calculates Reciprocal Rank (1/rank of first hit)."""
    expected_set = set(expected_files)
    for rank_idx, file_path in enumerate(retrieved_files, start=1):
        if file_path in expected_set:
            return 1.0 / rank_idx
    return 0.0


def calculate_context_relevance(retrieved_snippets: List[str], expected_concepts: List[str]) -> float:
    """
    Computes Context Relevance score (proportion of expected concepts present in retrieved context).
    """
    if not expected_concepts:
        return 1.0
    combined_text = " ".join(retrieved_snippets).lower()
    matches = sum(1 for concept in expected_concepts if concept.lower() in combined_text)
    return matches / len(expected_concepts)


def calculate_answer_relevance(generated_answer: str, ground_truth_answer: str) -> float:
    """
    Computes token-level Jaccard & overlap similarity between generated answer and ground truth answer.
    """
    if not generated_answer or not ground_truth_answer:
        return 0.0

    gen_tokens: Set[str] = set(generated_answer.lower().split())
    gt_tokens: Set[str] = set(ground_truth_answer.lower().split())

    if not gt_tokens:
        return 1.0

    intersection = gen_tokens.intersection(gt_tokens)
    union = gen_tokens.union(gt_tokens)
    return len(intersection) / len(union) if union else 0.0


def calculate_faithfulness(generated_answer: str, retrieved_snippets: List[str]) -> float:
    """
    Computes Faithfulness score (proportion of key generated sentences grounded in retrieved context).
    """
    if not generated_answer or not retrieved_snippets:
        return 0.0

    context_text = " ".join(retrieved_snippets).lower()
    sentences = [s.strip() for s in generated_answer.split(".") if len(s.strip()) > 10]

    if not sentences:
        return 1.0

    grounded_count = 0
    for sentence in sentences:
        words = [w for w in sentence.lower().split() if len(w) > 4]
        if not words:
            grounded_count += 1
            continue
        matched_words = sum(1 for w in words if w in context_text)
        if (matched_words / len(words)) >= 0.35:
            grounded_count += 1

    return grounded_count / len(sentences)


class RAGEvaluator:
    """RAG Quality Evaluation Suite."""

    def evaluate_query(
        case: RAGTestCase,
        retrieved_files: List[str],
        retrieved_snippets: List[str],
        generated_answer: str,
    ) -> Dict[str, float]:
        """Evaluates a single RAG query case across all retrieval & generation metrics."""
        return {
            "recall_at_1": calculate_recall_at_k(retrieved_files, case.expected_files, 1),
            "recall_at_3": calculate_recall_at_k(retrieved_files, case.expected_files, 3),
            "recall_at_5": calculate_recall_at_k(retrieved_files, case.expected_files, 5),
            "precision_at_1": calculate_precision_at_k(retrieved_files, case.expected_files, 1),
            "precision_at_3": calculate_precision_at_k(retrieved_files, case.expected_files, 3),
            "precision_at_5": calculate_precision_at_k(retrieved_files, case.expected_files, 5),
            "mrr": calculate_reciprocal_rank(retrieved_files, case.expected_files),
            "context_relevance": calculate_context_relevance(retrieved_snippets, case.expected_concepts),
            "answer_relevance": calculate_answer_relevance(generated_answer, case.ground_truth_answer),
            "faithfulness": calculate_faithfulness(generated_answer, retrieved_snippets),
        }
