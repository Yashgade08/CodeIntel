"""
LLM Provider Factory.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.providers.base import BaseLLMProvider
from app.llm.providers.gemini_provider import GeminiProvider
from app.llm.providers.groq_provider import GroqProvider
from app.llm.providers.mock_provider import MockLLMProvider
from app.llm.providers.openai_provider import OpenAIProvider

logger = get_logger(__name__)


def get_llm_provider(provider_name: str | None = None) -> BaseLLMProvider:
    """
    Factory function returning the configured LLM provider instance.
    Checks Gemini, Groq, OpenAI, or defaults to MockLLMProvider.
    """
    settings = get_settings()
    selected = (provider_name or settings.LLM_PROVIDER).lower()

    if selected == "gemini" and settings.GEMINI_API_KEY:
        logger.info("Using Gemini LLM Provider", model=settings.GEMINI_MODEL)
        return GeminiProvider()

    if selected == "groq" and settings.GROQ_API_KEY:
        logger.info("Using Groq LLM Provider", model=settings.GROQ_MODEL)
        return GroqProvider()

    if selected == "openai" and settings.OPENAI_API_KEY:
        logger.info("Using OpenAI LLM Provider", model=settings.OPENAI_MODEL)
        return OpenAIProvider()

    # Fallback checks if key exists even if LLM_PROVIDER wasn't updated
    if settings.GEMINI_API_KEY:
        logger.info("Using Gemini LLM Provider", model=settings.GEMINI_MODEL)
        return GeminiProvider()

    if settings.GROQ_API_KEY:
        logger.info("Using Groq LLM Provider", model=settings.GROQ_MODEL)
        return GroqProvider()

    if settings.OPENAI_API_KEY:
        logger.info("Using OpenAI LLM Provider", model=settings.OPENAI_MODEL)
        return OpenAIProvider()

    logger.info("Using Mock LLM Provider (Free Offline Mode)")
    return MockLLMProvider()
