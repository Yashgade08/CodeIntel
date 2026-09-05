"""
Model 1: Issue Classification Pipeline (TF-IDF + Logistic Regression).
Classifies GitHub issues into:
- Bug
- Feature Request
- Documentation
- Question
- Enhancement
- Performance
- Security
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.core.logging import get_logger
from app.ml.features import clean_issue_text

logger = get_logger(__name__)

ISSUE_CLASSES = [
    "Bug",
    "Feature Request",
    "Documentation",
    "Question",
    "Enhancement",
    "Performance",
    "Security",
]


class IssueClassifier:
    """Multi-class GitHub issue classification pipeline."""

    VERSION = "issue-classifier-v1.0.0"

    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path) if model_path else None
        self.classes = ISSUE_CLASSES
        self.pipeline: Pipeline | None = None
        self.is_trained = False

        if self.model_path and self.model_path.exists():
            self.load(self.model_path)
        else:
            self._init_pipeline()

    def _init_pipeline(self) -> None:
        """Initialize the default scikit-learn pipeline."""
        self.pipeline = Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    max_features=5000,
                    sublinear_tf=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=42,
                ),
            ),
        ])

    def fit(self, texts: list[str], labels: list[str]) -> dict[str, Any]:
        """
        Train the classification pipeline.
        
        Returns training metrics and class distribution.
        """
        cleaned_texts = [clean_issue_text(t) for t in texts]
        self._init_pipeline()
        assert self.pipeline is not None

        self.pipeline.fit(cleaned_texts, labels)
        self.classes = list(self.pipeline.classes_)
        self.is_trained = True

        train_score = self.pipeline.score(cleaned_texts, labels)
        logger.info(
            "IssueClassifier trained successfully",
            version=self.VERSION,
            classes=self.classes,
            train_accuracy=round(float(train_score), 4),
            samples=len(texts),
        )
        return {
            "version": self.VERSION,
            "samples": len(texts),
            "train_accuracy": float(train_score),
            "classes": self.classes,
        }

    def predict(self, title: str, body: str | None = None) -> tuple[str, float]:
        """
        Predict issue category and confidence score.
        
        Returns (predicted_type, confidence).
        """
        if not self.is_trained or self.pipeline is None:
            # Heuristic rule-based fallback if model is not yet trained
            return self._heuristic_predict(title, body)

        full_text = clean_issue_text(f"{title} {body or ''}")
        probabilities = self.pipeline.predict_proba([full_text])[0]
        max_idx = int(probabilities.argmax())
        predicted_class = str(self.pipeline.classes_[max_idx])
        confidence = float(probabilities[max_idx])

        return predicted_class, round(confidence, 4)

    def predict_proba(self, title: str, body: str | None = None) -> dict[str, float]:
        """Get class probability distribution for an issue."""
        if not self.is_trained or self.pipeline is None:
            pred, conf = self._heuristic_predict(title, body)
            return {c: (conf if c == pred else (1.0 - conf) / (len(self.classes) - 1)) for c in self.classes}

        full_text = clean_issue_text(f"{title} {body or ''}")
        probabilities = self.pipeline.predict_proba([full_text])[0]
        return {
            str(cls): round(float(prob), 4)
            for cls, prob in zip(self.pipeline.classes_, probabilities)
        }

    def _heuristic_predict(self, title: str, body: str | None) -> tuple[str, float]:
        """Baseline heuristic fallback before model training."""
        text = f"{title} {body or ''}".lower()
        if any(w in text for w in ["vulnerability", "cve", "breach", "exploit", "xss", "csrf", "sqli"]):
            return "Security", 0.85
        if any(w in text for w in ["slow", "latency", "lag", "cpu", "memory leak", "performance", "bottleneck"]):
            return "Performance", 0.80
        if any(w in text for w in ["docs", "readme", "documentation", "typo", "tutorial"]):
            return "Documentation", 0.85
        if any(w in text for w in ["how to", "how do i", "why does", "is there a way", "question", "?"]):
            return "Question", 0.75
        if any(w in text for w in ["crash", "error", "fail", "broken", "bug", "traceback", "exception"]):
            return "Bug", 0.80
        if any(w in text for w in ["add support", "new feature", "feature request", "would be great"]):
            return "Feature Request", 0.75
        return "Enhancement", 0.65

    def save(self, path: Path) -> None:
        """Save serialized pipeline artifact."""
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, path)
        logger.info("Saved IssueClassifier model artifact", path=str(path))

    def load(self, path: Path) -> None:
        """Load serialized pipeline artifact."""
        self.pipeline = joblib.load(path)
        self.classes = list(self.pipeline.classes_)
        self.is_trained = True
        logger.info("Loaded IssueClassifier model artifact", path=str(path), classes=self.classes)
