"""AI completion and synthesis services."""

import logging
from typing import Optional
from urllib.parse import quote

import httpx

from app.config import get_settings
from app.models.schemas import SynthesizeResponse

settings = get_settings()
logger = logging.getLogger("nebula.ai")

SYSTEM_PROMPT = (
    "You are Nebula, a helpful and concise search assistant. "
    "Provide clear, accurate, and brief answers. "
    "If you're unsure, say so. Do not make up facts."
)


async def ai_openai(prompt: str) -> str:
    """Get an answer from an OpenAI-compatible API."""
    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
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


async def ai_duckduckgo(prompt: str) -> Optional[str]:
    """Fallback: get an instant answer from DuckDuckGo."""
    url = f"https://api.duckduckgo.com/?q={quote(prompt)}&format=json&no_redirect=1&t=nebula"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
    return data.get("AbstractText") or data.get("Answer") or None


async def get_ai_answer(prompt: str) -> Optional[str]:
    """Try OpenAI first, then DuckDuckGo fallback."""
    answer = None
    if settings.openai_api_key:
        try:
            answer = await ai_openai(prompt)
        except httpx.HTTPStatusError as exc:
            logger.warning("OpenAI error %s — falling back to DuckDuckGo", exc.response.status_code)
        except httpx.RequestError as exc:
            logger.warning("OpenAI unreachable: %s — falling back to DuckDuckGo", exc)

    if not answer:
        try:
            answer = await ai_duckduckgo(prompt)
        except Exception as exc:
            logger.debug("DuckDuckGo fallback failed: %s", exc)
    return answer


async def synthesize_snippets(query: str, snippets: list[str]) -> SynthesizeResponse:
    """Synthesize search snippets into a summary."""
    combined = "\n".join(f"- {snippet}" for snippet in snippets[:10])

    if settings.openai_api_key:
        prompt = (
            f'The user searched for: "{query}"\n\n'
            f"Here are the top search result snippets:\n{combined}\n\n"
            "Synthesize these into a clear, concise summary paragraph (3-5 sentences). "
            "Do not add information not present in the snippets."
        )
        try:
            synthesis = await ai_openai(prompt)
            return SynthesizeResponse(synthesis=synthesis)
        except Exception as exc:
            logger.debug("OpenAI synthesis failed: %s", exc)

    transitions = [
        "According to search results, ",
        "Additionally, ",
        "Furthermore, ",
        "It is also noted that ",
        "Moreover, ",
    ]
    parts = []
    for index, snippet in enumerate(snippets[:5]):
        prefix = transitions[index] if index < len(transitions) else ""
        parts.append(f"{prefix}{snippet.strip().rstrip('.')}.")
    return SynthesizeResponse(synthesis=" ".join(parts))
