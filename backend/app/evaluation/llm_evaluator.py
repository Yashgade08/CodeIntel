"""
LLM Groundedness, Hallucination & Citation Correctness Evaluator.

Computes:
- Citation Correctness (%)
- Groundedness Score (0.0 to 1.0)
- Hallucination Rate (0.0 to 1.0)
- Answer Relevance (0.0 to 1.0)
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Set


def extract_cited_files(llm_answer: str) -> List[str]:
    """Extracts file paths cited in markdown answer links or code references."""
    pattern = r"\[`?([^`\]]+\.(?:py|ts|tsx|js|jsx|json|md))`?\]"
    matches = re.findall(pattern, llm_answer)
    return list(set(matches))


class LLMEvaluator:
    """LLM Evaluation Suite."""

    @staticmethod
    def evaluate_citation_correctness(
        llm_answer: str, retrieved_files: List[str]
    ) -> float:
        """
        Computes the ratio of cited files in the LLM answer that actually exist
        in the retrieved context files list.
        """
        cited_files = extract_cited_files(llm_answer)
        if not cited_files:
            return 1.0

        retrieved_set = set(retrieved_files)
        valid_citations = sum(1 for f in cited_files if f in retrieved_set or any(f in rf for rf in retrieved_set))
        return round(valid_citations / len(cited_files), 4)

    @staticmethod
    def evaluate_groundedness_and_hallucination(
        llm_answer: str, retrieved_snippets: List[str]
    ) -> Dict[str, float]:
        """
        Calculates groundedness score and hallucination rate.
        """
        if not llm_answer or not retrieved_snippets:
            return {"groundedness": 0.0, "hallucination_rate": 1.0}

        context_text = " ".join(retrieved_snippets).lower()
        sentences = [s.strip() for s in llm_answer.split(".") if len(s.strip()) > 15]

        if not sentences:
            return {"groundedness": 1.0, "hallucination_rate": 0.0}

        grounded_count = 0
        for sentence in sentences:
            words = [w.lower() for w in re.findall(r"\b[a-zA-Z_]{4,}\b", sentence)]
            if not words:
                grounded_count += 1
                continue
            matched = sum(1 for w in words if w in context_text)
            if (matched / len(words)) >= 0.30:
                grounded_count += 1

        groundedness = round(grounded_count / len(sentences), 4)
        hallucination_rate = round(1.0 - groundedness, 4)

        return {
            "groundedness": groundedness,
            "hallucination_rate": hallucination_rate,
        }

    @staticmethod
    def evaluate_answer_relevance(query: str, llm_answer: str) -> float:
        """
        Computes answer relevance score measuring query-answer topic overlap.
        """
        query_words = set(w.lower() for w in re.findall(r"\b[a-zA-Z_]{4,}\b", query))
        answer_words = set(w.lower() for w in re.findall(r"\b[a-zA-Z_]{4,}\b", llm_answer))

        if not query_words:
            return 1.0

        matched = query_words.intersection(answer_words)
        return round(len(matched) / len(query_words), 4)
