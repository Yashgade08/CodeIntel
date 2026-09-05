"""
Random Forest ML Model for Code Risk Intelligence.
Predicts continuous risk score (0-100) and categorical risk level (LOW, MEDIUM, HIGH).
Includes model serialization and graceful heuristic fallback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

from app.core.logging import get_logger
from app.ml.risk.features import FEATURE_NAMES, CodeFeatures

logger = get_logger(__name__)

DEFAULT_MODEL_PATH = Path("./storage/models/code_risk_model.joblib")
RISK_DISCLAIMER = (
    "This assessment estimates code and maintenance risk (structural complexity, churn, "
    "defect proneness, and maintainability overhead). It does NOT claim or identify security vulnerabilities."
)


class CodeRiskModel:
    """Random Forest regressor predicting continuous code risk score (0-100)."""

    VERSION = "code-risk-rf-v1.0.0"

    def __init__(self, model_path: Path | str | None = None) -> None:
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self.model: RandomForestRegressor | None = None
        self._is_trained = False
        self._load_if_available()

    def _load_if_available(self) -> bool:
        if self.model_path.exists():
            try:
                data = joblib.load(self.model_path)
                self.model = data["model"]
                self.VERSION = data.get("version", self.VERSION)
                self._is_trained = True
                logger.info("Loaded CodeRiskModel artifact", path=str(self.model_path), version=self.VERSION)
                return True
            except Exception as e:
                logger.warning("Failed to load CodeRiskModel artifact", path=str(self.model_path), error=str(e))
        return False

    @property
    def is_trained(self) -> bool:
        return self._is_trained and self.model is not None

    def fit(self, X: list[list[float]] | np.ndarray, y: list[float] | np.ndarray) -> None:
        """Fit Random Forest regressor on feature matrix X and target risk scores y."""
        X_arr = np.array(X)
        y_arr = np.array(y)

        rf = RandomForestRegressor(
            n_estimators=100,
            max_depth=6,
            min_samples_split=3,
            random_state=42,
        )
        rf.fit(X_arr, y_arr)
        self.model = rf
        self._is_trained = True

        logger.info(
            "CodeRiskModel trained successfully",
            samples=len(X_arr),
            version=self.VERSION,
        )

    def save(self, path: Path | str | None = None) -> Path:
        """Persist model artifact using joblib."""
        target_path = Path(path) if path else self.model_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "version": self.VERSION,
                "feature_names": FEATURE_NAMES,
            },
            target_path,
        )
        logger.info("Saved CodeRiskModel artifact", path=str(target_path))
        return target_path

    def predict(self, features: CodeFeatures | list[float]) -> tuple[int, str]:
        """
        Predict (risk_score, risk_level).
        risk_score: 0 - 100
        risk_level: LOW, MEDIUM, HIGH
        """
        vec = features.to_vector() if isinstance(features, CodeFeatures) else features
        if self.is_trained and self.model is not None:
            raw_score = float(self.model.predict([vec])[0])
            score = int(round(np.clip(raw_score, 0, 100)))
        else:
            score = self._heuristic_score(vec)

        level = self.score_to_level(score)
        return score, level

    @staticmethod
    def score_to_level(score: int) -> str:
        if score < 35:
            return "LOW"
        elif score < 70:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def _heuristic_score(vec: list[float]) -> int:
        """
        Rule-based heuristic baseline used when trained model artifact is not yet available.
        """
        loc, cc, n_funcs, n_classes, n_deps, n_imports, churn, commit_freq, n_contrib, issues = vec
        points = 0.0

        # Cyclomatic complexity factor
        if cc > 30:
            points += 30
        elif cc > 15:
            points += 18
        elif cc > 8:
            points += 8

        # Lines of code factor
        if loc > 1000:
            points += 20
        elif loc > 400:
            points += 12
        elif loc > 150:
            points += 6

        # Churn factor
        if churn > 2000:
            points += 20
        elif churn > 500:
            points += 12
        elif churn > 100:
            points += 6

        # Commit frequency & contributors (high churn + many cooks)
        if n_contrib > 5 and commit_freq > 20:
            points += 15
        elif n_contrib > 2:
            points += 7

        # Historical issue factor
        if issues > 5:
            points += 15
        elif issues > 0:
            points += 7

        return int(round(np.clip(points, 0, 100)))
