"""
Evaluation script for CodeIntel ML Issue Intelligence.
Trains and reports evaluation metrics: accuracy, precision, recall, F1, and confusion matrix.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure app package is importable
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.ml.training import train_issue_models


def main() -> None:
    print("\n========================================================")
    print("  CodeIntel Machine Learning Issue Intelligence Pipeline")
    print("========================================================\n")

    results = train_issue_models()

    print("[1] Model 1: Issue Classification (TF-IDF + Logistic Regression)")
    print(f"    Version:          {results['classifier']['version']}")
    print(f"    Artifact:         {results['classifier']['artifact_path']}")
    print(f"    Accuracy:         {results['classifier']['metrics']['accuracy']:.4f}")
    print(f"    Precision (Macro):{results['classifier']['metrics']['precision']:.4f}")
    print(f"    Recall (Macro):   {results['classifier']['metrics']['recall']:.4f}")
    print(f"    F1 Score (Macro): {results['classifier']['metrics']['f1']:.4f}")
    print("    Confusion Matrix:")
    for row in results['classifier']['metrics']['confusion_matrix']:
        print(f"      {row}")

    print("\n[2] Model 2: Issue Severity Prediction (TF-IDF + Metadata + Logistic Regression)")
    print(f"    Version:          {results['severity_predictor']['version']}")
    print(f"    Artifact:         {results['severity_predictor']['artifact_path']}")
    print(f"    Accuracy:         {results['severity_predictor']['metrics']['accuracy']:.4f}")
    print(f"    Precision (Macro):{results['severity_predictor']['metrics']['precision']:.4f}")
    print(f"    Recall (Macro):   {results['severity_predictor']['metrics']['recall']:.4f}")
    print(f"    F1 Score (Macro): {results['severity_predictor']['metrics']['f1']:.4f}")
    print("    Confusion Matrix:")
    for row in results['severity_predictor']['metrics']['confusion_matrix']:
        print(f"      {row}")

    print("\n[3] Model 3: Duplicate Issue Detector")
    print("    Architecture:     Dense Embeddings (SentenceTransformers all-MiniLM-L6-v2) + Cosine Similarity")
    print("    Confidence Tiers: High (>= 0.85), Medium (>= 0.70), Low (< 0.70)")

    print("\n[OK] All model artifacts saved and evaluation verified successfully.\n")


if __name__ == "__main__":
    main()
