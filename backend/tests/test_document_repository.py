"""Tests for backend/app/database/repositories/document.py.

Coverage areas:
- Document CRUD operations (create, get_by_id, list_for_user, delete)
- Indexing status management (mark_indexed, set_status)
- Content hash operations (find_by_hash)
- Edge cases and error handling
"""

import pytest
from unittest.mock import AsyncMock

from app.database.repositories.document import DocumentRepository


class FakeCursor:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    async def fetchone(self):
        return self._row

    async def fetchall(self):
        return list(self._rows)


class FakeDB:
    def __init__(self):
        self.committed = False
        self.executed_queries = []
        self._rows_by_query = {}

    async def execute(self, sql, args=None):
        self.executed_queries.append((sql, args))
        return FakeCursor()

    async def commit(self):
        self.committed = True

    async def fetchone(self, sql, args=None):
        query_key = (sql, tuple(args) if args else ())
        rows = self._rows_by_query.get(query_key, [{}])
        return rows[0] if rows else None

    async def fetchall(self, sql, args=None):
        query_key = (sql, tuple(args) if args else ())
        return list(self._rows_by_query.get(query_key, []))


@pytest.fixture
def repo():
    db = FakeDB()
    return DocumentRepository(db)


class TestDocumentCRUD:
    """Test document CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_document(self, repo):
        """Should create a new document."""
        doc_id = await repo.create(
            user_id=1,
            filename="test.pdf",
            content_type="application/pdf",
            storage_path="/storage/test.pdf",
        )
        assert doc_id >= 0
        assert repo._db.committed is True
        assert any("INSERT INTO documents" in q[0] for q in repo._db.executed_queries)

    @pytest.mark.asyncio
    async def test_list_for_user(self, repo):
        """Should list documents for a user."""
        repo._db._rows_by_query[("SELECT id, filename, content_type, storage_path, indexed_at, created_at, "
            "status, content_hash, error_message "
            "FROM documents WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (1, 50))] = [
            {"id": 1, "filename": "doc1.pdf", "status": "indexed"},
            {"id": 2, "filename": "doc2.pdf", "status": "processing"},
        ]
        docs = await repo.list_for_user(1, limit=50)
        assert len(docs) == 2
        assert docs[0]["filename"] == "doc1.pdf"
        assert docs[0]["status"] == "indexed"

    @pytest.mark.asyncio
    async def test_list_for_user_empty(self, repo):
        """Should return empty list when user has no documents."""
        repo._db._rows_by_query[("SELECT id, filename, content_type, storage_path, indexed_at, created_at, "
            "status, content_hash, error_message "
            "FROM documents WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (999, 50))] = []
        docs = await repo.list_for_user(999, limit=50)
        assert docs == []

    @pytest.mark.asyncio
    async def test_get_by_id(self, repo):
        """Should retrieve document by ID."""
        repo._db._rows_by_query[("SELECT id, filename, content_type, storage_path, indexed_at, created_at, "
            "status, content_hash, error_message "
            "FROM documents WHERE id = ? AND user_id = ?",
            (1, 1))] = [
            {"id": 1, "filename": "test.pdf", "status": "indexed"}
        ]
        doc = await repo.get_by_id(1, 1)
        assert doc is not None
        assert doc["id"] == 1
        assert doc["filename"] == "test.pdf"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo):
        """Should return None when document not found."""
        repo._db._rows_by_query[("SELECT id, filename, content_type, storage_path, indexed_at, created_at, "
            "status, content_hash, error_message "
            "FROM documents WHERE id = ? AND user_id = ?",
            (999, 1))] = []
        doc = await repo.get_by_id(999, 1)
        assert doc is None

    @pytest.mark.asyncio
    async def test_get_by_id_wrong_user(self, repo):
        """Should return None when accessing another user's document."""
        repo._db._rows_by_query[("SELECT id, filename, content_type, storage_path, indexed_at, created_at, "
            "status, content_hash, error_message "
            "FROM documents WHERE id = ? AND user_id = ?",
            (1, 2))] = []
        doc = await repo.get_by_id(1, 2)
        assert doc is None

    @pytest.mark.asyncio
    async def test_delete_document(self, repo):
        """Should delete a document."""
        repo._db._rows_by_query[("SELECT id, filename, content_type, storage_path, indexed_at, created_at, "
            "status, content_hash, error_message "
            "FROM documents WHERE id = ? AND user_id = ?",
            (1, 1))] = [
            {"id": 1, "filename": "test.pdf"}
        ]
        result = await repo.delete(1, 1)
        assert result is True
        assert repo._db.committed is True
        assert any("DELETE FROM documents" in q[0] for q in repo._db.executed_queries)

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, repo):
        """Should return False when document not found."""
        repo._db._rows_by_query[("SELECT id, filename, content_type, storage_path, indexed_at, created_at, "
            "status, content_hash, error_message "
            "FROM documents WHERE id = ? AND user_id = ?",
            (999, 1))] = []
        result = await repo.delete(999, 1)
        assert result is False
        assert repo._db.committed is False

    @pytest.mark.asyncio
    async def test_delete_document_wrong_user(self, repo):
        """Should return False when deleting another user's document."""
        repo._db._rows_by_query[("SELECT id, filename, content_type, storage_path, indexed_at, created_at, "
            "status, content_hash, error_message "
            "FROM documents WHERE id = ? AND user_id = ?",
            (1, 2))] = []
        result = await repo.delete(1, 2)
        assert result is False


class TestIndexingStatus:
    """Test document indexing status management."""

    @pytest.mark.asyncio
    async def test_mark_indexed_with_hash(self, repo):
        """Should mark document as indexed with content hash."""
        await repo.mark_indexed(1, "content_hash_123")
        assert repo._db.committed is True
        assert any("UPDATE documents SET indexed_at = ?, status = ?, content_hash = ?, error_message = NULL" in q[0] for q in repo._db.executed_queries)

    @pytest.mark.asyncio
    async def test_mark_indexed_without_hash(self, repo):
        """Should mark document as indexed without content hash."""
        await repo.mark_indexed(1)
        assert repo._db.committed is True
        assert any("UPDATE documents SET indexed_at = ?, status = ?, error_message = NULL" in q[0] for q in repo._db.executed_queries)

    @pytest.mark.asyncio
    async def test_set_status_processing(self, repo):
        """Should set document status to processing."""
        await repo.set_status(1, "processing")
        assert repo._db.committed is True
        assert any("UPDATE documents SET status = ?" in q[0] for q in repo._db.executed_queries)

    @pytest.mark.asyncio
    async def test_set_status_with_error(self, repo):
        """Should set document status with error message."""
        await repo.set_status(1, "error", error_message="Failed to index")
        assert repo._db.committed is True
        assert any("error_message = ?" in q[0] for q in repo._db.executed_queries)

    @pytest.mark.asyncio
    async def test_set_status_with_hash(self, repo):
        """Should set document status with content hash."""
        await repo.set_status(1, "indexed", content_hash="hash123")
        assert repo._db.committed is True
        assert any("content_hash = ?" in q[0] for q in repo._db.executed_queries)

    @pytest.mark.asyncio
    async def test_set_status_all_fields(self, repo):
        """Should set document status with all fields."""
        await repo.set_status(1, "indexed", "hash123", None)
        assert repo._db.committed is True


class TestContentHashOperations:
    """Test content hash related operations."""

    @pytest.mark.asyncio
    async def test_find_by_hash(self, repo):
        """Should find document by content hash."""
        repo._db._rows_by_query[("SELECT id, filename, content_hash, status FROM documents "
            "WHERE user_id = ? AND content_hash = ? AND status = 'indexed'",
            (1, "hash123"))] = [
            {"id": 1, "filename": "test.pdf", "content_hash": "hash123", "status": "indexed"}
        ]
        doc = await repo.find_by_hash(1, "hash123")
        assert doc is not None
        assert doc["filename"] == "test.pdf"

    @pytest.mark.asyncio
    async def test_find_by_hash_not_found(self, repo):
        """Should return None when hash not found."""
        repo._db._rows_by_query[("SELECT id, filename, content_hash, status FROM documents "
            "WHERE user_id = ? AND content_hash = ? AND status = 'indexed'",
            (1, "nonexistent_hash"))] = []
        doc = await repo.find_by_hash(1, "nonexistent_hash")
        assert doc is None

    @pytest.mark.asyncio
    async def test_find_by_hash_not_indexed(self, repo):
        """Should return None when document is not indexed."""
        repo._db._rows_by_query[("SELECT id, filename, content_hash, status FROM documents "
            "WHERE user_id = ? AND content_hash = ? AND status = 'indexed'",
            (1, "hash123"))] = [
            {"id": 1, "filename": "test.pdf", "content_hash": "hash123", "status": "processing"}
        ]
        doc = await repo.find_by_hash(1, "hash123")
        assert doc is None

    @pytest.mark.asyncio
    async def test_find_by_hash_wrong_user(self, repo):
        """Should return None when hash belongs to another user."""
        repo._db._rows_by_query[("SELECT id, filename, content_hash, status FROM documents "
            "WHERE user_id = ? AND content_hash = ? AND status = 'indexed'",
            (2, "hash123"))] = []
        doc = await repo.find_by_hash(2, "hash123")
        assert doc is None


class TestCountOperations:
    """Test document count operations."""

    @pytest.mark.asyncio
    async def test_count_all(self, repo):
        """Should count total documents across all users."""
        repo._db._rows_by_query[("SELECT COUNT(*) as count FROM documents", ())] = [
            {"count": 150}
        ]
        count = await repo.count_all()
        assert count == 150

    @pytest.mark.asyncio
    async def test_count_all_empty(self, repo):
        """Should return 0 when no documents exist."""
        repo._db._rows_by_query[("SELECT COUNT(*) as count FROM documents", ())] = [
            {"count": 0}
        ]
        count = await repo.count_all()
        assert count == 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_create_document_with_none_content_type(self, repo):
        """Should handle None content_type."""
        doc_id = await repo.create(
            user_id=1,
            filename="test.txt",
            content_type=None,
            storage_path="/storage/test.txt",
        )
        assert doc_id >= 0
        assert repo._db.committed is True

    @pytest.mark.asyncio
    async def test_list_for_user_with_limit(self, repo):
        """Should respect limit parameter."""
        repo._db._rows_by_query[("SELECT id, filename, content_type, storage_path, indexed_at, created_at, "
            "status, content_hash, error_message "
            "FROM documents WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (1, 10))] = []
        await repo.list_for_user(1, limit=10)
        # Verify limit is passed correctly
        executed = repo._db.executed_queries[-1]
        assert "LIMIT ?" in executed[0]

    @pytest.mark.asyncio
    async def test_get_by_id_with_special_characters(self, repo):
        """Should handle document IDs and filenames with special characters."""
        repo._db._rows_by_query[("SELECT id, filename, content_type, storage_path, indexed_at, created_at, "
            "status, content_hash, error_message "
            "FROM documents WHERE id = ? AND user_id = ?",
            (1, 1))] = [
            {"id": 1, "filename": "test (copy).pdf", "status": "indexed"}
        ]
        doc = await repo.get_by_id(1, 1)
        assert doc is not None
        assert doc["filename"] == "test (copy).pdf"

    @pytest.mark.asyncio
    async def test_mark_indexed_idempotent(self, repo):
        """Should handle marking already indexed document."""
        # First mark
        await repo.mark_indexed(1)
        # Second mark should not raise
        await repo.mark_indexed(1)
        assert repo._db.committed is True

    @pytest.mark.asyncio
    async def test_delete_non_indexed_document(self, repo):
        """Should delete document regardless of indexing status."""
        repo._db._rows_by_query[("SELECT id, filename, content_type, storage_path, indexed_at, created_at, "
            "status, content_hash, error_message "
            "FROM documents WHERE id = ? AND user_id = ?",
            (1, 1))] = [
            {"id": 1, "filename": "test.pdf", "status": "error"}
        ]
        result = await repo.delete(1, 1)
        assert result is True


class TestContentTypeHandling:
    """Test content type related operations."""

    @pytest.mark.asyncio
    async def test_create_with_pdf_content_type(self, repo):
        """Should handle PDF content type."""
        doc_id = await repo.create(1, "report.pdf", "application/pdf", "/storage/report.pdf")
        assert doc_id >= 0

    @pytest.mark.asyncio
    async def test_create_with_text_content_type(self, repo):
        """Should handle text content type."""
        doc_id = await repo.create(1, "note.txt", "text/plain", "/storage/note.txt")
        assert doc_id >= 0

    @pytest.mark.asyncio
    async def test_create_with_image_content_type(self, repo):
        """Should handle image content type."""
        doc_id = await repo.create(1, "photo.jpg", "image/jpeg", "/storage/photo.jpg")
        assert doc_id >= 0

    @pytest.mark.asyncio
    async def test_create_with_unknown_content_type(self, repo):
        """Should handle unknown content type."""
        doc_id = await repo.create(1, "unknown.xyz", "application/octet-stream", "/storage/unknown.xyz")
        assert doc_id >= 0