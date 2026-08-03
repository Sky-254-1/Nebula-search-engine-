"""Behavioral tests for incremental/detector.py pure-logic functions."""
import pytest
from pathlib import Path

from app.incremental.detector import (
    ChangeType,
    DocumentChange,
    ChangeDetector,
    MetadataComparator,
)


@pytest.fixture
def detector():
    return ChangeDetector()


class TestChangeType:
    def test_enum_values(self):
        assert ChangeType.NEW == "new"
        assert ChangeType.UNCHANGED == "unchanged"
        assert ChangeType.MODIFIED == "modified"
        assert ChangeType.DELETED == "deleted"


class TestDocumentChange:
    def test_defaults(self):
        change = DocumentChange(document_id=1, change_type=ChangeType.NEW)
        assert change.document_id == 1
        assert change.change_type == ChangeType.NEW
        assert change.changed_chunks == []
        assert change.unchanged_chunks == []
        assert change.metadata_changed is False
        assert change.timestamp is not None


class TestChangeDetectorDetectRename:
    def test_rename_detected(self, detector):
        result = detector._detect_rename(
            "/docs/old_name.pdf", "/docs/new_name.pdf", "abc123"
        )
        assert result is True

    def test_no_rename_same_name(self, detector):
        result = detector._detect_rename(
            "/docs/file.pdf", "/docs/file.pdf", "abc123"
        )
        assert result is False

    def test_no_rename_different_dir(self, detector):
        result = detector._detect_rename(
            "/dir1/file.pdf", "/dir2/file.pdf", "abc123"
        )
        assert result is False


class TestChangeDetectorDetectMove:
    def test_move_detected(self, detector):
        result = detector._detect_move("/dir1/file.pdf", "/dir2/file.pdf")
        assert result is True

    def test_no_move_same_dir(self, detector):
        result = detector._detect_move("/dir/file.pdf", "/dir/file.pdf")
        assert result is False

    def test_no_move_different_name(self, detector):
        result = detector._detect_move("/dir/file1.pdf", "/dir/file2.pdf")
        assert result is False


class TestChangeDetectorCompareChunks:
    def test_all_unchanged(self, detector):
        from app.incremental.hashing import calculate_chunk_hash
        chunks = ["chunk1", "chunk2"]
        hashes = [calculate_chunk_hash(c, i) for i, c in enumerate(chunks)]
        result = detector._compare_chunks(chunks, hashes, chunks)
        assert result["unchanged_chunks"] == [0, 1]
        assert result["changed_chunks"] == []
        assert result["new_chunks"] == []

    def test_all_changed(self, detector):
        old = ["old1", "old2"]
        new = ["new1", "new2"]
        result = detector._compare_chunks(old, [], new)
        assert result["changed_chunks"] == [0, 1]

    def test_new_chunks_added(self, detector):
        old = ["chunk1"]
        new = ["chunk1", "chunk2", "chunk3"]
        result = detector._compare_chunks(old, [], new)
        assert 1 in result["new_chunks"]
        assert 2 in result["new_chunks"]

    def test_chunks_removed(self, detector):
        old = ["chunk1", "chunk2", "chunk3"]
        new = ["chunk1"]
        result = detector._compare_chunks(old, [], new)
        assert len(result["removed_chunks"]) >= 1


class TestMetadataComparator:
    def test_no_changes(self):
        old = {"title": "Test", "author": "John"}
        new = {"title": "Test", "author": "John"}
        changed, changes = MetadataComparator.compare(old, new)
        assert changed is False
        assert changes == {}

    def test_with_changes(self):
        old = {"title": "Old", "author": "John"}
        new = {"title": "New", "author": "John"}
        changed, changes = MetadataComparator.compare(old, new)
        assert changed is True
        assert "title" in changes
        assert changes["title"]["old"] == "Old"
        assert changes["title"]["new"] == "New"

    def test_specific_fields(self):
        old = {"title": "Old", "author": "John", "tags": ["a"]}
        new = {"title": "New", "author": "Jane", "tags": ["b"]}
        changed, changes = MetadataComparator.compare(old, new, ["title"])
        assert changed is True
        assert "title" in changes
        assert "author" not in changes

    def test_empty_metadata(self):
        changed, changes = MetadataComparator.compare({}, {})
        assert changed is False