"""
Offline Mock LLM Provider Implementation.
Generates deterministic, evidence-grounded response text and token streams.
"""

from __future__ import annotations

import asyncio
import re
from typing import AsyncGenerator

from app.core.logging import get_logger
from app.llm.providers.base import BaseLLMProvider

logger = get_logger(__name__)


class MockLLMProvider(BaseLLMProvider):
    """Offline mock LLM provider for local execution, fallback, and unit testing."""

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.1,
    ) -> str:
        """Generate response grounded in evidence extracted from prompt."""
        # Extract citation references if present in prompt
        citations = re.findall(r"\[([a-zA-Z0-9_/\-\.]+:\d+(?:-\d+)?)\]", prompt)
        
        # Check if hallucination safeguard was requested in prompt
        if "I couldn't find enough evidence" in prompt:
            return "I couldn't find enough evidence in this repository to answer confidently."

        main_citation = citations[0] if citations else "codebase"
        
        # Extract question lines
        user_query = "this topic"
        for line in prompt.splitlines():
            if line.startswith("User Query:"):
                user_query = line.replace("User Query:", "").strip()
                break

        response = (
            f"Based on repository evidence in `[{main_citation}]`:\n\n"
            f"1. **Implementation Details (Facts)**: The codebase addresses '{user_query}' in `[{main_citation}]`.\n"
            f"2. **Architectural Flow (Inference)**: Surrounding module dependencies interact with this logic during execution.\n"
        )
        return response

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        """Stream token chunks asynchronously."""
        full_text = await self.generate(prompt, system_prompt, temperature)
        words = full_text.split(" ")
        for word in words:
            yield word + " "
            await asyncio.sleep(0.01)
