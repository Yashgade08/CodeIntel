"""
Training pipeline and seed dataset for Code Risk Intelligence.
Trains a Random Forest regressor, calculates MAE, MSE, and R2 evaluation metrics,
and serializes model artifacts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from app.core.logging import get_logger
from app.ml.risk.features import FEATURE_NAMES
from app.ml.risk.model import DEFAULT_MODEL_PATH, CodeRiskModel

logger = get_logger(__name__)

# Seed dataset: [LOC, CC, n_funcs, n_classes, n_deps, n_imports, churn, commit_freq, n_contrib, issues], target_risk_score
SEED_RISK_DATA: list[tuple[list[float], float]] = [
    # ── LOW Risk Profiles (Scores 5 - 30)
    ([45, 2, 3, 0, 2, 2, 20, 2, 1, 0], 12.0),
    ([60, 1, 0, 2, 1, 1, 15, 1, 1, 0], 8.0),
    ([110, 3, 5, 1, 3, 3, 50, 3, 1, 0], 18.0),
    ([75, 2, 2, 1, 2, 2, 30, 2, 1, 0], 15.0),
    ([95, 4, 4, 1, 3, 3, 65, 4, 2, 0], 22.0),
    ([30, 1, 1, 0, 1, 1, 10, 1, 1, 0], 5.0),
    ([140, 5, 6, 1, 4, 4, 85, 5, 2, 1], 26.0),
    ([80, 3, 3, 1, 2, 2, 40, 2, 1, 0], 16.0),

    # ── MEDIUM Risk Profiles (Scores 35 - 68)
    ([240, 12, 8, 2, 6, 7, 320, 14, 3, 2], 48.0),
    ([310, 16, 9, 1, 7, 8, 480, 18, 4, 3], 55.0),
    ([180, 14, 5, 1, 4, 5, 260, 11, 2, 1], 42.0),
    ([290, 18, 10, 3, 5, 6, 410, 15, 3, 2], 52.0),
    ([350, 15, 7, 1, 8, 9, 520, 16, 4, 2], 58.0),
    ([210, 11, 6, 2, 5, 5, 280, 10, 2, 1], 39.0),
    ([420, 20, 12, 2, 9, 10, 680, 22, 5, 4], 66.0),
    ([260, 13, 7, 1, 6, 6, 350, 12, 3, 2], 49.0),

    # ── HIGH Risk Profiles (Scores 70 - 98)
    ([1250, 42, 28, 4, 16, 19, 2800, 65, 9, 8], 88.0),
    ([1800, 56, 35, 6, 22, 25, 4100, 84, 12, 14], 95.0),
    ([890, 34, 19, 3, 14, 15, 2200, 52, 7, 6], 79.0),
    ([1100, 48, 15, 2, 11, 12, 1950, 44, 6, 9], 84.0),
    ([950, 38, 18, 5, 15, 18, 2400, 58, 8, 11], 91.0),
    ([1450, 50, 32, 5, 18, 21, 3500, 72, 10, 12], 93.0),
    ([780, 31, 16, 2, 12, 13, 1750, 38, 6, 5], 74.0),
    ([1020, 36, 22, 3, 13, 16, 2100, 49, 7, 7], 82.0),
]


def train_code_risk_model(model_path: Path | None = None) -> dict[str, Any]:
    """
    Train Random Forest regressor on seed software engineering dataset and persist model artifact.
    """
    target_path = model_path or DEFAULT_MODEL_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    X = [item[0] for item in SEED_RISK_DATA]
    y = [item[1] for item in SEED_RISK_DATA]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42
    )

    model = CodeRiskModel(target_path)
    model.fit(X_train, y_train)

    # Predictions & metrics
    y_pred = [model.predict(vec)[0] for vec in X_test]
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = float(np.sqrt(mse))
    r2 = r2_score(y_test, y_pred)

    saved_path = model.save(target_path)

    logger.info(
        "Code risk model trained and saved successfully",
        mae=mae,
        rmse=rmse,
        r2=r2,
        artifact=str(saved_path),
    )

    return {
        "status": "trained",
        "model_version": model.VERSION,
        "artifact_path": str(saved_path),
        "samples_trained": len(X_train),
        "metrics": {
            "mae": round(mae, 3),
            "rmse": round(rmse, 3),
            "r2": round(r2, 3),
        },
    }


if __name__ == "__main__":
    import json
    print("=" * 60)
    print("Training Code Risk Intelligence Model...")
    print("=" * 60)
    res = train_code_risk_model()
    print(f"Model Version: {res['model_version']}")
    print(f"Artifact Path: {res['artifact_path']}")
    print(f"Metrics:       {json.dumps(res['metrics'], indent=2)}")
    print("=" * 60)
