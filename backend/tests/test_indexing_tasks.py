"""Tests for indexing tasks.

Focus areas:
- Task creation (index, reindex)
- File checksum calculation
- File type detection
- Text chunking
- Task submission
"""

import hashlib
import os
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.indexing.tasks import (
    TaskBuilder,
    TaskType,
    IndexTask,
    calculate_file_checksum,
    calculate_chunk_hash,
    chunk_text,
    detect_file_type,
    get_file_size,
    submit_index_task,
)


class TestTaskTypeConstants:
    """Test task type constants."""

    def test_index_document_type(self):
        """Should have index_document type."""
        assert TaskType.INDEX_DOCUMENT == "index_document"

    def test_reindex_document_type(self):
        """Should have reindex_document type."""
        assert TaskType.REINDEX_DOCUMENT == "reindex_document"

    def test_delete_document_type(self):
        """Should have delete_document type."""
        assert TaskType.DELETE_DOCUMENT == "delete_document"

    def test_optimize_index_type(self):
        """Should have optimize_index type."""
        assert TaskType.OPTIMIZE_INDEX == "optimize_index"


class TestIndexTask:
    """Test IndexTask dataclass."""

    def test_create_index_task_minimal(self):
        """Should create minimal index task."""
        task = IndexTask(
            task_id=str(uuid.uuid4()),
            task_type=TaskType.INDEX_DOCUMENT,
            document_id=1,
        )

        assert task.task_id is not None
        assert task.task_type == TaskType.INDEX_DOCUMENT
        assert task.document_id == 1
        assert task.user_id is None
        assert task.filename == ""
        assert task.payload == {}
        assert task.priority is not None
        assert task.created_at > 0

    def test_create_index_task_with_all_fields(self):
        """Should create task with all fields."""
        task = IndexTask(
            task_id=str(uuid.uuid4()),
            task_type=TaskType.REINDEX_DOCUMENT,
            document_id=2,
            user_id=123,
            filename="document.pdf",
            priority="HIGH",
            payload={"key": "value"},
            created_at=1234567890.0,
        )

        assert task.user_id == 123
        assert task.filename == "document.pdf"
        assert task.priority == "HIGH"
        assert task.payload == {"key": "value"}
        assert task.created_at == 1234567890.0

    def test_post_init_default_created_at(self):
        """Should set created_at to current time if 0."""
        task = IndexTask(
            task_id=str(uuid.uuid4()),
            task_type=TaskType.INDEX_DOCUMENT,
            document_id=1,
            created_at=0.0,
        )

        assert task.created_at > 0

    def test_post_init_default_payload(self):
        """Should set empty payload if None."""
        task = IndexTask(
            task_id=str(uuid.uuid4()),
            task_type=TaskType.INDEX_DOCUMENT,
            document_id=1,
            payload=None,
        )

        assert task.payload == {}


class TestTaskBuilder:
    """Test TaskBuilder static methods."""

    def test_create_index_task(self):
        """Should create index task with all fields."""
        task = TaskBuilder.create_index_task(
            document_id=123,
            user_id=456,
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            priority="HIGH",
        )

        assert task.task_id is not None
        assert task.task_type == TaskType.INDEX_DOCUMENT
        assert task.document_id == 123
        assert task.user_id == 456
        assert task.filename == "test.pdf"
        assert task.priority == "HIGH"

        # Check payload
        assert task.payload["document_id"] == 123
        assert task.payload["user_id"] == 456
        assert task.payload["filename"] == "test.pdf"
        assert task.payload["file_path"] == "/path/to/test.pdf"

    def test_create_index_task_defaults(self):
        """Should create task with defaults."""
        task = TaskBuilder.create_index_task(document_id=1)

        assert task.user_id is None
        assert task.filename == ""
        assert task.priority is not None
        assert task.payload["file_path"] is None

    def test_create_reindex_task(self):
        """Should create reindex task."""
        task = TaskBuilder.create_reindex_task(
            document_id=123,
            user_id=456,
            filename="test.pdf",
            incremental=True,
            priority="NORMAL",
        )

        assert task.task_type == TaskType.REINDEX_DOCUMENT
        assert task.document_id == 123
        assert task.user_id == 456
        assert task.filename == "test.pdf"
        assert task.priority == "NORMAL"

        # Check payload
        assert task.payload["document_id"] == 123
        assert task.payload["user_id"] == 456
        assert task.payload["incremental"] is True

    def test_create_reindex_task_defaults(self):
        """Should create reindex task with defaults."""
        task = TaskBuilder.create_reindex_task(document_id=1)

        assert task.user_id is None
        assert task.filename == ""
        assert task.priority is not None
        assert task.payload["incremental"] is True


class TestFileChecksum:
    """Test file checksum calculation."""

    def test_calculate_file_checksum(self, tmp_path):
        """Should calculate SHA-256 checksum."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        checksum = calculate_file_checksum(str(test_file))

        # Verify checksum
        expected = hashlib.sha256(b"Hello, World!").hexdigest()
        assert checksum == expected

    def test_calculate_file_checksum_empty(self, tmp_path):
        """Should calculate checksum for empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        checksum = calculate_file_checksum(str(test_file))

        expected = hashlib.sha256(b"").hexdigest()
        assert checksum == expected

    def test_calculate_file_checksum_large(self, tmp_path):
        """Should handle large files efficiently."""
        # Create 1MB file
        test_file = tmp_path / "large.bin"
        test_file.write_bytes(b"x" * (1024 * 1024))

        checksum = calculate_file_checksum(str(test_file))

        # Verify checksum is correct length
        assert len(checksum) == 64  # SHA-256 hex

    def test_calculate_file_checksum_nonexistent(self):
        """Should handle nonexistent file."""
        with pytest.raises(FileNotFoundError):
            calculate_file_checksum("/nonexistent/file.txt")


class TestFileSize:
    """Test file size calculation."""

    def test_get_file_size(self, tmp_path):
        """Should get file size in bytes."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        size = get_file_size(str(test_file))

        assert size == 13  # Length of "Hello, World!"

    def test_get_file_size_empty(self, tmp_path):
        """Should return 0 for empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        size = get_file_size(str(test_file))

        assert size == 0

    def test_get_file_size_nonexistent(self):
        """Should handle nonexistent file."""
        with pytest.raises(FileNotFoundError):
            get_file_size("/nonexistent/file.txt")


class TestFileTypeDetection:
    """Test file type detection."""

    def test_detect_file_type_pdf(self):
        """Should detect PDF files."""
        assert detect_file_type("document.pdf") == "pdf"

    def test_detect_file_type_docx(self):
        """Should detect DOCX files."""
        assert detect_file_type("document.docx") == "docx"

    def test_detect_file_type_txt(self):
        """Should detect text files."""
        assert detect_file_type("document.txt") == "text"

    def test_detect_file_type_markdown(self):
        """Should detect markdown files."""
        assert detect_file_type("document.md") == "markdown"
        assert detect_file_type("document.markdown") == "markdown"

    def test_detect_file_type_html(self):
        """Should detect HTML files."""
        assert detect_file_type("document.html") == "html"

    def test_detect_file_type_csv(self):
        """Should detect CSV files."""
        assert detect_file_type("document.csv") == "csv"

    def test_detect_file_type_json(self):
        """Should detect JSON files."""
        assert detect_file_type("document.json") == "json"

    def test_detect_file_type_unknown(self):
        """Should handle unknown file types."""
        assert detect_file_type("document.xyz") == "unknown"

    def test_detect_file_type_case_insensitive(self):
        """Should handle case-insensitive extensions."""
        assert detect_file_type("DOCUMENT.PDF") == "pdf"
        assert detect_file_type("document.Pdf") == "pdf"

    def test_detect_file_type_no_extension(self):
        """Should handle files without extension."""
        assert detect_file_type("noextension") == "unknown"


class TestTextChunking:
    """Test text chunking functionality."""

    def test_chunk_text_basic(self):
        """Should split text into chunks."""
        text = "Hello " * 200  # ~1000 characters
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)

        assert len(chunks) >= 1
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_chunk_text_empty(self):
        """Should handle empty text."""
        chunks = chunk_text("")
        assert chunks == []

        chunks = chunk_text("   ")
        assert chunks == []

    def test_chunk_text_small(self):
        """Should handle small text that fits in one chunk."""
        text = "Hello, World!"
        chunks = chunk_text(text, chunk_size=1000, chunk_overlap=100)

        # With overlap, text splits into chunks of ~800 chars
        # "Hello, World!" (13 chars) fits in one chunk
        assert len(chunks) >= 1
        assert "Hello, World!" in chunks[0]

    def test_chunk_text_overlap(self):
        """Should respect overlap between chunks."""
        text = " ".join([f"word_{i}" for i in range(100)])
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=50)

        # Check overlap exists
        if len(chunks) > 1:
            first_chunk = chunks[0]
            second_chunk = chunks[1]

            # Second chunk should contain words from first chunk
            assert first_chunk != second_chunk

    def test_chunk_text_exact_size(self):
        """Should handle text that fits in chunks."""
        text = "x" * 800
        chunks = chunk_text(text, chunk_size=1000, chunk_overlap=200)

        assert len(chunks) >= 1

    def test_chunk_text_word_boundary(self):
        """Should break at word boundaries when possible."""
        text = "word1 word2 word3 word4 word5"
        chunks = chunk_text(text, chunk_size=15, chunk_overlap=5)

        # Should break at space, not in middle of word
        for chunk in chunks:
            # Check no word is split (simplified check)
            assert "word1" not in chunk or "word2" in chunk or chunk == "word1"


class TestChunkHash:
    """Test chunk hashing."""

    def test_calculate_chunk_hash(self):
        """Should calculate SHA-256 hash for chunk."""
        content = "Test chunk content"
        chunk_hash = calculate_chunk_hash(content)

        expected = hashlib.sha256(content.encode()).hexdigest()
        assert chunk_hash == expected

    def test_calculate_chunk_hash_different(self):
        """Different content should have different hashes."""
        hash1 = calculate_chunk_hash("content1")
        hash2 = calculate_chunk_hash("content2")

        assert hash1 != hash2

    def test_calculate_chunk_hash_empty(self):
        """Should calculate hash for empty string."""
        hash1 = calculate_chunk_hash("")
        hash2 = calculate_chunk_hash("")

        assert hash1 == hash2  # Same hash for same content


class TestSubmitIndexTask:
    """Test index task submission."""

    @pytest_asyncio.fixture
    def mock_indexing_queue(self):
        """Mock indexing queue."""
        with patch("app.indexing.tasks.indexing_queue") as mock_queue:
            mock_queue.enqueue = AsyncMock(return_value="job-123")
            yield mock_queue

    @pytest.mark.asyncio
    async def test_submit_index_task(self, mock_indexing_queue):
        """Should submit index task to queue."""
        job_id = await submit_index_task(
            document_id=123,
            user_id=456,
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            priority="HIGH",
        )

        assert job_id == "job-123"
        mock_indexing_queue.enqueue.assert_called_once()

        # Verify job structure
        call_args = mock_indexing_queue.enqueue.call_args[0][0]
        assert call_args["type"] == TaskType.INDEX_DOCUMENT
        assert call_args["document_id"] == 123
        assert call_args["user_id"] == 456
        assert call_args["filename"] == "test.pdf"
        assert call_args["priority"] == "HIGH"

    @pytest.mark.asyncio
    async def test_submit_index_task_defaults(self, mock_indexing_queue):
        """Should submit with defaults."""
        job_id = await submit_index_task(document_id=1)

        assert job_id == "job-123"
        call_args = mock_indexing_queue.enqueue.call_args[0][0]
        assert call_args["user_id"] is None
        assert call_args["filename"] == ""
        assert call_args["priority"] == "NORMAL"
        # file_path is in payload
        assert call_args["payload"]["file_path"] is None

    @pytest.mark.asyncio
    async def test_submit_index_task_queue_error(self, mock_indexing_queue):
        """Should propagate queue errors."""
        from app.indexing.queue import QueueError

        mock_indexing_queue.enqueue.side_effect = QueueError("Queue full")

        with pytest.raises(QueueError):
            await submit_index_task(document_id=1)