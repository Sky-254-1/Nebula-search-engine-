"""Unified search API endpoint combining web, vector, hybrid, and AI search modes."""

import asyncio
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

from app.database import get_db
from app.database.repositories.notification import NotificationRepository
from app.database.repositories.saved_search import SavedSearchRepository
from app.database.repositories.search import SearchRepository
from app.database.repositories.user import UserRepository
from app.middleware.rate_limit import rate_limit
from app.services.auth import get_current_user
from app.services.search import run_web_search
from app.search.intelligence import (
    autocomplete_engine,
    query_suggestion_engine,
    spell_corrector,
    search_analytics,
)
from app.search.orchestrator import orchestrate_search
from app.search.ranking import hybrid_ranker
from vector.pipeline import hybrid_search
from app.services.ai import get_ai_answer, synthesize_snippets

logger = logging.getLogger("nebula.search.unified")

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


# ============================================
# Models
# ============================================

class SearchMode(str, Enum):
    web = "web"
    vector = "vector"
    hybrid = "hybrid"
    ai = "ai"


class SearchFilters(BaseModel):
    date_range: Optional[Dict[str, str]] = None
    document_type: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    mode: SearchMode = Field(default=SearchMode.hybrid, description="Search mode")
    filters: Optional[SearchFilters] = None
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=50, description="Results per page")
    sort: str = Field(default="relevance", description="Sort field")
    include_ai_answer: bool = Field(default=True, description="Include AI-generated answer")
    include_suggestions: bool = Field(default=True, description="Include search suggestions")
    spell_check: bool = Field(default=True, description="Auto spell correction")
    include_highlights: bool = Field(default=True, description="Include result highlights")
    facets: Optional[List[str]] = Field(default=None, description="Facet fields to return")


class SearchResult(BaseModel):
    id: int
    title: str
    snippet: str
    url: str
    source: str
    score: float
    document_id: Optional[int] = None
    highlights: Optional[List[Dict[str, Any]]] = None


class AIAnswer(BaseModel):
    answer: str
    provider: str
    citations: Optional[List[Dict[str, Any]]] = None
    tokens_used: Optional[int] = None
    response_time_ms: Optional[float] = None


class FacetCount(BaseModel):
    field: str
    value: str
    count: int


class SearchResponse(BaseModel):
    query: str
    mode: str
    results: List[SearchResult]
    ai_answer: Optional[AIAnswer] = None
    suggestions: Optional[List[str]] = None
    facets: Optional[List[FacetCount]] = None
    total: int
    response_time_ms: float


# ============================================
# Helpers
# ============================================

async def _user_id(db, email: str) -> int:
    users = UserRepository(db)
    user_id = await users.get_id_by_email(email)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
    return user_id


def _highlight(text: str, query: str, max_length: int = 200) -> tuple[str, List[Dict[str, Any]]]:
    """Simple keyword highlighting."""
    query_terms = query.lower().split()
    highlights = []
    lower = text.lower()
    for term in query_terms:
        idx = lower.find(term)
        if idx >= 0:
            highlights.append({"text": term, "start": idx, "end": idx + len(term)})
    snippet = text[:max_length] + "..." if len(text) > max_length else text
    return snippet, highlights


def _compute_facets(results: List[SearchResult], facet_fields: List[str]) -> List[FacetCount]:
    """Compute facet counts from results."""
    facets = []
    for field in facet_fields:
        counts: Dict[str, int] = {}
        for r in results:
            if field == "source":
                val = r.source
            elif field == "document_type":
                val = r.url.split(".")[-1] if r.url else "unknown"
            else:
                continue
            counts[val] = counts.get(val, 0) + 1
        for val, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True):
            facets.append(FacetCount(field=field, value=val, count=cnt))
    return facets


async def _safe_ai_synthesis(query: str, results: List[SearchResult]):
    try:
        snippets = [r.snippet for r in results[:5] if r.snippet]
        if not snippets:
            return None
        synth = await synthesize_snippets(query, snippets)
        if synth and synth.synthesis:
            return AIAnswer(answer=synth.synthesis, provider="openai", citations=[])
    except Exception:
        pass
    return None


# ============================================
# Endpoints
# ============================================

@router.post("/", response_model=SearchResponse, dependencies=[Depends(rate_limit)])
async def unified_search(
    body: SearchRequest,
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Unified search endpoint supporting web, vector, hybrid, and AI search modes.

    Consolidates:
    - GET /api/v1/search/web
    - GET /api/v1/search/orchestrate
    - POST /api/v1/vector/search
    - POST /api/v1/ai/ask

    into a single, consistent API.
    """
    start_time = time.time()
    user_id = await _user_id(db, email)

    # Spell correction
    corrected_query = body.query
    if body.spell_check:
        corrected_query, was_corrected = await spell_corrector.correct_query(body.query)
        if was_corrected:
            logger.info("Query corrected: '%s' -> '%s'", body.query, corrected_query)

    query = corrected_query
    results: List[SearchResult] = []
    ai_answer: Optional[AIAnswer] = None
    suggestions: Optional[List[str]] = None
    facets_out: Optional[List[FacetCount]] = None

    try:
        if body.mode == SearchMode.web:
            web_results = await run_web_search(
                query, backend="wikipedia", page=body.page, page_size=body.limit
            )
            results = [
                SearchResult(
                    id=i,
                    title=r.get("title", ""),
                    snippet=r.get("snippet", ""),
                    url=r.get("url", ""),
                    source="web",
                    score=r.get("score", 0.0),
                    highlights=[{"text": t, "start": 0, "end": len(t)}
                               for t in query.split() if t][:5]
                    if body.include_highlights else [],
                )
                for i, r in enumerate(web_results, 1)
            ]

        elif body.mode == SearchMode.vector:
            vector_results = await hybrid_search(db, user_id, query, top_k=body.limit)
            results = [
                SearchResult(
                    id=r.get("chunk_id", i),
                    title=r.get("filename", ""),
                    snippet=r.get("content", "")[:200],
                    url=f"/documents/{r.get('document_id')}",
                    source="vector",
                    score=r.get("score", 0.0),
                    document_id=r.get("document_id"),
                    highlights=[],
                )
                for i, r in enumerate(vector_results, 1)
            ]

        elif body.mode == SearchMode.hybrid:
            web_results, vector_results = await asyncio.gather(
                run_web_search(query, backend="wikipedia", page=1, page_size=body.limit // 2),
                hybrid_search(db, user_id, query, top_k=body.limit // 2),
            )
            for i, r in enumerate(web_results, 1):
                results.append(SearchResult(
                    id=i, title=r.get("title", ""), snippet=r.get("snippet", ""),
                    url=r.get("url", ""), source="web", score=r.get("score", 0.0),
                    highlights=[],
                ))
            for i, r in enumerate(vector_results, len(results) + 1):
                results.append(SearchResult(
                    id=i, title=r.get("filename", ""),
                    snippet=r.get("content", "")[:200],
                    url=f"/documents/{r.get('document_id')}",
                    source="vector", score=r.get("score", 0.0),
                    document_id=r.get("document_id"), highlights=[],
                ))
            results.sort(key=lambda x: x.score, reverse=True)
            results = results[:body.limit]

        elif body.mode == SearchMode.ai:
            answer, provider = await get_ai_answer(query)
            if answer:
                ai_answer = AIAnswer(answer=answer, provider=provider, citations=[])

        # Apply advanced ranking (BM25 + ML + diversity)
        if results:
            try:
                ranked = await hybrid_ranker.rank(
                    query=query, results=[r.dict() for r in results],
                    user_profile=None, enable_diversity=True,
                )
                results = [SearchResult(**r) for r in ranked[:body.limit]]
            except Exception as exc:
                logger.debug("Advanced ranking failed: %s", exc)

        # Facets
        if body.facets and results:
            facets_out = _compute_facets(results, body.facets)

        # AI answer
        if body.include_ai_answer and body.mode != SearchMode.ai and results:
            ai_answer = await _safe_ai_synthesis(query, results)

        # Suggestions
        if body.include_suggestions:
            try:
                suggestions = [
                    s["text"] for s in
                    (await query_suggestion_engine.get_suggestions(query, user_id, limit=5))
                ]
            except Exception:
                suggestions = []

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(exc)}")

    response_time_ms = (time.time() - start_time) * 1000

    search_repo = SearchRepository(db)
    await search_repo.log_search(user_id, query, body.mode.value, len(results))

    return SearchResponse(
        query=query,
        mode=body.mode.value,
        results=results,
        ai_answer=ai_answer,
        suggestions=suggestions,
        facets=facets_out,
        total=len(results),
        response_time_ms=round(response_time_ms, 2),
    )


@router.get("/suggestions")
async def get_suggestions(
    q: str = Query(..., min_length=1, max_length=100, description="Query prefix"),
    limit: int = Query(5, ge=1, le=10, description="Number of suggestions"),
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get search suggestions based on query prefix."""
    user_id = await _user_id(db, email)
    suggestions = await query_suggestion_engine.get_suggestions(q, user_id, limit=limit)
    return {
        "success": True,
        "data": {
            "query": q,
            "suggestions": [
                {"text": s.suggestion, "score": s.score, "source": s.source}
                for s in suggestions
            ],
        },
    }


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=1, max_length=100, description="Query prefix"),
    limit: int = Query(10, ge=1, le=20, description="Number of suggestions"),
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get autocomplete suggestions for search query."""
    await _user_id(db, email)
    suggestions = await autocomplete_engine.suggest(q, limit=limit)
    return {
        "success": True,
        "data": {
            "query": q,
            "suggestions": [s.suggestion for s in suggestions],
        },
    }


@router.get("/history")
async def search_history(
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get user's search history."""
    user_id = await _user_id(db, email)
    search_repo = SearchRepository(db)
    history = await search_repo.recent_for_user(user_id, limit)
    return {"success": True, "data": {"history": history}}


@router.delete("/history")
async def clear_search_history(
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Clear user's search history."""
    user_id = await _user_id(db, email)
    await db.execute(
        "UPDATE search_logs SET is_deleted = TRUE, deleted_at = datetime('now') "
        "WHERE user_id = ?",
        (user_id,),
    )
    await db.commit()
    return {"success": True, "data": {"message": "Search history cleared"}}


@router.post("/save")
async def save_search(
    query: str = Query(..., min_length=1, max_length=500),
    mode: str = Query("hybrid"),
    filters: Optional[str] = Query(None),
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Save a search query for later use."""
    import json
    user_id = await _user_id(db, email)
    saved_repo = SavedSearchRepository(db)
    filter_dict = json.loads(filters) if filters else None
    if mode not in ("web", "vector", "hybrid", "ai"):
        mode = "hybrid"
    saved_id = await saved_repo.create(user_id, query, mode, filter_dict)
    return {
        "success": True,
        "data": {"id": saved_id, "message": "Search saved", "query": query, "mode": mode},
    }


@router.get("/saved")
async def list_saved_searches(
    email: str = Depends(get_current_user),
    db=Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
):
    """List user's saved searches."""
    user_id = await _user_id(db, email)
    saved_repo = SavedSearchRepository(db)
    saved = await saved_repo.list_for_user(user_id, limit=limit)
    return {"success": True, "data": {"saved": saved}}


@router.delete("/saved/{search_id}")
async def delete_saved_search(
    search_id: int,
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete a saved search."""
    user_id = await _user_id(db, email)
    saved_repo = SavedSearchRepository(db)
    row = await saved_repo.get_by_id(search_id, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Saved search not found")
    await saved_repo.delete(search_id, user_id)
    return {"success": True, "data": {"message": "Saved search deleted"}}
