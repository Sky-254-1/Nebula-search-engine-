from fastapi import APIRouter, Depends, Query
from typing import List
from auth.dependencies import get_current_user
from search.service import SearchService, SearchResult

router = APIRouter()

@router.get("/web", response_model=List[SearchResult])
async def web_search(
    q: str = Query(..., min_length=1),
    page: int = 1,
    page_size: int = 10,
    backend: str = "brave",
    user=Depends(get_current_user)
):
    service = SearchService(backend=backend)
    return await service.search(q, page, page_size)