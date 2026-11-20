"""AI model client — registry pattern, easy to add / switch models.

Supported models:
    gemini   — Google Gemini (vision)
    deepseek — DeepSeek (vision via OpenAI-compatible API)

Usage:
    from services.ai_client import AIClient
    client = AIClient.get("deepseek", api_key="...", model="deepseek-chat")
    result = client.chat_with_image(image_bytes, text, system_prompt)

Add a new model:
    @AIClient.register("new_model")
    class NewModelClient(AIClient):
        def chat_with_image(self, image_bytes, text, system_prompt):
            ...
"""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from typing import ClassVar


class AIClient(ABC):
    """Abstract base for AI model clients."""

    _registry: ClassVar[dict[str, type[AIClient]]] = {}

    # ── registry ────────────────────────────────────────────────────

    @classmethod
    def register(cls, name: str):
        """Decorator: register a client implementation under a name."""

        def decorator(subclass: type[AIClient]) -> type[AIClient]:
            cls._registry[name] = subclass
            return subclass

        return decorator

    @classmethod
    def get(cls, name: str, api_key: str, model: str = "") -> AIClient:
        """Factory: get a client instance by registered name."""
        if name not in cls._registry:
            raise ValueError(
                f"Unknown model '{name}'. Available: {list(cls._registry)}"
            )
        return cls._registry[name](api_key, model)

    @classmethod
    def available(cls) -> list[str]:
        """List all registered model names."""
        return list(cls._registry)

    # ── interface ───────────────────────────────────────────────────

    def __init__(self, api_key: str, model: str = ""):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def chat_with_image(
        self, image_bytes: bytes, text: str, system_prompt: str
    ) -> str:
        """Send image + text, return model response."""
        ...

    @abstractmethod
    def chat_with_text(
        self, text: str, system_prompt: str
    ) -> str:
        """Send text only, return model response."""
        ...


# ══════════════════════════════════════════════════════════════════════
#  Gemini
# ══════════════════════════════════════════════════════════════════════

@AIClient.register("gemini")
class GeminiClient(AIClient):
    """Google Gemini vision client."""

    def __init__(self, api_key: str, model: str = ""):
        super().__init__(api_key, model or "gemini-2.5-flash")
        from google import genai
        from google.genai import types as gtypes

        self._genai = genai
        self._gtypes = gtypes
        self._client = genai.Client(api_key=api_key)

    def chat_with_image(
        self, image_bytes: bytes, text: str, system_prompt: str
    ) -> str:
        chat = self._client.chats.create(
            model=self.model,
            config={"system_instruction": system_prompt},
        )
        image_part = self._gtypes.Part.from_bytes(
            data=image_bytes, mime_type="image/jpeg"
        )
        response = chat.send_message([text, image_part])
        return response.text.strip()

    def chat_with_text(self, text: str, system_prompt: str) -> str:
        chat = self._client.chats.create(
            model=self.model,
            config={"system_instruction": system_prompt},
        )
        response = chat.send_message(text)
        return response.text.strip()


# ══════════════════════════════════════════════════════════════════════
#  DeepSeek
# ══════════════════════════════════════════════════════════════════════

@AIClient.register("deepseek")
class DeepSeekClient(AIClient):
    """DeepSeek vision client (OpenAI-compatible API).

    Model: deepseek-chat (supports vision via image_url)
    Endpoint: https://api.deepseek.com/v1
    """

    BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, api_key: str, model: str = ""):
        super().__init__(api_key, model or "deepseek-chat")
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=self.BASE_URL)

    def chat_with_image(
        self, image_bytes: bytes, text: str, system_prompt: str
    ) -> str:
        # Encode image as base64 data URL
        b64 = base64.b64encode(image_bytes).decode()
        image_url = f"data:image/jpeg;base64,{b64}"

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    },
                ],
            },
        ]

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()

    def chat_with_text(self, text: str, system_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()
