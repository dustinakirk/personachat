from __future__ import annotations

from typing import Optional

import google.generativeai as genai


class GeminiService:
    """Helper for creating prompts using Google Gemini."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._model: Optional[genai.GenerativeModel] = None

        if api_key:
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel("gemini-pro")

    @property
    def is_configured(self) -> bool:
        return self._model is not None

    def generate_response(self, prompt: str) -> str:
        if not self._model:
            raise RuntimeError("Gemini API key is missing. Set GEMINI_API_KEY.")

        if not prompt.strip():
            return ""

        response = self._model.generate_content(prompt)
        return response.text or "No response returned from Gemini."
