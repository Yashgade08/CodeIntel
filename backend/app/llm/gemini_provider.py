"""
Google Gemini API LLM Provider
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.llm.base import LLMProvider


class GeminiLLMProvider(LLMProvider):
    """
    Google Gemini 2.0 / 1.5 Provider using direct REST API via HTTPX.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        api_base: str = "https://generativelanguage.googleapis.com/v1beta",
    ):
        self.api_key = (api_key or "").strip()
        self.model = model
        self.api_base = api_base.rstrip("/")

    def generate_analysis(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError(
                "LLM_API_KEY_MISSING: Gemini API key is not configured. Set GEMINI_API_KEY in backend/.env"
            )

        url = f"{self.api_base}/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=payload)
                if response.status_code != 200:
                    err_text = response.text
                    raise RuntimeError(f"Gemini API returned HTTP {response.status_code}: {err_text}")

                res_json = response.json()
        except httpx.RequestError as e:
            raise RuntimeError(f"NETWORK_ERROR: Failed to connect to Gemini API: {str(e)}")

        # Extract text candidate
        try:
            candidates = res_json.get("candidates", [])
            if not candidates:
                raise ValueError("LLM_EMPTY_RESPONSE: No candidates returned by Gemini.")

            content_parts = candidates[0].get("content", {}).get("parts", [])
            raw_text = content_parts[0].get("text", "").strip()
        except Exception as e:
            raise ValueError(f"LLM_INVALID_RESPONSE: Could not extract content from Gemini response: {str(e)}")

        # Clean JSON markdown blocks if present
        cleaned_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
        cleaned_text = re.sub(r"\s*```$", "", cleaned_text, flags=re.MULTILINE).strip()

        try:
            parsed = json.loads(cleaned_text)
            if not isinstance(parsed, dict):
                raise ValueError("LLM_INVALID_RESPONSE: Response JSON must be an object.")
            return parsed
        except json.JSONDecodeError as jde:
            raise ValueError(f"LLM_INVALID_RESPONSE: Model output is not valid JSON: {str(jde)}")
