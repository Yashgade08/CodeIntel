"""
Sentence Transformers embedding generator with model fallback support.
"""

from __future__ import annotations

import math
import re
from typing import Sequence

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingManager:
    """Manages dense vector embeddings generation using Sentence Transformers."""

    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model = None
        self._dimension = 384  # default dimension for all-MiniLM-L6-v2

    def _load_model(self) -> None:
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading SentenceTransformer model", model=self.model_name)
            self._model = SentenceTransformer(self.model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
        except Exception as e:
            logger.warning(
                "Could not load SentenceTransformer model, using deterministic fallback vector encoder",
                error=str(e),
            )
            self._model = "fallback"

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """
        Generate dense embeddings for a list of text strings.
        
        Returns normalized float vector embeddings.
        """
        if not texts:
            return []

        self._load_model()

        if self._model != "fallback":
            try:
                embeddings = self._model.encode(
                    list(texts),
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                return [vec.tolist() for vec in embeddings]
            except Exception as e:
                logger.error("SentenceTransformer encoding error, falling back", error=str(e))

        # Fallback deterministic vector generator
        return [self._fallback_embed(text) for text in texts]

    def embed_query(self, query: str) -> list[float]:
        """Generate vector embedding for a single user query."""
        results = self.embed_texts([query])
        return results[0] if results else [0.0] * self._dimension

    def _fallback_embed(self, text: str) -> list[float]:
        """Deterministic feature hashing vector fallback (384 dimensions)."""
        dim = self._dimension
        vec = [0.0] * dim
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return vec

        for token in tokens:
            # Hash token to index and sign
            h = hash(token)
            idx = abs(h) % dim
            val = 1.0 if h > 0 else -1.0
            vec[idx] += val

        # Normalize L2 norm
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec
