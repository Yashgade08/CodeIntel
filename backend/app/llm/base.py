"""
LLM Provider Interface
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract interface for LLM interaction with structured JSON output."""

    @abstractmethod
    def generate_analysis(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """
        Sends system and user prompt to the LLM and returns parsed JSON.
        Raises ValueError / RuntimeError on network error or invalid JSON.
        """
        pass
