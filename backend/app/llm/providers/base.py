"""
Abstract Base Class for LLM Provider Abstraction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseLLMProvider(ABC):
    """Abstract interface for configurable LLM providers (OpenAI, Local/Mock, Anthropic)."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.1,
    ) -> str:
        """Generate a complete text response asynchronously."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        """Stream token chunks asynchronously."""
        pass
