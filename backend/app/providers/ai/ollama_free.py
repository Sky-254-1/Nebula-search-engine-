"""Ollama provider using ollamafreeapi library as fallback."""

import logging
from collections.abc import AsyncIterator
from typing import Optional

from app.config import get_settings
from app.providers.ai.base import AIProvider

try:
    from ollamafreeapi import OllamaFreeAPI

    _ollama_free_available = True
except ImportError:
    _ollama_free_available = False

logger = logging.getLogger("nebula.ai.ollama_free")
settings = get_settings()


class OllamaFreeProvider(AIProvider):
    """Ollama provider with OllamaFreeAPI fallback support."""

    name = "ollama_free"

    def __init__(self) -> None:
        self._client: Optional[object] = None
        if _ollama_free_available:
            try:
                self._client = OllamaFreeAPI()
            except Exception as exc:
                logger.warning("Failed to initialize OllamaFreeAPI client: %s", exc)

    async def complete(self, prompt: str, system: Optional[str] = None) -> Optional[str]:
        if not self._client:
            return None
        try:
            response = self._client.chat(
                model_name=settings.ollama_model,
                prompt=prompt,
                system=system or "You are Nebula, a helpful search assistant.",
                temperature=0.7,
            )
            return str(response).strip() or None
        except Exception as exc:
            logger.debug("OllamaFreeAPI provider failed: %s", exc)
            return None

    async def stream(self, prompt: str, system: Optional[str] = None) -> AsyncIterator[str]:
        if not self._client:
            return
        try:
            for chunk in self._client.stream_chat(
                model_name=settings.ollama_model,
                prompt=prompt,
                system=system or "You are Nebula, a helpful search assistant.",
                temperature=0.7,
            ):
                yield str(chunk)
        except Exception as exc:
            logger.debug("OllamaFreeAPI stream failed: %s", exc)
            answer = await self.complete(prompt, system)
            if answer:
                yield answer