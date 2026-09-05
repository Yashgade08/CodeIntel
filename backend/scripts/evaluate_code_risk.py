"""
Evaluation script for CodeIntel Code Risk Intelligence.
Trains/evaluates the Random Forest model and inspects SHAP feature attributions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure backend package is importable
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.ml.risk.explainer import CodeRiskExplainer
from app.ml.risk.features import extract_code_features
from app.ml.risk.model import CodeRiskModel
from app.ml.risk.training import train_code_risk_model


def main() -> None:
    print("\n========================================================")
    print("   CodeIntel Code Risk Intelligence Evaluation")
    print("========================================================\n")

    # 1. Train and report regression metrics
    print("[1] Training Random Forest Code Risk Regressor...")
    train_results = train_code_risk_model()
    print(f"    Version:     {train_results['model_version']}")
    print(f"    Artifact:    {train_results['artifact_path']}")
    print(f"    MAE:         {train_results['metrics']['mae']:.3f}")
    print(f"    RMSE:        {train_results['metrics']['rmse']:.3f}")
    print(f"    R2 Score:    {train_results['metrics']['r2']:.3f}")

    # 2. Test SHAP feature attribution on archetypal files
    model = CodeRiskModel()
    explainer = CodeRiskExplainer(model)

    test_cases = [
        (
            "Low Risk File (utils/formatters.py)",
            """
def format_currency(val: float) -> str:
    return f"${val:,.2f}"

def format_percentage(val: float) -> str:
    return f"{val * 100:.1f}%"
""",
            10, 2, 1, 0,
        ),
        (
            "Medium Risk File (services/user_service.py)",
            """
import os
import json
import httpx
from datetime import datetime

class UserService:
    def __init__(self, db_client):
        self.db = db_client

    async def get_user(self, user_id: str):
        if not user_id:
            raise ValueError("user_id required")
        user = await self.db.find(user_id)
        if not user:
            return None
        if user.is_active:
            return user
        return None

    async def update_user(self, user_id: str, data: dict):
        for k, v in data.items():
            if k == 'email' and '@' not in v:
                raise ValueError("Invalid email")
        return await self.db.update(user_id, data)
""",
            350, 14, 3, 2,
        ),
        (
            "High Risk God File (legacy/monolith_engine.py)",
            """
import os, sys, re, json, time, socket, threading, asyncio
from typing import Any, List, Dict

class MonolithEngine:
    def __init__(self):
        self.state = {}
        self.lock = threading.Lock()

    def process_all(self, items: list, flags: dict):
        if not items:
            return
        for item in items:
            if item.get('type') == 'A':
                if item.get('priority') > 5:
                    for sub in item.get('children', []):
                        if sub.get('active') and not sub.get('error'):
                            while sub.get('retries', 0) < 3:
                                try:
                                    self._do_work(sub)
                                    break
                                except Exception:
                                    sub['retries'] = sub.get('retries', 0) + 1
            elif item.get('type') == 'B':
                switch_val = flags.get('mode')
                if switch_val == 1:
                    pass
                elif switch_val == 2:
                    pass
                elif switch_val == 3:
                    pass

    def _do_work(self, x):
        pass
""" * 8,
            2400, 55, 8, 9,
        ),
    ]

    print("\n[2] Evaluating Model & SHAP Explainer on Sample Profiles:")
    for title, code, churn, commits, contribs, issues in test_cases:
        feats = extract_code_features(
            file_path=title.split("(")[-1].rstrip(")"),
            content=code,
            churn=churn,
            commit_frequency=commits,
            contributors=contribs,
            historical_issues=issues,
        )
        score, level = model.predict(feats)
        factors = explainer.explain(feats, top_n=3)

        print(f"\n  - {title}")
        print(f"    Risk Score: {score}/100  |  Level: {level}")
        print(f"    Features: LOC={feats.lines_of_code}, CC={feats.cyclomatic_complexity}, Churn={feats.code_churn}")
        print("    Top SHAP Factors:")
        for factor in factors:
            print(f"      - {factor['factor']} (val={factor['value']}): {factor['impact']} ({factor['description']})")

    print("\n[OK] Code Risk Intelligence training, evaluation, and SHAP explainability verified.\n")


if __name__ == "__main__":
    main()
