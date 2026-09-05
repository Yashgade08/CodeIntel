"""
Machine Learning models and pipelines.

Independent ML models for issue triage and code quality analysis.
Full implementation in Phase 4.

Submodules (to be created):
- base.py                 — Abstract model interface
- feature_engineering.py  — Feature extraction pipeline
- issue_classifier.py     — Issue type classification (XGBoost)
- severity_predictor.py   — Issue severity prediction (XGBoost)
- duplicate_detector.py   — Duplicate issue detection (embeddings + clustering)
- code_risk_predictor.py  — File-level risk scoring (XGBoost)
- training/               — Training scripts
- evaluation/             — Evaluation metrics and cross-validation
- explainability/         — SHAP explanations
"""
