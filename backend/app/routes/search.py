"""Web search routes."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.middleware.rate_limit import rate_limit
from app.models.schemas import SearchResult
from app.services.auth import get_current_user
from app.services.search import ALLOWED_BACKENDS, run_web_search

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


@router.get("/web", response_model=list[SearchResult], dependencies=[Depends(rate_limit)])
async def web_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    backend: str = Query("wikipedia", description="Search backend: wikipedia, brave, serpapi"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Results per page"),
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    if backend not in ALLOWED_BACKENDS:
        raise HTTPException(status_code=400, detail=f"Unknown backend: {backend}")

    cursor = await db.execute("SELECT id FROM users WHERE email = ?", (email,))
    user = await cursor.fetchone()
    user_id = user["id"] if user else None

    try:
        results = await run_web_search(q, backend, page, page_size)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Search backend error: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Search backend unreachable: {str(exc)}",
        ) from exc

    await db.execute(
        "INSERT INTO search_logs (user_id, query, backend, results_count) VALUES (?, ?, ?, ?)",
        (user_id, q, backend, len(results)),
    )
    await db.commit()
    return results
