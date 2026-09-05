"""
LLM Provider Factory
"""

from __future__ import annotations

from app.core.config import get_settings
from app.llm.base import LLMProvider
from app.llm.gemini_provider import GeminiLLMProvider
from app.llm.openai_provider import OpenAILLMProvider


def get_llm_provider() -> LLMProvider:
    """Instantiate and return the configured LLMProvider based on settings."""
    settings = get_settings()
    provider_name = (settings.LLM_PROVIDER or "gemini").lower().strip()

    if provider_name == "gemini":
        return GeminiLLMProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
            api_base=settings.GEMINI_API_BASE,
        )
    elif provider_name == "groq":
        return OpenAILLMProvider(
            api_key=settings.GROQ_API_KEY,
            model=settings.GROQ_MODEL,
            api_base=settings.GROQ_API_BASE,
            provider_name="Groq",
        )
    elif provider_name in ("openai", "openai-compatible"):
        return OpenAILLMProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            api_base=settings.OPENAI_API_BASE,
            provider_name="OpenAI",
        )
    else:
        # Fallback to gemini if available or openai
        if settings.GEMINI_API_KEY:
            return GeminiLLMProvider(
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_MODEL,
                api_base=settings.GEMINI_API_BASE,
            )
        return OpenAILLMProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            api_base=settings.OPENAI_API_BASE,
            provider_name="OpenAI",
        )
