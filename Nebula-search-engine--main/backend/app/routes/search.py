"""Web search routes."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import get_db
from app.database.repositories.search import SearchRepository
from app.database.repositories.search_click import SearchClickRepository
from app.database.repositories.user import UserRepository
from app.indexer.ranker import ranker
from app.middleware.rate_limit import rate_limit
from app.models.schemas import OrchestratedSearchResponse, SearchResult
from app.search.orchestrator import orchestrate_search
from app.services.auth import get_current_user
from app.services.search import ALLOWED_BACKENDS, run_web_search


class ClickTrackingRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    result_url: str = Field(..., min_length=1, max_length=2000)
    result_title: str | None = Field(default=None, max_length=500)
    result_position: int | None = Field(default=None, ge=1)
    backend: str | None = Field(default=None, max_length=50)
    search_log_id: int | None = None

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

    users = UserRepository(db)
    user_id = await users.get_id_by_email(email)

    try:
        results = await run_web_search(q, backend, page, page_size)
    except HTTPException:
        raise
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

    search_repo = SearchRepository(db)
    await search_repo.log_search(user_id, q, backend, len(results))
    return results


@router.get(
    "/orchestrate",
    response_model=OrchestratedSearchResponse,
    dependencies=[Depends(rate_limit)],
)
async def orchestrated_search(
    q: str = Query(..., min_length=1, max_length=500),
    backends: str = Query("wikipedia", description="Comma-separated backends"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    backend_list = [b.strip() for b in backends.split(",") if b.strip()]
    try:
        payload = await orchestrate_search(q, backend_list, page, page_size)
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Search backend error: {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Search backend unreachable: {str(exc)}") from exc

    users = UserRepository(db)
    user_id = await users.get_id_by_email(email)
    search_repo = SearchRepository(db)
    await search_repo.log_search(user_id, q, ",".join(backend_list), len(payload["results"]))
    return payload


@router.post("/click", status_code=204)
async def track_click(body: ClickTrackingRequest, email: str = Depends(get_current_user), db=Depends(get_db)):
    users = UserRepository(db)
    user_id = await users.get_id_by_email(email)
    click_repo = SearchClickRepository(db)
    await click_repo.record_click(
        user_id=user_id,
        query=body.query,
        result_url=body.result_url,
        result_title=body.result_title,
        result_position=body.result_position,
        backend=body.backend,
        search_log_id=body.search_log_id,
    )
    ranker.record_click(hash(body.result_url) & 0x7FFFFFFF)


@router.get("/history")
async def search_history(
    limit: int = Query(20, ge=1, le=100),
    email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    users = UserRepository(db)
    user_id = await users.get_id_by_email(email)
    if not user_id:
        return {"history": []}
    search_repo = SearchRepository(db)
    return {"history": await search_repo.recent_for_user(user_id, limit)}
