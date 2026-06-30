"""Extended vector tests: document indexing, hybrid search, reindexing, export, citations, stats."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_vector_upload_and_index_status(client: AsyncClient, auth_headers: dict):
    content = b"Python is a popular programming language for data science."
    files = {"file": ("test.txt", content, "text/plain")}
    upload = await client.post("/api/v1/storage/documents", headers=auth_headers, files=files)
    assert upload.status_code == 200
    doc_id = upload.json()["id"]

    index = await client.post(f"/api/v1/vector/documents/{doc_id}/index-now", headers=auth_headers)
    assert index.status_code == 200

    status = await client.get(f"/api/v1/vector/documents/{doc_id}/status", headers=auth_headers)
    assert status.status_code == 200
    assert status.json()["id"] == doc_id


@pytest.mark.asyncio
async def test_vector_search_hybrid(client: AsyncClient, auth_headers: dict):
    content = b"Nebula hybrid vector search engine test for pytest."
    files = {"file": ("hybrid.txt", content, "text/plain")}
    upload = await client.post("/api/v1/storage/documents", headers=auth_headers, files=files)
    doc_id = upload.json()["id"]

    await client.post(f"/api/v1/vector/documents/{doc_id}/index-now", headers=auth_headers)

    search = await client.post(
        "/api/v1/vector/search",
        headers=auth_headers,
        json={"query": "hybrid vector search", "top_k": 5},
    )
    assert search.status_code == 200
    data = search.json()
    assert data["total"] > 0


@pytest.mark.asyncio
async def test_vector_reindex_document(client: AsyncClient, auth_headers: dict):
    content = b"Reindex test document content."
    files = {"file": ("reindex.txt", content, "text/plain")}
    upload = await client.post("/api/v1/storage/documents", headers=auth_headers, files=files)
    doc_id = upload.json()["id"]

    resp = await client.post(f"/api/v1/vector/documents/{doc_id}/reindex", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["document_id"] == doc_id


@pytest.mark.asyncio
async def test_vector_reindex_all(client: AsyncClient, auth_headers: dict):
    from app.routes import vector as vector_routes
    from app.middleware.rate_limit import rate_limit
    from app.services.auth import get_current_user
    from app.database import get_db
    import app.main as main_mod

    try:
        main_mod.app.dependency_overrides[get_current_user] = lambda: "test@example.com"
        main_mod.app.dependency_overrides[get_db] = lambda: MagicMock()
        main_mod.app.dependency_overrides[rate_limit] = lambda: None

        with patch("app.routes.vector.UserRepository.get_id_by_email", new=AsyncMock(return_value=1)), \
             patch("app.routes.vector.DocumentRepository.list_for_user", new=AsyncMock(return_value=[{"id": 1}, {"id": 2}])), \
             patch("app.routes.vector.job_queue.enqueue", new=AsyncMock()) as mock_enqueue:

            resp = await client.post("/api/v1/vector/documents/reindex-all", json={"limit": 10})
            assert resp.status_code == 200
            assert resp.json()["count"] == 2
            assert mock_enqueue.call_count == 2
    finally:
        main_mod.app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_vector_stats(client: AsyncClient, auth_headers: dict):
    from app.middleware.rate_limit import rate_limit
    from app.services.auth import get_current_user
    from app.database import get_db
    import app.main as main_mod

    try:
        main_mod.app.dependency_overrides[get_current_user] = lambda: "test@example.com"
        main_mod.app.dependency_overrides[get_db] = lambda: MagicMock()
        main_mod.app.dependency_overrides[rate_limit] = lambda: None

        with patch("app.routes.vector.UserRepository.get_id_by_email", new=AsyncMock(return_value=1)), \
             patch("app.routes.vector.ChunkRepository.list_for_user", new=AsyncMock(return_value=[{"document_id": 1}, {"document_id": 1}, {"document_id": 2}])):

            resp = await client.get("/api/v1/vector/stats")
            assert resp.status_code == 200
            data = resp.json()
            assert data["chunks"] == 3
            assert data["documents_indexed"] == 2
    finally:
        main_mod.app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_vector_export(client: AsyncClient, auth_headers: dict):
    from app.middleware.rate_limit import rate_limit
    from app.services.auth import get_current_user
    from app.database import get_db
    import app.main as main_mod

    try:
        main_mod.app.dependency_overrides[get_current_user] = lambda: "test@example.com"
        main_mod.app.dependency_overrides[get_db] = lambda: MagicMock()
        main_mod.app.dependency_overrides[rate_limit] = lambda: None

        with patch("app.routes.vector.UserRepository.get_id_by_email", new=AsyncMock(return_value=1)), \
             patch("app.routes.vector.ChunkRepository.list_for_user", new=AsyncMock(return_value=[{"id": 1}])), \
             patch("app.routes.vector.ExportRepository.create", new=AsyncMock(return_value=101)), \
             patch("pathlib.Path.mkdir"), \
             patch("pathlib.Path.write_text"):

            resp = await client.post("/api/v1/vector/export")
            assert resp.status_code == 200
            assert resp.json()["export_id"] == 101
    finally:
        main_mod.app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_vector_citations_list(client: AsyncClient, auth_headers: dict):
    from app.middleware.rate_limit import rate_limit
    from app.services.auth import get_current_user
    from app.database import get_db
    import app.main as main_mod

    try:
        main_mod.app.dependency_overrides[get_current_user] = lambda: "test@example.com"
        main_mod.app.dependency_overrides[get_db] = lambda: MagicMock()
        main_mod.app.dependency_overrides[rate_limit] = lambda: None

        mock_citations = [
            {"id": 1, "document_id": 1, "chunk_id": 1, "query": "test", "snippet": "snippet", "score": 0.9, "created_at": "2025-01-01"},
        ]
        with patch("app.routes.vector.UserRepository.get_id_by_email", new=AsyncMock(return_value=1)), \
             patch("app.routes.vector.CitationRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.list_for_user = AsyncMock(return_value=mock_citations)
            mock_repo_cls.return_value = mock_repo

            resp = await client.get("/api/v1/vector/citations")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["citations"]) == 1
            assert data["citations"][0]["query"] == "test"
    finally:
        main_mod.app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_vector_document_status_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/vector/documents/99999/status", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_hybrid_search_embeddings(client: AsyncClient, auth_headers: dict):
    from vector.embeddings import embed_text, _hash_embed
    vec, model, dims = await embed_text("test embedding")
    assert model == "local-hash"
    assert len(vec) == dims

    same_vec, _, _ = await embed_text("test embedding")
    assert vec == same_vec


@pytest.mark.asyncio
async def test_hybrid_search_imports():
    from vector.retrieval import cosine_similarity, keyword_score, retrieve_chunks
    assert callable(cosine_similarity)
    assert callable(keyword_score)
    assert callable(retrieve_chunks)
