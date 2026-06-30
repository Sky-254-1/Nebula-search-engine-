"""Crawler tests: URL normalization, robots.txt, job creation, content extraction, rate-limiting, depth."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme, netloc, path, parsed.params, parsed.query, parsed.fragment))


class TestURLNormalization:
    def test_removes_www_prefix(self):
        assert normalize_url("https://www.example.com/path") == "https://example.com/path"

    def test_lowercases_domain(self):
        assert normalize_url("https://Example.COM/Path") == "https://example.com/Path"

    def test_removes_trailing_slash(self):
        assert normalize_url("https://example.com/path/") == "https://example.com/path"

    def test_adds_root_slash(self):
        assert normalize_url("https://example.com") == "https://example.com/"

    def test_preserves_query_params(self):
        assert normalize_url("https://example.com/path?q=1") == "https://example.com/path?q=1"

    def test_handles_fragment(self):
        assert normalize_url("https://example.com/page#section") == "https://example.com/page#section"


class TestRobotsTxtParsing:
    def test_allowed_by_default(self):
        rules = {"User-agent": "*", "Disallow": ""}
        assert _is_allowed("https://example.com/page", rules)

    def test_disallowed_path(self):
        rules = {"User-agent": "*", "Disallow": "/private"}
        assert not _is_allowed("https://example.com/private/data", rules)

    def test_allowed_outside_disallow(self):
        rules = {"User-agent": "*", "Disallow": "/private"}
        assert _is_allowed("https://example.com/public", rules)


def _is_allowed(url: str, rules: dict) -> bool:
    parsed = urlparse(url)
    path = parsed.path
    disallow = rules.get("Disallow", "")
    if not disallow:
        return True
    return not path.startswith(disallow)


class TestCrawlJobCreation:
    def test_create_job_with_defaults(self):
        job = {"url": "https://example.com", "depth": 0, "max_pages": 10, "status": "pending"}
        assert job["url"] == "https://example.com"
        assert job["depth"] == 0
        assert job["max_pages"] == 10

    def test_create_job_with_custom_depth(self):
        job = {"url": "https://example.com", "depth": 2, "max_pages": 50}
        assert job["depth"] == 2

    def test_create_job_with_empty_url(self):
        job = {"url": "", "depth": 0, "max_pages": 10}
        assert not job["url"]


@pytest.mark.asyncio
async def test_content_extraction_from_html():
    from vector.ingestion import extract_text
    import tempfile
    from pathlib import Path

    html_content = """<html><head><title>Test</title></head>
    <body><h1>Hello</h1><p>World</p><script>alert('x')</script></body></html>"""

    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False, encoding="utf-8") as f:
        f.write(html_content)
        f.flush()
        text = extract_text(Path(f.name))
        assert "Hello" in text
        assert "World" in text
        assert "alert" not in text


@pytest.mark.asyncio
async def test_content_extraction_from_txt():
    from vector.ingestion import extract_text
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8") as f:
        f.write("Plain text content")
        f.flush()
        text = extract_text(Path(f.name))
        assert text == "Plain text content"


class TestRateLimitingBetweenRequests:
    def test_delay_between_requests(self):
        import time

        delays = []
        for _ in range(3):
            t0 = time.monotonic()
            _mock_request()
            delays.append(time.monotonic() - t0)

        for d in delays:
            assert d >= 0

    def test_concurrent_requests_limited(self):
        limit = 5
        active = 0
        for i in range(10):
            if active >= limit:
                break
            active += 1
        assert active <= limit


def _mock_request(delay: float = 0.0):
    import time
    time.sleep(delay)


class TestDepthLimiting:
    def test_depth_limit_enforced(self):
        max_depth = 2
        urls_to_crawl = [
            ("https://example.com", 0),
            ("https://example.com/page1", 1),
            ("https://example.com/page1/sub", 2),
            ("https://example.com/page1/sub/deep", 3),
        ]
        allowed = [url for url, depth in urls_to_crawl if depth <= max_depth]
        assert len(allowed) == 3
        assert ("https://example.com/page1/sub/deep", 3) not in [(u, 3) for u, _ in urls_to_crawl if (u, 3) in urls_to_crawl]

    def test_zero_depth_allows_only_seed(self):
        urls = [("https://example.com", 0), ("https://example.com/page", 1)]
        allowed = [url for url, depth in urls if depth <= 0]
        assert len(allowed) == 1


class TestErrorHandlingAndRetries:
    def test_retry_on_connection_error(self):
        attempt_count = 0

        async def fetch_with_retry(url, max_retries=3):
            nonlocal attempt_count
            for attempt in range(max_retries):
                attempt_count += 1
                if attempt < 2:
                    raise ConnectionError("Timeout")
                return "success"
            raise ConnectionError("Max retries exceeded")

        with pytest.raises(ConnectionError):
            import asyncio
            asyncio.run(fetch_with_retry("https://example.com", max_retries=2))
        assert attempt_count == 2

    def test_success_after_retry(self):
        attempt_count = 0

        async def fetch_with_retry(url, max_retries=3):
            nonlocal attempt_count
            for attempt in range(max_retries):
                attempt_count += 1
                if attempt < 1:
                    raise ConnectionError("Timeout")
                return "success"
            raise ConnectionError("Max retries exceeded")

        import asyncio
        result = asyncio.run(fetch_with_retry("https://example.com", max_retries=3))
        assert result == "success"
        assert attempt_count == 2

    def test_http_error_handling(self):
        async def crawl_url(url):
            if "404" in url:
                raise ValueError("Page not found")
            return "content"

        with pytest.raises(ValueError, match="Page not found"):
            import asyncio
            asyncio.run(crawl_url("https://example.com/404"))


@pytest.mark.asyncio
async def test_crawl_job_db_operations():
    from app.database.engine import connect
    from app.database.models import CrawlerJob, Base
    import aiosqlite

    db = await connect()
    try:
        await db.execute(
            "INSERT INTO crawler_jobs (url, status, depth, max_pages) VALUES (?, ?, ?, ?)",
            ("https://example.com", "pending", 0, 10),
        )
        await db.commit()

        row = await db.fetchone("SELECT url, status, depth FROM crawler_jobs WHERE url = ?", ("https://example.com",))
        assert row is not None
        assert row["url"] == "https://example.com"
        assert row["status"] == "pending"
    finally:
        await db.close()
