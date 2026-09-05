"""
Model 2: Issue Severity Prediction Pipeline.
Predicts issue severity into:
- LOW
- MEDIUM
- HIGH
- CRITICAL
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from app.core.logging import get_logger
from app.ml.features import clean_issue_text, extract_issue_metadata_features

logger = get_logger(__name__)

SEVERITY_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class IssueSeverityPredictor:
    """Predicts GitHub issue severity based on textual and metadata features."""

    VERSION = "severity-predictor-v1.0.0"

    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path) if model_path else None
        self.classes = SEVERITY_LEVELS
        self.vectorizer: TfidfVectorizer | None = None
        self.classifier: LogisticRegression | None = None
        self.is_trained = False

        if self.model_path and self.model_path.exists():
            self.load(self.model_path)
        else:
            self.vectorizer = TfidfVectorizer(max_features=2500, ngram_range=(1, 2))
            self.classifier = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)

    def _extract_features(
        self,
        titles: list[str],
        bodies: list[str | None],
        comments: list[int],
    ) -> np.ndarray:
        """Extract combined text TF-IDF features and metadata numerical features."""
        assert self.vectorizer is not None
        cleaned_texts = [clean_issue_text(f"{t} {b or ''}") for t, b in zip(titles, bodies)]
        text_features = self.vectorizer.transform(cleaned_texts).toarray()

        meta_features = np.array([
            extract_issue_metadata_features(t, b, c)
            for t, b, c in zip(titles, bodies, comments)
        ])

        return np.hstack([text_features, meta_features])

    def fit(
        self,
        titles: list[str],
        bodies: list[str | None],
        comments: list[int],
        labels: list[str],
    ) -> dict[str, Any]:
        """
        Train the severity prediction model.
        """
        self.vectorizer = TfidfVectorizer(max_features=2500, ngram_range=(1, 2))
        cleaned_texts = [clean_issue_text(f"{t} {b or ''}") for t, b in zip(titles, bodies)]
        text_features = self.vectorizer.fit_transform(cleaned_texts).toarray()

        meta_features = np.array([
            extract_issue_metadata_features(t, b, c)
            for t, b, c in zip(titles, bodies, comments)
        ])
        X = np.hstack([text_features, meta_features])

        self.classifier = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
        self.classifier.fit(X, labels)
        self.classes = list(self.classifier.classes_)
        self.is_trained = True

        train_score = self.classifier.score(X, labels)
        logger.info(
            "IssueSeverityPredictor trained successfully",
            version=self.VERSION,
            train_accuracy=round(float(train_score), 4),
            samples=len(titles),
        )
        return {
            "version": self.VERSION,
            "samples": len(titles),
            "train_accuracy": float(train_score),
            "classes": self.classes,
        }

    def predict(
        self,
        title: str,
        body: str | None = None,
        comment_count: int = 0,
    ) -> tuple[str, float]:
        """
        Predict severity level (LOW, MEDIUM, HIGH, CRITICAL) and confidence.
        """
        if not self.is_trained or self.classifier is None or self.vectorizer is None:
            return self._heuristic_predict(title, body)

        X = self._extract_features([title], [body], [comment_count])
        probabilities = self.classifier.predict_proba(X)[0]
        max_idx = int(probabilities.argmax())
        predicted_severity = str(self.classifier.classes_[max_idx])
        confidence = float(probabilities[max_idx])

        return predicted_severity, round(confidence, 4)

    def _heuristic_predict(self, title: str, body: str | None) -> tuple[str, float]:
        """Heuristic baseline when model is not yet trained."""
        text = f"{title} {body or ''}".lower()
        if any(w in text for w in ["cve", "breach", "vulnerability", "exploit", "critical", "data loss", "segfault", "panic"]):
            return "CRITICAL", 0.85
        if any(w in text for w in ["crash", "broken", "fatal", "outage", "blocker", "urgent", "regression"]):
            return "HIGH", 0.75
        if any(w in text for w in ["slow", "bug", "error", "fail", "unexpected", "leak"]):
            return "MEDIUM", 0.70
        return "LOW", 0.65

    def save(self, path: Path) -> None:
        """Save vectorizer and classifier artifacts."""
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"vectorizer": self.vectorizer, "classifier": self.classifier}, path)
        logger.info("Saved IssueSeverityPredictor model artifact", path=str(path))

    def load(self, path: Path) -> None:
        """Load vectorizer and classifier artifacts."""
        data = joblib.load(path)
        self.vectorizer = data["vectorizer"]
        self.classifier = data["classifier"]
        self.classes = list(self.classifier.classes_)
        self.is_trained = True
        logger.info("Loaded IssueSeverityPredictor model artifact", path=str(path))
