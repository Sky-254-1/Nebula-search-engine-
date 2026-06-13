import httpx
from config import BRAVE_API_KEY
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    thumbnail: Optional[str] = None
    source: str = "brave"

class SearchService:
    def __init__(self, backend: str = "brave"):
        self.backend = backend

    async def search(self, query: str, page: int = 1, page_size: int = 10) -> List[SearchResult]:
        if self.backend == "brave":
            return await self._brave(query, page, page_size)
        elif self.backend == "wikipedia":
            return await self._wikipedia(query, page, page_size)
        else:
            raise ValueError("Unsupported backend")

    async def _brave(self, query, page, page_size):
        params = {
            "q": query,
            "count": min(page_size, 20),
            "offset": (page - 1) * page_size
        }
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_API_KEY
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.search.brave.com/res/v1/web/search", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("web", {}).get("results", []):
                results.append(SearchResult(
                    title=item["title"],
                    url=item["url"],
                    snippet=item.get("description", ""),
                    thumbnail=item.get("thumbnail", {}).get("src"),
                    source="brave"
                ))
            return results

    async def _wikipedia(self, query, page, page_size):
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": page_size,
            "sroffset": (page - 1) * page_size
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://en.wikipedia.org/w/api.php", params=params)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for page_data in data.get("query", {}).get("search", []):
                results.append(SearchResult(
                    title=page_data["title"],
                    url=f"https://en.wikipedia.org/wiki/{page_data['title'].replace(' ', '_')}",
                    snippet=page_data.get("snippet", "").replace('<span class="searchmatch">', '').replace('</span>', ''),
                    source="wikipedia"
                ))
            return results