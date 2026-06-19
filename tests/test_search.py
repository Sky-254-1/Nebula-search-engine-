"""Search endpoint tests."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_web_search_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/search/web", params={"q": "python"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_web_search_wikipedia(client: AsyncClient, auth_headers: dict):
    mock_results = [
        {
            "title": "Python",
            "snippet": "A programming language",
            "url": "https://en.wikipedia.org/wiki/Python",
            "source": "wikipedia",
        }
    ]
    with patch("app.routes.search.run_web_search", new=AsyncMock(return_value=mock_results)):
        response = await client.get(
            "/api/v1/search/web",
            params={"q": "python", "backend": "wikipedia"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["source"] == "wikipedia"


@pytest.mark.asyncio
async def test_web_search_unknown_backend(client: AsyncClient, auth_headers: dict):
    response = await client.get(
        "/api/v1/search/web",
        params={"q": "test", "backend": "invalid"},
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_sanitize_query():
    from app.services.search import sanitize_query

    assert sanitize_query("  hello\x00world  ") == "helloworld"
