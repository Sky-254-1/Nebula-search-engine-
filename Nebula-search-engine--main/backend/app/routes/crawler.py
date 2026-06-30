"""Crawler API routes for managing crawl jobs and viewing crawled pages."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.database.engine import DatabaseConnection
from app.models.schemas import (
    CrawlJobListResponse,
    CrawlJobResponse,
    CrawlStartRequest,
    CrawledPageListResponse,
    CrawledPageResponse,
)
from app.services.auth import get_current_user, require_admin
from app.crawler.scheduler import CrawlJob, JobStatus, crawl_scheduler

logger = logging.getLogger("nebula.routes.crawler")

router = APIRouter(prefix="/api/v1/crawler", tags=["Crawler"])


def _job_to_response(job: CrawlJob) -> CrawlJobResponse:
    return CrawlJobResponse(
        id=job.id,
        url=job.url,
        status=job.status.value,
        depth=job.depth,
        max_pages=job.max_pages,
        pages_crawled=job.pages_crawled,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        created_at=job.created_at,
    )


@router.post("/start", response_model=CrawlJobResponse, dependencies=[Depends(require_admin)])
async def start_crawl(
    body: CrawlStartRequest,
    email: str = Depends(get_current_user),
):
    job_id = await crawl_scheduler.create_job(
        url=body.url,
        max_pages=body.max_pages,
        depth=body.depth,
    )
    job = crawl_scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=500, detail="Failed to create crawl job")
    return _job_to_response(job)


@router.get("/jobs", response_model=CrawlJobListResponse, dependencies=[Depends(require_admin)])
async def list_crawl_jobs(
    status: str | None = Query(None, description="Filter by status"),
    email: str = Depends(get_current_user),
):
    jobs = crawl_scheduler.list_jobs(status=status)
    return CrawlJobListResponse(jobs=[_job_to_response(j) for j in jobs])


@router.get("/jobs/{job_id}", response_model=CrawlJobResponse, dependencies=[Depends(require_admin)])
async def get_crawl_job(
    job_id: str,
    email: str = Depends(get_current_user),
):
    job = crawl_scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Crawl job not found")
    return _job_to_response(job)


@router.post("/jobs/{job_id}/stop", response_model=CrawlJobResponse, dependencies=[Depends(require_admin)])
async def stop_crawl_job(
    job_id: str,
    email: str = Depends(get_current_user),
):
    job = crawl_scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Crawl job not found")
    success = await crawl_scheduler.stop_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be stopped or already finished")
    return _job_to_response(job)


@router.get("/pages", response_model=CrawledPageListResponse)
async def list_crawled_pages(
    job_id: str | None = Query(None, description="Filter by job ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    email: str = Depends(get_current_user),
    db: DatabaseConnection = Depends(get_db),
):
    where_clause = " WHERE cp.job_id = ?" if job_id else ""
    params = (job_id, limit, offset) if job_id else (limit, offset)
    rows = await db.fetchall(
        "SELECT cp.id, cp.job_id, cp.url, cp.title, cp.content, cp.extracted_at "
        f"FROM crawled_pages cp{where_clause} ORDER BY cp.extracted_at DESC LIMIT ? OFFSET ?",
        params,
    )
    count_where = " WHERE job_id = ?" if job_id else ""
    count_params = (job_id,) if job_id else ()
    count_row = await db.fetchone(
        f"SELECT COUNT(*) as total FROM crawled_pages{count_where}",
        count_params,
    )
    total = count_row["total"] if count_row else 0

    pages = []
    for row in rows:
        d = dict(row) if isinstance(row, dict) else dict(row)
        excerpt = (d.get("content") or "")[:200] if d.get("content") else None
        pages.append(
            CrawledPageResponse(
                id=d["id"],
                job_id=d["job_id"],
                url=d["url"],
                title=d.get("title"),
                excerpt=excerpt,
                extracted_at=d.get("extracted_at", ""),
            )
        )

    return CrawledPageListResponse(pages=pages, total=total)
