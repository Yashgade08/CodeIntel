"""
Embedding Provider Interface
"""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract interface for text/code embedding generation."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a list of code documents/chunks."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Generate an embedding vector for a single search query."""
        pass
