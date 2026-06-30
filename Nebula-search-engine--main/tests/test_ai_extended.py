"""Extended AI tests: provider fallback, streaming, chat history CRUD, caching."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ai_ask_with_openai_provider(client: AsyncClient, auth_headers: dict):
    with patch("app.routes.ai.get_ai_answer", new=AsyncMock(return_value=("OpenAI answer.", "openai"))):
        resp = await client.post(
            "/api/v1/ai/ask",
            json={"prompt": "What is Python?"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "OpenAI answer."
    assert data["provider"] == "openai"


@pytest.mark.asyncio
async def test_ai_ask_fallback_provider_chain(client: AsyncClient, auth_headers: dict):
    with patch("app.routes.ai.get_ai_answer", new=AsyncMock(return_value=("Fallback answer.", "duckduckgo"))):
        resp = await client.post(
            "/api/v1/ai/ask",
            json={"prompt": "unknown topic"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.json()["provider"] == "duckduckgo"


@pytest.mark.asyncio
async def test_ai_ask_no_answer_from_any_provider(client: AsyncClient, auth_headers: dict):
    with patch("app.routes.ai.get_ai_answer", new=AsyncMock(return_value=(None, "none"))):
        resp = await client.post(
            "/api/v1/ai/ask",
            json={"prompt": "obscure query xyz"},
            headers=auth_headers,
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ai_ask_streaming(client: AsyncClient, auth_headers: dict):
    async def mock_stream(_prompt):
        yield "chunk1"
        yield "chunk2"

    with patch("app.routes.ai.stream_ai_answer", side_effect=mock_stream):
        resp = await client.post(
            "/api/v1/ai/ask/stream",
            json={"prompt": "stream test"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "text/event-stream"
    body = resp.text
    assert "chunk1" in body
    assert "chunk2" in body


@pytest.mark.asyncio
async def test_chat_history_crud(client: AsyncClient, auth_headers: dict):
    with patch("app.routes.ai.get_ai_answer", new=AsyncMock(return_value=("Test answer.", "openai"))):
        await client.post(
            "/api/v1/ai/ask",
            json={"prompt": "What is AI?"},
            headers=auth_headers,
        )

    resp = await client.get("/api/v1/ai/chat/history", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "messages" in data
    assert len(data["messages"]) >= 2

    messages = data["messages"]
    assert messages[0]["role"] == "user"
    assert messages[-1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_clear_chat_history(client: AsyncClient, auth_headers: dict):
    with patch("app.routes.ai.get_ai_answer", new=AsyncMock(return_value=("Answer.", "openai"))):
        await client.post(
            "/api/v1/ai/ask",
            json={"prompt": "Hello"},
            headers=auth_headers,
        )

    resp = await client.delete("/api/v1/ai/chat/history", headers=auth_headers)
    assert resp.status_code == 200

    hist = await client.get("/api/v1/ai/chat/history", headers=auth_headers)
    assert hist.json()["messages"] == []


@pytest.mark.asyncio
async def test_chat_history_empty_for_new_user(client: AsyncClient):
    from app.database import get_db
    from app.services.auth import get_current_user
    import app.main as main_mod

    try:
        main_mod.app.dependency_overrides[get_current_user] = lambda: "new@test.com"
        main_mod.app.dependency_overrides[get_db] = lambda: MagicMock()

        with patch("app.routes.ai.UserRepository.get_id_by_email", new=AsyncMock(return_value=None)):
            resp = await client.get("/api/v1/ai/chat/history")
            assert resp.status_code == 200
            assert resp.json()["messages"] == []
    finally:
        main_mod.app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_synthesize_endpoint(client: AsyncClient, auth_headers: dict):
    from app.models.schemas import SynthesizeResponse
    with patch("app.routes.ai.synthesize_snippets", new=AsyncMock(return_value=SynthesizeResponse(synthesis="Summarized text."))):
        resp = await client.post(
            "/api/v1/ai/synthesize",
            json={"query": "python", "snippets": ["Python is great.", "Python is versatile."]},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.json()["synthesis"] == "Summarized text."


@pytest.mark.asyncio
async def test_ai_ask_caching(client: AsyncClient, auth_headers: dict):
    mock_fn = AsyncMock(return_value=("Cached answer.", "openai"))
    with patch("app.routes.ai.get_ai_answer", new=mock_fn):
        r1 = await client.post(
            "/api/v1/ai/ask",
            json={"prompt": "cache test"},
            headers=auth_headers,
        )
        assert r1.status_code == 200

    with patch("app.routes.ai.get_ai_answer", new=AsyncMock(return_value=("Should not appear.", "openai"))):
        r2 = await client.post(
            "/api/v1/ai/ask",
            json={"prompt": "cache test"},
            headers=auth_headers,
        )
        assert r2.status_code == 200


@pytest.mark.asyncio
async def test_synthesize_fallback_no_provider(client: AsyncClient, auth_headers: dict):
    from app.services.ai import synthesize_snippets
    with patch("app.services.ai.router") as mock_router:
        mock_router.complete = AsyncMock(return_value=(None, "none"))
        result = await synthesize_snippets("python", ["Snippet one."])
    assert len(result.synthesis) > 0


@pytest.mark.asyncio
async def test_ai_ask_invalid_payload(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/ai/ask",
        json={"prompt": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 422
