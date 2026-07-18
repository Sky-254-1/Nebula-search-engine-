"""Embedding generation — local hash vectors and optional OpenAI."""

import hashlib
import json
import math
from pathlib import Path

import httpx

from app.config import get_settings

DEFAULT_DIMENSIONS = 256


def _hash_embed(text: str, dimensions: int = DEFAULT_DIMENSIONS) -> list[float]:
    """Deterministic offline embedding via hashed token projection."""
    vec = [0.0] * dimensions
    tokens = text.lower().split()
    if not tokens:
        return vec
    for token in tokens:
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        idx = h % dimensions
        sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


async def embed_text(text: str, model: str | None = None) -> tuple[list[float], str, int]:
    settings = get_settings()

    # Try sentence-transformers first (local, fast, high quality)
    if model != "local-hash":
        try:
            from vector.semantic import embed_semantic
            return await embed_semantic(text)
        except Exception:
            pass

    # Try OpenAI as fallback
    if settings.openai_api_key and model != "local-hash":
        try:
            return await _openai_embed(text, settings)
        except Exception:
            pass

    # Deterministic hash embedding as last resort
    vec = _hash_embed(text)
    return vec, "local-hash", len(vec)


async def _openai_embed(text: str, settings) -> tuple[list[float], str, int]:
    url = f"{settings.openai_base_url.rstrip('/')}/embeddings"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    payload = {"input": text, "model": "text-embedding-3-small"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()["data"][0]["embedding"]
        return data, "text-embedding-3-small", len(data)


def save_vector(path: Path, vector: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(vector), encoding="utf-8")


def load_vector(path: Path | str) -> list[float]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))
