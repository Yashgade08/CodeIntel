"""
Application configuration using pydantic-settings.

All environment variables are defined here with sensible defaults
for local Docker Compose development.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=[
            str(Path(__file__).resolve().parent.parent.parent / ".env"),
            ".env",
        ],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "CodeIntel"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:5173"])

    # ── Database (PostgreSQL) ────────────────────────────────────────────
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://codeintel:codeintel@localhost:5432/codeintel"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    # ── Redis ────────────────────────────────────────────────────────────
    REDIS_URL: RedisDsn = Field(default="redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = 20

    # ── ChromaDB ─────────────────────────────────────────────────────────
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"

    # ── GitHub & Ingestion ───────────────────────────────────────────────
    GITHUB_TOKEN: str = ""
    GITHUB_API_BASE: str = "https://api.github.com"
    REPO_STORAGE_PATH: str = "./storage/repos"
    MAX_FILE_SIZE_BYTES: int = 1_048_576  # 1 MB
    MAX_FILE_SIZE_MB: int = 5
    MAX_REPO_SIZE_BYTES: int = 104_857_600  # 100 MB
    GITHUB_MAX_ISSUES: int = 100

    # ── LLM ──────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_API_BASE: str = "https://api.groq.com/openai/v1"
    LLM_PROVIDER: str = "gemini"  # gemini, openai, groq
    LLM_TEMPERATURE: float = 0.1
    MAX_CONVERSATION_HISTORY: int = 6

    # ── Embeddings & RAG ─────────────────────────────────────────────────
    EMBEDDING_PROVIDER: str = "local"  # local (SentenceTransformers), openai, gemini
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_API_KEY: str = ""
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    TOP_K: int = 8
    TOP_K_RETRIEVAL: int = 20
    TOP_K_FINAL: int = 8
    SIMILARITY_THRESHOLD: float = 0.35

    # ── Security ─────────────────────────────────────────────────────────
    API_SECRET_KEY: str = "dev-secret-key-change-in-production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — parsed once at startup."""
    return Settings()
