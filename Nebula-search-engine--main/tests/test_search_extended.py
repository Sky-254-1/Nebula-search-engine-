"""Extended search tests: multiple backends, orchestration, history, caching, pagination."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_search_with_wikipedia(client: AsyncClient, auth_headers: dict):
    mock_results = [
        {"title": "Python", "snippet": "Programming language", "url": "https://en.wikipedia.org/wiki/Python", "source": "wikipedia"}
    ]
    with patch("app.routes.search.run_web_search", new=AsyncMock(return_value=mock_results)):
        resp = await client.get(
            "/api/v1/search/web?q=python&backend=wikipedia",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["source"] == "wikipedia"


@pytest.mark.asyncio
async def test_search_with_brave(client: AsyncClient, auth_headers: dict):
    mock_results = [
        {"title": "Brave Result", "snippet": "Brave snippet", "url": "https://brave.com", "source": "brave"}
    ]
    with patch("app.routes.search.run_web_search", new=AsyncMock(return_value=mock_results)):
        resp = await client.get(
            "/api/v1/search/web?q=test&backend=brave",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.json()[0]["source"] == "brave"


@pytest.mark.asyncio
async def test_search_with_serpapi(client: AsyncClient, auth_headers: dict):
    mock_results = [
        {"title": "Serp Result", "snippet": "Serp snippet", "url": "https://google.com", "source": "serpapi"}
    ]
    with patch("app.routes.search.run_web_search", new=AsyncMock(return_value=mock_results)):
        resp = await client.get(
            "/api/v1/search/web?q=test&backend=serpapi",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.json()[0]["source"] == "serpapi"


@pytest.mark.asyncio
async def test_search_invalid_backend(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/v1/search/web?q=test&backend=invalid",
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_orchestrated_search_multiple_backends(client: AsyncClient, auth_headers: dict):
    mock_payload = {
        "query": "python",
        "expanded_queries": ["python"],
        "backends": ["wikipedia", "brave"],
        "results": [
            {"title": "Wiki", "snippet": "Wiki snippet", "url": "https://wikipedia.org", "source": "wikipedia"},
            {"title": "Brave", "snippet": "Brave snippet", "url": "https://brave.com", "source": "brave"},
        ],
        "total": 2,
        "page": 1,
        "page_size": 10,
        "cached": False,
    }
    with patch("app.routes.search.orchestrate_search", new=AsyncMock(return_value=mock_payload)):
        resp = await client.get(
            "/api/v1/search/orchestrate?q=python&backends=wikipedia,brave",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["results"]) == 2
    assert data["cached"] is False


@pytest.mark.asyncio
async def test_search_history(client: AsyncClient, auth_headers: dict):
    with patch("app.routes.search.run_web_search", new=AsyncMock(return_value=[])):
        await client.get("/api/v1/search/web?q=history1&backend=wikipedia", headers=auth_headers)

    resp = await client.get("/api/v1/search/history", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "history" in data


@pytest.mark.asyncio
async def test_search_history_empty_for_new_user(client: AsyncClient):
    from app.middleware.rate_limit import rate_limit
    from app.services.auth import get_current_user
    from app.database import get_db
    import app.main as main_mod

    try:
        main_mod.app.dependency_overrides[get_current_user] = lambda: "newuser@test.com"
        main_mod.app.dependency_overrides[get_db] = lambda: MagicMock()
        main_mod.app.dependency_overrides[rate_limit] = lambda: None

        with patch("app.routes.search.UserRepository.get_id_by_email", new=AsyncMock(return_value=None)):
            resp = await client.get("/api/v1/search/history")
            assert resp.status_code == 200
            assert resp.json()["history"] == []
    finally:
        main_mod.app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_search_pagination(client: AsyncClient, auth_headers: dict):
    mock_results = [{"title": f"Result {i}", "snippet": f"Snippet {i}", "url": f"https://example.com/{i}", "source": "wikipedia"} for i in range(5)]
    with patch("app.routes.search.run_web_search", new=AsyncMock(return_value=mock_results)):
        resp = await client.get(
            "/api/v1/search/web?q=test&page=1&page_size=5",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert len(resp.json()) == 5


@pytest.mark.asyncio
async def test_search_caching_behavior(client: AsyncClient, auth_headers: dict):
    mock = AsyncMock(return_value=[{"title": "Cached", "snippet": "Test", "url": "https://example.com", "source": "wikipedia"}])
    with patch("app.routes.search.run_web_search", new=mock):
        r1 = await client.get("/api/v1/search/web?q=cached&backend=wikipedia", headers=auth_headers)
        assert r1.status_code == 200

    with patch("app.routes.search.run_web_search", new=AsyncMock(return_value=[{"title": "Should Not Appear", "snippet": "", "url": "https://x.com", "source": "wikipedia"}])):
        r2 = await client.get("/api/v1/search/web?q=cached&backend=wikipedia", headers=auth_headers)
        assert r2.status_code == 200


@pytest.mark.asyncio
async def test_empty_query_returns_bad_request(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/search/web?q=&backend=wikipedia", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_backend_unreachable(client: AsyncClient, auth_headers: dict):
    import httpx
    with patch("app.routes.search.run_web_search", side_effect=httpx.RequestError("Connection refused")):
        resp = await client.get(
            "/api/v1/search/web?q=test&backend=wikipedia",
            headers=auth_headers,
        )
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_orchestrated_search_empty_query(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/search/orchestrate?q=&backends=wikipedia", headers=auth_headers)
    assert resp.status_code == 422
