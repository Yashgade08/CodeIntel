"""
Machine Learning Model Evaluator.

Computes classification metrics, confusion matrices, and calibration scores:
- Issue Classification: accuracy, precision, recall, macro/weighted F1, confusion matrix
- Issue Severity: macro F1, weighted F1, confusion matrix
- Duplicate Detection: precision, recall, F1
- Code Risk: accuracy, log loss, Brier calibration score
"""

from __future__ import annotations

from typing import List, Dict, Any, Tuple
from collections import defaultdict


def calculate_accuracy(y_true: List[str], y_pred: List[str]) -> float:
    """Calculates overall classification accuracy."""
    if not y_true:
        return 1.0
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    return correct / len(y_true)


def calculate_precision_recall_f1(
    y_true: List[str], y_pred: List[str], target_class: str
) -> Tuple[float, float, float]:
    """Calculates Precision, Recall, and F1 score for a target class."""
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == target_class and yp == target_class)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != target_class and yp == target_class)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == target_class and yp != target_class)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return precision, recall, f1


def calculate_macro_weighted_f1(
    y_true: List[str], y_pred: List[str], classes: List[str]
) -> Dict[str, float]:
    """Calculates Macro and Weighted F1 scores across multiple classes."""
    class_counts = defaultdict(int)
    for yt in y_true:
        class_counts[yt] += 1

    total_samples = len(y_true)
    f1_scores = []
    weighted_f1_sum = 0.0

    for cls in classes:
        _, _, f1 = calculate_precision_recall_f1(y_true, y_pred, cls)
        f1_scores.append(f1)
        count = class_counts[cls]
        weighted_f1_sum += f1 * count

    macro_f1 = sum(f1_scores) / len(classes) if classes else 0.0
    weighted_f1 = weighted_f1_sum / total_samples if total_samples > 0 else 0.0

    return {
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
    }


def calculate_confusion_matrix(
    y_true: List[str], y_pred: List[str], classes: List[str]
) -> Dict[str, Any]:
    """
    Computes confusion matrix dictionary mapping class pairs to count.
    """
    matrix: Dict[str, Dict[str, int]] = {c1: {c2: 0 for c2 in classes} for c1 in classes}
    for yt, yp in zip(y_true, y_pred):
        if yt in matrix and yp in matrix[yt]:
            matrix[yt][yp] += 1

    return {
        "classes": classes,
        "matrix": matrix,
    }


def calculate_brier_score(y_true_binary: List[int], y_prob: List[float]) -> float:
    """
    Calculates Brier Score Calibration metric: (1/N) * sum((prob - actual)^2).
    Lower score indicates better probability calibration.
    """
    if not y_true_binary:
        return 0.0
    squared_errors = sum((prob - actual) ** 2 for actual, prob in zip(y_true_binary, y_prob))
    return round(squared_errors / len(y_true_binary), 4)


class MLEvaluator:
    """ML Model Evaluation Suite."""

    @staticmethod
    def evaluate_issue_classification(
        y_true: List[str], y_pred: List[str], categories: List[str]
    ) -> Dict[str, Any]:
        """Evaluates issue category classification model."""
        acc = calculate_accuracy(y_true, y_pred)
        f1_metrics = calculate_macro_weighted_f1(y_true, y_pred, categories)
        cm = calculate_confusion_matrix(y_true, y_pred, categories)

        return {
            "accuracy": round(acc, 4),
            "macro_f1": f1_metrics["macro_f1"],
            "weighted_f1": f1_metrics["weighted_f1"],
            "confusion_matrix": cm,
        }

    @staticmethod
    def evaluate_severity_prediction(
        y_true: List[str], y_pred: List[str], severities: List[str]
    ) -> Dict[str, Any]:
        """Evaluates issue severity prediction model."""
        f1_metrics = calculate_macro_weighted_f1(y_true, y_pred, severities)
        cm = calculate_confusion_matrix(y_true, y_pred, severities)

        return {
            "macro_f1": f1_metrics["macro_f1"],
            "weighted_f1": f1_metrics["weighted_f1"],
            "confusion_matrix": cm,
        }

    @staticmethod
    def evaluate_duplicate_detection(
        y_true: List[bool], y_pred: List[bool]
    ) -> Dict[str, float]:
        """Evaluates duplicate detection model."""
        str_true = ["DUP" if y else "NON_DUP" for y in y_true]
        str_pred = ["DUP" if y else "NON_DUP" for y in y_pred]

        prec, rec, f1 = calculate_precision_recall_f1(str_true, str_pred, "DUP")
        return {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
        }

    @staticmethod
    def evaluate_code_risk(
        y_true_risk: List[str],
        y_pred_risk: List[str],
        y_true_high_risk_binary: List[int],
        y_prob_high_risk: List[float],
    ) -> Dict[str, Any]:
        """Evaluates code risk classifier metrics and Brier score calibration."""
        acc = calculate_accuracy(y_true_risk, y_pred_risk)
        brier_score = calculate_brier_score(y_true_high_risk_binary, y_prob_high_risk)

        return {
            "accuracy": round(acc, 4),
            "brier_score_calibration": brier_score,
            "calibration_status": "WELL_CALIBRATED" if brier_score < 0.15 else "DEGRADED",
        }
