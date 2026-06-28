"""Search orchestration pipeline."""

import asyncio
import hashlib
import logging
from typing import Optional

from app.config import get_settings
from app.services.cache import cache_service
from app.services.search import ALLOWED_BACKENDS, run_web_search, sanitize_query

logger = logging.getLogger("nebula.search.orchestrator")
settings = get_settings()


def expand_query(query: str) -> list[str]:
    """Generate lightweight query variants for broader recall."""
    base = sanitize_query(query)
    if not base:
        return []
    variants = [base]
    words = base.split()
    if len(words) > 2:
        variants.append(" ".join(words[:3]))
    return list(dict.fromkeys(variants))


def _dedupe_results(results: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for item in results:
        url = item.get("url", "").strip().lower()
        key = url or hashlib.md5(item.get("title", "").encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _rank_results(results: list[dict], query: str) -> list[dict]:
    # OPTIMIZATION: pre-calculating unique query terms and using a manual loop
    # instead of a generator within sum() reduces overhead for large result sets.
    # We use a set for query terms to preserve exact original ranking behavior.
    query_terms = {term.lower() for term in query.split() if term}
    if not query_terms:
        return list(results)

    scored_results = []
    for item in results:
        text = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
        s = 0.0
        for term in query_terms:
            if term in text:
                s += 1.0
        scored_results.append((s, item))

    # Python's sort is stable, but to be safe and efficient we sort by score.
    scored_results.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored_results]


async def orchestrate_search(
    query: str,
    backends: Optional[list[str]] = None,
    page: int = 1,
    page_size: int = 10,
    use_cache: bool = True,
) -> dict:
    """
    Query → expand → parallel provider search → rank → dedupe → paginate.
    """
    safe_query = sanitize_query(query)
    if not safe_query:
        return {"query": query, "results": [], "total": 0, "page": page, "page_size": page_size}

    selected = backends or ["wikipedia"]
    selected = [b for b in selected if b in ALLOWED_BACKENDS] or ["wikipedia"]

    cache_key = f"search:{safe_query}:{','.join(selected)}:{page}:{page_size}"
    if use_cache:
        cached = await cache_service.get(cache_key)
        if cached:
            cached["cached"] = True
            return cached

    async def fetch_backend(backend: str) -> list[dict]:
        try:
            return await run_web_search(safe_query, backend, 1, page_size)
        except Exception as exc:
            logger.debug("Backend %s failed: %s", backend, exc)
            return []

    gathered = await asyncio.gather(*(fetch_backend(b) for b in selected))
    merged = _dedupe_results([item for batch in gathered for item in batch])
    ranked = _rank_results(merged, safe_query)

    start = (page - 1) * page_size
    page_results = ranked[start : start + page_size]

    payload = {
        "query": safe_query,
        "expanded_queries": expand_query(safe_query),
        "backends": selected,
        "results": page_results,
        "total": len(ranked),
        "page": page,
        "page_size": page_size,
        "cached": False,
    }
    await cache_service.set(cache_key, payload)
    return payload
