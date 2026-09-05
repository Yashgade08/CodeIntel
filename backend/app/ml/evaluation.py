"""
Evaluation metrics calculation utilities for issue ML models.
Tracks:
- accuracy
- precision
- recall
- F1-score
- confusion matrix
"""

from __future__ import annotations

from typing import Any

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


def evaluate_classifier(
    y_true: list[str],
    y_pred: list[str],
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """
    Calculate classification metrics: accuracy, precision, recall, F1, and confusion matrix.
    """
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, average="macro", zero_division=0)
    rec = recall_score(y_true, y_pred, average="macro", zero_division=0)
    f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)

    return {
        "accuracy": round(float(acc), 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1": round(float(f1), 4),
        "weighted_f1": round(float(weighted_f1), 4),
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
        "labels": labels or list(set(y_true)),
    }
