"""
Embedding Provider Factory
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.local_embeddings import LocalEmbeddingProvider


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    """Factory returning the configured EmbeddingProvider singleton."""
    settings = get_settings()
    # Default to high-performance local SentenceTransformer
    return LocalEmbeddingProvider(model_name=settings.EMBEDDING_MODEL)
