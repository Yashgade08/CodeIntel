"""
OpenAI & Groq API LLM Provider
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.llm.base import LLMProvider


class OpenAILLMProvider(LLMProvider):
    """
    OpenAI-compatible LLM Provider (supports OpenAI, Groq, OpenRouter, Ollama, etc.).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        api_base: str = "https://api.openai.com/v1",
        provider_name: str = "OpenAI",
    ):
        self.api_key = (api_key or "").strip()
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.provider_name = provider_name

    def generate_analysis(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        if not self.api_key:
            env_var = "GROQ_API_KEY" if "groq" in self.provider_name.lower() else "OPENAI_API_KEY"
            raise ValueError(
                f"LLM_API_KEY_MISSING: {self.provider_name} API key is not configured. Set {env_var} in backend/.env"
            )

        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code != 200:
                    err_text = response.text
                    raise RuntimeError(f"{self.provider_name} API returned HTTP {response.status_code}: {err_text}")

                res_json = response.json()
        except httpx.RequestError as e:
            raise RuntimeError(f"NETWORK_ERROR: Failed to connect to {self.provider_name} API: {str(e)}")

        try:
            choices = res_json.get("choices", [])
            if not choices:
                raise ValueError(f"LLM_EMPTY_RESPONSE: No choices returned by {self.provider_name}.")

            raw_text = choices[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            raise ValueError(f"LLM_INVALID_RESPONSE: Could not extract message from response: {str(e)}")

        cleaned_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
        cleaned_text = re.sub(r"\s*```$", "", cleaned_text, flags=re.MULTILINE).strip()

        try:
            parsed = json.loads(cleaned_text)
            if not isinstance(parsed, dict):
                raise ValueError("LLM_INVALID_RESPONSE: Response JSON must be an object.")
            return parsed
        except json.JSONDecodeError as jde:
            raise ValueError(f"LLM_INVALID_RESPONSE: Output is not valid JSON: {str(jde)}")
