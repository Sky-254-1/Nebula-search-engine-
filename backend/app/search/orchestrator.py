"""Search orchestration pipeline."""

import asyncio
import hashlib
import logging
from typing import Optional

from app.config import get_settings
from app.search.query_understanding.pipeline import get_query_preprocessor
from app.services.cache import cache_service
from app.services.search import ALLOWED_BACKENDS, run_web_search, sanitize_query

logger = logging.getLogger("nebula.search.orchestrator")
settings = get_settings()

# Initialize query preprocessor
_query_preprocessor = get_query_preprocessor()


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
        key = url or hashlib.md5(item.get("title", "").encode(), usedforsecurity=False).hexdigest()
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
    user_id: Optional[int] = None,
) -> dict:
    """
    Query → preprocess → expand → parallel provider search → rank → dedupe → paginate.
    
    Args:
        query: Search query
        backends: List of search backends to use
        page: Page number (1-indexed)
        page_size: Number of results per page
        use_cache: Whether to use caching
        user_id: Optional user ID for personalization
        
    Returns:
        Search results with metadata
    """
    # Step 1: Query preprocessing with NLP pipeline
    try:
        processed_query = await _query_preprocessor.process(query)
        search_query = processed_query.expanded_query
        query_metadata = {
            "intent": processed_query.intent.value,
            "language": processed_query.language,
            "entities": processed_query.entities,
            "synonyms": processed_query.synonyms,
            "original_query": processed_query.original,
            "normalized_query": processed_query.normalized
        }
        logger.debug(f"Query preprocessed: {query} → {search_query}")
    except Exception as e:
        logger.warning(f"Query preprocessing failed, using original query: {e}")
        search_query = query
        query_metadata = {
            "intent": "informational",
            "language": "en",
            "entities": [],
            "synonyms": [],
            "original_query": query,
            "normalized_query": query
        }

    # Step 2: Sanitize query
    safe_query = sanitize_query(search_query)
    if not safe_query:
        return {
            "query": query,
            "results": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "metadata": query_metadata
        }

    # Step 3: Select backends
    selected = backends or ["wikipedia"]
    selected = [b for b in selected if b in ALLOWED_BACKENDS] or ["wikipedia"]

    # Step 4: Check cache (include user_id for personalized caching)
    cache_key = f"search:{safe_query}:{','.join(selected)}:{page}:{page_size}:{user_id or 'anon'}"
    if use_cache:
        cached = await cache_service.get(cache_key)
        if cached:
            cached["cached"] = True
            cached["metadata"] = query_metadata
            return cached

    # Step 5: Fetch results from backends
    async def fetch_backend(backend: str) -> list[dict]:
        try:
            return await run_web_search(safe_query, backend, 1, page_size)
        except Exception as exc:
            logger.debug("Backend %s failed: %s", backend, exc)
            return []

    gathered = await asyncio.gather(*(fetch_backend(b) for b in selected))
    merged = _dedupe_results([item for batch in gathered for item in batch])
    
    # Step 6: Rank results with enhanced ranking
    ranked = _rank_results(merged, safe_query)
    
    # Step 7: Apply filters from query understanding
    filters = processed_query.filters if 'processed_query' in dir() else {}
    if filters:
        ranked = _apply_filters(ranked, filters)
    
    # Step 8: Paginate
    start = (page - 1) * page_size
    page_results = ranked[start : start + page_size]

    # Step 9: Build response
    payload = {
        "query": safe_query,
        "original_query": query,
        "expanded_queries": expand_query(safe_query),
        "backends": selected,
        "results": page_results,
        "total": len(ranked),
        "page": page,
        "page_size": page_size,
        "cached": False,
        "metadata": query_metadata
    }
    
    # Step 10: Cache results
    await cache_service.set(cache_key, payload)
    
    # Step 11: Track search analytics (async, don't block)
    if user_id:
        asyncio.create_task(_track_search_analytics(
            user_id=user_id,
            query=query,
            search_type="hybrid",
            result_count=len(page_results)
        ))
    
    return payload


def _apply_filters(results: list[dict], filters: dict) -> list[dict]:
    """
    Apply filters to search results.
    
    Args:
        results: Search results
        filters: Filters to apply
        
    Returns:
        Filtered results
    """
    if not filters:
        return results
    
    filtered = results
    
    # Filter by file type
    if "file_type" in filters:
        file_type = filters["file_type"].lower()
        filtered = [r for r in filtered if file_type in r.get("url", "").lower()]
    
    # Filter by location
    if "location" in filters:
        location = filters["location"].lower()
        filtered = [r for r in filtered if location in r.get("snippet", "").lower()]
    
    # Filter by date range (if available in metadata)
    if "date_range" in filters:
        # Implementation depends on date metadata in results
        pass
    
    return filtered


async def _track_search_analytics(
    user_id: int,
    query: str,
    search_type: str,
    result_count: int
):
    """
    Track search analytics asynchronously.
    
    Args:
        user_id: User ID
        query: Search query
        search_type: Type of search
        result_count: Number of results
    """
    try:
        from app.database import get_db
        from app.database.repositories.analytics import AnalyticsRepository
        
        db = await get_db()
        try:
            analytics_repo = AnalyticsRepository(db)
            await analytics_repo.track_search(
                user_id=user_id,
                query=query,
                search_type=search_type,
                result_count=result_count
            )
        finally:
            await db.close()
    except Exception as e:
        logger.debug(f"Failed to track search analytics: {e}")
