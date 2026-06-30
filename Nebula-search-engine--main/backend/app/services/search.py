"""Web search provider integrations."""

import re
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from app.config import get_settings

settings = get_settings()
ALLOWED_BACKENDS = frozenset({"wikipedia", "brave", "serpapi"})


def sanitize_query(query: str) -> str:
    """Strip control characters and normalize whitespace."""
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", query).strip()
    return cleaned


async def search_wikipedia(query: str, page: int, page_size: int) -> list[dict]:
    """Search Wikipedia's public API."""
    offset = (page - 1) * page_size
    encoded = quote(query)
    url = (
        "https://en.wikipedia.org/w/api.php"
        f"?action=query&list=search&srsearch={encoded}"
        f"&srlimit={page_size}&sroffset={offset}"
        "&format=json&origin=*"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("query", {}).get("search", []):
        snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
        title = item.get("title", "")
        results.append(
            {
                "title": title,
                "snippet": snippet,
                "url": f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'), safe='')}",
                "source": "wikipedia",
            }
        )
    return results


async def search_brave(query: str, page: int, page_size: int) -> list[dict]:
    """Search via Brave Search API."""
    if not settings.brave_api_key:
        raise HTTPException(status_code=400, detail="Brave API key not configured on server")
    offset = (page - 1) * page_size
    url = (
        "https://api.search.brave.com/res/v1/web/search"
        f"?q={quote(query)}&count={page_size}&offset={offset}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            url,
            headers={
                "X-Subscription-Token": settings.brave_api_key,
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return [
        {
            "title": item.get("title", ""),
            "snippet": item.get("description", ""),
            "url": item.get("url", ""),
            "source": "brave",
        }
        for item in data.get("web", {}).get("results", [])
    ]


async def search_serpapi(query: str, page: int, page_size: int) -> list[dict]:
    """Search via SerpAPI (Google results)."""
    if not settings.serpapi_key:
        raise HTTPException(status_code=400, detail="SerpAPI key not configured on server")
    start = (page - 1) * page_size
    url = (
        "https://serpapi.com/search.json"
        f"?q={quote(query)}&api_key={settings.serpapi_key}&engine=google"
        f"&start={start}&num={page_size}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    return [
        {
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "url": item.get("link", ""),
            "source": "serpapi",
        }
        for item in data.get("organic_results", [])
    ]


async def run_web_search(
    query: str,
    backend: str,
    page: int,
    page_size: int,
) -> list[dict]:
    """Dispatch search to the configured backend."""
    if backend not in ALLOWED_BACKENDS:
        raise HTTPException(status_code=400, detail=f"Unknown backend: {backend}")

    safe_query = sanitize_query(query)
    if not safe_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if backend == "wikipedia":
        return await search_wikipedia(safe_query, page, page_size)
    if backend == "brave":
        return await search_brave(safe_query, page, page_size)
    return await search_serpapi(safe_query, page, page_size)
