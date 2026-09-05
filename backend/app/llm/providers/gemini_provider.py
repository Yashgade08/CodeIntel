"""
Google Gemini LLM Provider Implementation (using Google AI Studio's OpenAI-compatible API endpoint).
"""

from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.providers.base import BaseLLMProvider

logger = get_logger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider using Google AI Studio free API key."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.1,
    ) -> str:
        """Generate response via Gemini API."""
        if not self.api_key:
            logger.warning("Gemini API key missing, returning provider notification")
            return f"[Gemini API key missing] Prompt processed: {prompt[:100]}..."

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.api_url, headers=self._get_headers(), json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error("Gemini API call failed", error=str(e))
                return f"Error communicating with Gemini API: {str(e)}"

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        """Stream token chunks via Gemini API."""
        if not self.api_key:
            yield "[Gemini API key missing]"
            return

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                async with client.stream(
                    "POST", self.api_url, headers=self._get_headers(), json=payload
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk["choices"][0]["delta"].get("content", "")
                                if delta:
                                    yield delta
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.error("Gemini streaming failed", error=str(e))
                yield f"[Error: {str(e)}]"
