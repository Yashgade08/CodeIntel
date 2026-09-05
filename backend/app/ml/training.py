"""
Training pipeline and seed dataset for GitHub issue classification & severity prediction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sklearn.model_selection import train_test_split

from app.core.logging import get_logger
from app.ml.evaluation import evaluate_classifier
from app.ml.issue_classifier import ISSUE_CLASSES, IssueClassifier
from app.ml.severity_predictor import SEVERITY_LEVELS, IssueSeverityPredictor

logger = get_logger(__name__)

# Default model artifacts storage directory
DEFAULT_MODELS_DIR = Path("./storage/models")

# Seed dataset representing standard GitHub issues across 7 categories and 4 severities
SEED_ISSUES_DATA = [
    # ── Bug (LOW, MEDIUM, HIGH, CRITICAL)
    ("NullPointerException when parsing malformed JSON payload", "Application crashes with traceback in JsonParser.java line 102", 4, "Bug", "HIGH"),
    ("Application segfault on startup when AVX instructions are missing", "Fatal crash segfault on Linux x86_64 during bootstrap", 12, "Bug", "CRITICAL"),
    ("Button alignment is off by 2px on Safari iOS", "Minor visual glitch in navbar submit button styling", 1, "Bug", "LOW"),
    ("Form validation error message does not clear on reset", "The error tooltip stays visible after clicking cancel", 2, "Bug", "LOW"),
    ("Database connection pool leak under high concurrency", "Connections not released causing 504 gateway timeout after 100 requests", 8, "Bug", "HIGH"),
    ("Worker thread deadlock causes ingestion to halt completely", "Severe deadlock in worker pool threads, zero progress made", 6, "Bug", "CRITICAL"),
    ("Pagination offset calculation fails on last page", "Expected 10 items returned 0 when page index equals total pages", 3, "Bug", "MEDIUM"),
    ("TypeError: undefined is not an object in UserProfile.tsx", "Uncaught runtime exception on profile page rendering", 5, "Bug", "MEDIUM"),

    # ── Feature Request
    ("Add dark mode theme support", "Allow users to switch between light and dark themes in user settings", 15, "Feature Request", "LOW"),
    ("Support OAuth2 login with GitHub and GitLab", "Provide single sign-on authentication via popular Git providers", 20, "Feature Request", "MEDIUM"),
    ("Export repository dependency graph as SVG or PNG", "Users should be able to download the rendered graph", 7, "Feature Request", "LOW"),
    ("Add webhook notifications for completed repository ingestion", "Send HTTP POST payload to external endpoints when pipeline finishes", 9, "Feature Request", "MEDIUM"),
    ("Implement support for multi-branch code indexing", "Allow selecting specific branches instead of only default branch", 11, "Feature Request", "MEDIUM"),

    # ── Documentation
    ("Fix broken link in README quickstart guide", "The link to docker-compose installation returns 404", 1, "Documentation", "LOW"),
    ("Update API documentation with new /api/chat endpoints", "Swagger docs are missing parameter descriptions for streaming SSE", 3, "Documentation", "LOW"),
    ("Clarify environment variable configuration in deployment docs", "Explain difference between CHROMA_HOST and local vector store", 2, "Documentation", "LOW"),
    ("Add contribution guide and code style instructions", "CONTRIBUTING.md is currently missing from repository root", 4, "Documentation", "LOW"),

    # ── Question
    ("How to configure custom port for ChromaDB in Docker Compose?", "I want to change the port from 8001 to 8080, where should I change it?", 3, "Question", "LOW"),
    ("Is there a way to run embedding models on GPU?", "Can SentenceTransformers leverage CUDA if torch is installed?", 5, "Question", "LOW"),
    ("Why does ingestion fail with shallow clone on private repositories?", "Does the cloner support passing personal access tokens?", 4, "Question", "MEDIUM"),
    ("What are the minimum hardware requirements for running CodeIntel?", "How much RAM is required for ChromaDB and PostgreSQL?", 2, "Question", "LOW"),

    # ── Enhancement
    ("Improve indexing speed by batching ChromaDB insertions", "Insert 100 chunks per batch instead of single chunk requests", 6, "Enhancement", "MEDIUM"),
    ("Optimize BM25 tokenization with caching for frequently searched repos", "Cache inverted index to avoid rebuilding every query", 8, "Enhancement", "MEDIUM"),
    ("Refactor repository service to use connection pooling properly", "Clean up session lifecycle management across background workers", 4, "Enhancement", "LOW"),
    ("Add toast notification when repository URL is copied to clipboard", "Better user feedback in frontend header component", 2, "Enhancement", "LOW"),

    # ── Performance
    ("High CPU usage during file tree scanning of large repositories", "Scanner causes 100% CPU spike when traversing deep node_modules or vendor", 14, "Performance", "HIGH"),
    ("Slow vector retrieval query times with over 50,000 chunks", "Query latency exceeds 3000ms on dense vector cosine search", 18, "Performance", "HIGH"),
    ("Memory footprint grows unboundedly during large git clone operations", "Memory leak in subprocess stream buffer reading", 10, "Performance", "HIGH"),
    ("API latency spike under 50 concurrent requests on /api/repositories", "Database pool exhaustion causes 2000ms TTFB", 9, "Performance", "HIGH"),

    # ── Security
    ("SQL Injection vulnerability in repository search query filter", "Sanitize user input before passing parameters into raw SQL query", 25, "Security", "CRITICAL"),
    ("Path traversal vulnerability allows reading arbitrary host files via cloner", "Cloner does not sanitize repo_id leading to ../../ traversal", 30, "Security", "CRITICAL"),
    ("Insecure direct object reference (IDOR) on /api/issues/{id}", "Users can view private issues belonging to other organizations", 16, "Security", "HIGH"),
    ("Cross-Site Scripting (XSS) in issue markdown preview renderer", "Unsanitized HTML tags in issue body are executed in DOM", 19, "Security", "HIGH"),
    ("API secret key exposed in debug error logs", "Remove authorization bearer tokens from structlog error traces", 12, "Security", "CRITICAL"),
]


def train_issue_models(models_dir: Path | None = None) -> dict[str, Any]:
    """
    Train both IssueClassifier and IssueSeverityPredictor on seed dataset,
    calculate evaluation metrics, and persist model artifacts.
    """
    target_dir = models_dir or DEFAULT_MODELS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    titles = [item[0] for item in SEED_ISSUES_DATA]
    bodies = [item[1] for item in SEED_ISSUES_DATA]
    comments = [item[2] for item in SEED_ISSUES_DATA]
    type_labels = [item[3] for item in SEED_ISSUES_DATA]
    severity_labels = [item[4] for item in SEED_ISSUES_DATA]

    full_texts = [f"{t} {b}" for t, b in zip(titles, bodies)]

    # ── 1. Train Issue Classifier ────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        full_texts, type_labels, test_size=0.25, random_state=42, stratify=type_labels
    )

    classifier = IssueClassifier()
    classifier.fit(X_train, y_train)

    y_pred_class = [classifier.predict(t)[0] for t in X_test]
    class_metrics = evaluate_classifier(y_test, y_pred_class, labels=ISSUE_CLASSES)

    classifier_path = target_dir / "issue_classifier.joblib"
    classifier.save(classifier_path)

    # ── 2. Train Severity Predictor ──────────────────────────────────────────
    t_train, t_test, b_train, b_test, c_train, c_test, s_train, s_test = train_test_split(
        titles, bodies, comments, severity_labels, test_size=0.25, random_state=42, stratify=severity_labels
    )

    severity_predictor = IssueSeverityPredictor()
    severity_predictor.fit(t_train, b_train, c_train, s_train)

    s_pred = [severity_predictor.predict(t, b, c)[0] for t, b, c in zip(t_test, b_test, c_test)]
    severity_metrics = evaluate_classifier(s_test, s_pred, labels=SEVERITY_LEVELS)

    severity_path = target_dir / "severity_predictor.joblib"
    severity_predictor.save(severity_path)

    logger.info(
        "Issue models trained and saved successfully",
        classifier_f1=class_metrics["f1"],
        severity_f1=severity_metrics["f1"],
        storage=str(target_dir),
    )

    return {
        "status": "trained",
        "models_directory": str(target_dir),
        "classifier": {
            "version": classifier.VERSION,
            "metrics": class_metrics,
            "artifact_path": str(classifier_path),
        },
        "severity_predictor": {
            "version": severity_predictor.VERSION,
            "metrics": severity_metrics,
            "artifact_path": str(severity_path),
        },
    }


if __name__ == "__main__":
    import json
    print("=" * 60)
    print("Training Issue Intelligence Models...")
    print("=" * 60)
    results = train_issue_models()
    print("\n--- Model 1: Issue Classification ---")
    print(f"Artifact: {results['classifier']['artifact_path']}")
    print(f"Accuracy:  {results['classifier']['metrics']['accuracy']:.4f}")
    print(f"Macro P:   {results['classifier']['metrics']['precision']:.4f}")
    print(f"Macro R:   {results['classifier']['metrics']['recall']:.4f}")
    print(f"Macro F1:  {results['classifier']['metrics']['f1']:.4f}")
    print(f"Confusion Matrix:\n{json.dumps(results['classifier']['metrics']['confusion_matrix'], indent=2)}")

    print("\n--- Model 2: Issue Severity Prediction ---")
    print(f"Artifact: {results['severity_predictor']['artifact_path']}")
    print(f"Accuracy:  {results['severity_predictor']['metrics']['accuracy']:.4f}")
    print(f"Macro P:   {results['severity_predictor']['metrics']['precision']:.4f}")
    print(f"Macro R:   {results['severity_predictor']['metrics']['recall']:.4f}")
    print(f"Macro F1:  {results['severity_predictor']['metrics']['f1']:.4f}")
    print(f"Confusion Matrix:\n{json.dumps(results['severity_predictor']['metrics']['confusion_matrix'], indent=2)}")
    print("=" * 60)
    print("Training and Evaluation complete.")

