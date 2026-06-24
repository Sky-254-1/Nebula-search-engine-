"""OpenAI-compatible provider."""

from typing import Optional

import httpx

from app.config import get_settings
from app.providers.ai.base import AIProvider

settings = get_settings()
DEFAULT_SYSTEM = (
    "You are Nebula, a helpful and concise search assistant. "
    "Provide clear, accurate, and brief answers."
)


class OpenAIProvider(AIProvider):
    name = "openai"

    async def complete(self, prompt: str, system: Optional[str] = None) -> Optional[str]:
        if not settings.openai_api_key:
            return None
        url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": system or DEFAULT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 500,
            "temperature": 0.7,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
