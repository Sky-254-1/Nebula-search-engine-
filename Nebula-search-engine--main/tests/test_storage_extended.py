"""Extended storage tests: document upload validation, file types, size limits, CRUD, settings, exports."""

import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_allowed_file_types(client: AsyncClient, auth_headers: dict):
    for ext, mime in [(".txt", "text/plain"), (".md", "text/markdown"), (".json", "application/json"), (".csv", "text/csv")]:
        content = f"test content {ext}".encode()
        files = {"file": (f"test{ext}", io.BytesIO(content), mime)}
        resp = await client.post("/api/v1/storage/documents", headers=auth_headers, files=files)
        assert resp.status_code == 200, f"Failed for {ext}: {resp.json()}"


@pytest.mark.asyncio
async def test_upload_disallowed_file_type(client: AsyncClient, auth_headers: dict):
    files = {"file": ("test.exe", io.BytesIO(b"binary"), "application/x-msdownload")}
    resp = await client.post("/api/v1/storage/documents", headers=auth_headers, files=files)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_file_too_large(client: AsyncClient, auth_headers: dict):
    large_content = b"x" * (11 * 1024 * 1024)
    files = {"file": ("large.txt", io.BytesIO(large_content), "text/plain")}
    resp = await client.post("/api/v1/storage/documents", headers=auth_headers, files=files)
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_upload_without_file(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/storage/documents", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_document_crud(client: AsyncClient, auth_headers: dict):
    content = b"CRUD test document"
    files = {"file": ("crud.txt", io.BytesIO(content), "text/plain")}
    upload = await client.post("/api/v1/storage/documents", headers=auth_headers, files=files)
    assert upload.status_code == 200
    doc_id = upload.json()["id"]

    listing = await client.get("/api/v1/storage/documents", headers=auth_headers)
    assert listing.status_code == 200
    doc_ids = [d["id"] for d in listing.json()["documents"]]
    assert doc_id in doc_ids

    delete = await client.delete(f"/api/v1/storage/documents/{doc_id}", headers=auth_headers)
    assert delete.status_code == 200

    listing2 = await client.get("/api/v1/storage/documents", headers=auth_headers)
    doc_ids2 = [d["id"] for d in listing2.json()["documents"]]
    assert doc_id not in doc_ids2


@pytest.mark.asyncio
async def test_delete_nonexistent_document(client: AsyncClient, auth_headers: dict):
    resp = await client.delete("/api/v1/storage/documents/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_settings_get_and_update(client: AsyncClient, auth_headers: dict):
    get_res = await client.get("/api/v1/storage/settings", headers=auth_headers)
    assert get_res.status_code == 200
    assert "settings" in get_res.json()

    put_res = await client.put(
        "/api/v1/storage/settings",
        headers=auth_headers,
        json={"settings": {"theme": "dark", "backends": "wikipedia,brave"}},
    )
    assert put_res.status_code == 200
    assert put_res.json()["settings"]["theme"] == "dark"

    get_res2 = await client.get("/api/v1/storage/settings", headers=auth_headers)
    assert get_res2.json()["settings"]["theme"] == "dark"


@pytest.mark.asyncio
async def test_export_create_and_list(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/storage/exports",
        headers=auth_headers,
        json={"export_type": "search_history", "data": {"queries": ["test"]}},
    )
    assert create.status_code == 200
    export_id = create.json()["id"]

    listing = await client.get("/api/v1/storage/exports", headers=auth_headers)
    assert listing.status_code == 200
    exports = listing.json()["exports"]
    assert any(e["id"] == export_id for e in exports)


@pytest.mark.asyncio
async def test_storage_requires_auth(client: AsyncClient):
    assert (await client.get("/api/v1/storage/settings")).status_code == 401
    assert (await client.post("/api/v1/storage/exports", json={"export_type": "test", "data": {}})).status_code == 401
    assert (await client.get("/api/v1/storage/documents")).status_code == 401


@pytest.mark.asyncio
async def test_upload_html_file(client: AsyncClient, auth_headers: dict):
    content = b"<html><body><p>Hello World</p></body></html>"
    files = {"file": ("page.html", io.BytesIO(content), "text/html")}
    resp = await client.post("/api/v1/storage/documents", headers=auth_headers, files=files)
    assert resp.status_code == 200
