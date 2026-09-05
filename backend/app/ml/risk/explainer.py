"""
Model explainability module using SHAP TreeExplainer for Code Risk Intelligence.
Calculates local SHAP feature contributions and generates human-readable risk factor summaries.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.core.logging import get_logger
from app.ml.risk.features import FEATURE_NAMES, CodeFeatures
from app.ml.risk.model import CodeRiskModel

logger = get_logger(__name__)

FACTOR_DESCRIPTIONS = {
    "cyclomatic_complexity": "High cyclomatic complexity ({val} decision points) creates complex branch logic that is error-prone.",
    "code_churn": "Substantial historical code churn ({val} line changes) indicates frequent volatility.",
    "lines_of_code": "Extensive file size ({val} LOC) creates excessive cognitive load and single-file coupling.",
    "historical_issue_count": "Historical issue count ({val} reports) indicates recurring bugs and defect hotspots.",
    "number_of_contributors": "High developer dispersion ({val} distinct contributors) creates coordination and style drift.",
    "commit_frequency": "Frequent revisions ({val} commits) indicate an unstable or actively mutating component.",
    "dependency_count": "Heavy dependency coupling ({val} external/internal modules) increases susceptibility to breaking changes.",
    "number_of_functions": "High function density ({val} functions) suggests excessive module responsibility.",
    "number_of_classes": "Multiple class definitions ({val} classes) may violate single-responsibility design.",
    "number_of_imports": "Extensive import footprint ({val} statements) signals high coupling.",
}


class CodeRiskExplainer:
    """SHAP-based model explainer for code risk predictions."""

    def __init__(self, risk_model: CodeRiskModel) -> None:
        self.risk_model = risk_model
        self._explainer: Any = None
        self._init_explainer()

    def _init_explainer(self) -> None:
        if self.risk_model.is_trained and self.risk_model.model is not None:
            try:
                import shap
                self._explainer = shap.TreeExplainer(self.risk_model.model)
                logger.info("Initialized SHAP TreeExplainer for CodeRiskModel")
            except Exception as e:
                logger.warning("Failed to initialize SHAP TreeExplainer", error=str(e))
                self._explainer = None

    def explain(self, features: CodeFeatures | list[float], top_n: int = 4) -> list[dict[str, Any]]:
        """
        Compute top risk factors using SHAP TreeExplainer.
        Returns a sorted list of factor dictionaries with impact and readable descriptions.
        """
        vec = features.to_vector() if isinstance(features, CodeFeatures) else features
        feat_dict = features.to_dict() if isinstance(features, CodeFeatures) else dict(zip(FEATURE_NAMES, vec))

        if self._explainer is None and self.risk_model.is_trained:
            self._init_explainer()

        if self._explainer is not None:
            try:
                X = np.array([vec])
                shap_values = self._explainer.shap_values(X)
                # If 2D array [1, num_features]
                if isinstance(shap_values, list):
                    values = shap_values[0][0]
                elif len(shap_values.shape) == 2:
                    values = shap_values[0]
                else:
                    values = shap_values

                factors = []
                for name, val, shap_val in zip(FEATURE_NAMES, vec, values):
                    # Only include factors with positive impact (increasing risk)
                    impact_sign = "+" if shap_val >= 0 else ""
                    desc_template = FACTOR_DESCRIPTIONS.get(name, "{name}: {val}")
                    desc = desc_template.format(val=int(val) if val.is_integer() else f"{val:.1f}")

                    factors.append({
                        "factor": name,
                        "value": int(val) if val.is_integer() else round(val, 2),
                        "shap_value": round(float(shap_val), 4),
                        "impact": f"{impact_sign}{shap_val:.2f}",
                        "description": desc,
                    })

                # Sort primarily by SHAP value descending (largest risk drivers first)
                factors.sort(key=lambda item: item["shap_value"], reverse=True)
                return factors[:top_n]
            except Exception as e:
                logger.warning("SHAP explanation failed, using fallback explanation", error=str(e))

        return self._fallback_explain(feat_dict, top_n=top_n)

    @staticmethod
    def _fallback_explain(feat_dict: dict[str, Any], top_n: int = 4) -> list[dict[str, Any]]:
        """Fallback feature importance calculation when SHAP is unavailable."""
        ranked: list[dict[str, Any]] = []

        # Relative risk heuristic checks
        weights = {
            "cyclomatic_complexity": (feat_dict.get("cyclomatic_complexity", 0) / 10.0),
            "code_churn": (feat_dict.get("code_churn", 0) / 200.0),
            "historical_issue_count": (feat_dict.get("historical_issue_count", 0) * 2.0),
            "lines_of_code": (feat_dict.get("lines_of_code", 0) / 100.0),
            "number_of_contributors": (feat_dict.get("number_of_contributors", 0) * 1.5),
            "dependency_count": (feat_dict.get("dependency_count", 0) * 0.8),
            "commit_frequency": (feat_dict.get("commit_frequency", 0) * 0.5),
        }

        for name, score in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            val = feat_dict.get(name, 0)
            desc_template = FACTOR_DESCRIPTIONS.get(name, "{name}: {val}")
            desc = desc_template.format(val=int(val) if isinstance(val, (int, float)) and float(val).is_integer() else val)
            ranked.append({
                "factor": name,
                "value": val,
                "shap_value": round(score, 2),
                "impact": f"+{score:.2f}",
                "description": desc,
            })

        return ranked[:top_n]
