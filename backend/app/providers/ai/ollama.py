"""Ollama local model provider."""

from typing import Optional

import httpx

from app.config import get_settings
from app.providers.ai.base import AIProvider

settings = get_settings()
DEFAULT_SYSTEM = "You are Nebula, a helpful search assistant."


class OllamaProvider(AIProvider):
    name = "ollama"

    async def complete(self, prompt: str, system: Optional[str] = None) -> Optional[str]:
        url = f"{settings.ollama_url.rstrip('/')}/api/chat"
        payload = {
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": system or DEFAULT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
            message = data.get("message", {})
            content = message.get("content", "").strip()
            return content or None
        except Exception:
            return None
