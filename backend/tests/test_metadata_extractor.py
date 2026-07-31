"""Behavioral tests for hybrid/metadata.py pure-logic functions."""
import pytest
from datetime import datetime

from app.hybrid.metadata import MetadataExtractor


@pytest.fixture
def extractor():
    return MetadataExtractor()


@pytest.fixture
def sample_doc():
    return {
        "id": "doc1",
        "title": "Python Programming Guide",
        "author": "John Doe",
        "description": "A comprehensive guide to Python programming",
        "tags": ["python", "programming"],
        "categories": ["tech", "education"],
        "content": "Python is a versatile programming language " * 10,
        "filename": "guide.pdf",
        "url": "https://example.com/guide",
        "language": "en",
    }


class TestExtract:
    def test_extract_basic(self, extractor, sample_doc):
        meta = extractor.extract(sample_doc)
        assert meta["id"] == "doc1"
        assert meta["title"] == "Python Programming Guide"
        assert meta["author"] == "John Doe"
        assert meta["tags"] == ["python", "programming"]

    def test_extract_with_snippet_fallback(self, extractor):
        doc = {"title": "Test", "snippet": "A snippet"}
        meta = extractor.extract(doc)
        assert meta["description"] == "A snippet"

    def test_extract_custom_fields(self, extractor, sample_doc):
        sample_doc["custom_field"] = "custom_value"
        meta = extractor.extract(sample_doc)
        assert "custom_field" in meta["custom"]

    def test_extract_has_embedding(self, extractor):
        doc = {"title": "Test", "embedding": [0.1, 0.2]}
        meta = extractor.extract(doc)
        assert meta["has_embedding"] is True

    def test_extract_no_embedding(self, extractor, sample_doc):
        meta = extractor.extract(sample_doc)
        assert meta["has_embedding"] is False

    def test_extract_quality_score(self, extractor, sample_doc):
        meta = extractor.extract(sample_doc)
        assert 0.0 <= meta["quality_score"] <= 1.0
        assert meta["quality_score"] > 0.5


class TestParseDate:
    def test_parse_string_date(self, extractor):
        assert extractor._parse_date("2024-01-01") == "2024-01-01"

    def test_parse_none(self, extractor):
        assert extractor._parse_date(None) is None

    def test_parse_datetime_obj(self, extractor):
        dt = datetime(2024, 1, 1)
        result = extractor._parse_date(dt)
        assert "2024-01-01" in result

    def test_parse_invalid_type(self, extractor):
        assert extractor._parse_date(12345) is None


class TestExtractFileType:
    def test_explicit_file_type(self, extractor):
        doc = {"file_type": "pdf"}
        assert extractor._extract_file_type(doc) == "pdf"

    def test_from_filename(self, extractor):
        doc = {"filename": "document.docx"}
        assert extractor._extract_file_type(doc) == "docx"

    def test_from_content_type(self, extractor):
        doc = {"content_type": "application/pdf"}
        assert extractor._extract_file_type(doc) == "pdf"

    def test_no_file_type(self, extractor):
        doc = {}
        assert extractor._extract_file_type(doc) is None


class TestCountWords:
    def test_with_content(self, extractor):
        doc = {"content": "one two three four"}
        assert extractor._count_words(doc) == 4

    def test_with_snippet_fallback(self, extractor):
        doc = {"snippet": "one two three"}
        assert extractor._count_words(doc) == 3

    def test_empty(self, extractor):
        assert extractor._count_words({}) == 0


class TestCalculateQualityScore:
    def test_full_metadata(self, extractor):
        meta = {
            "title": "A long enough title",
            "author": "Author",
            "description": "A long enough description",
            "tags": ["tag1"],
            "categories": ["cat1"],
            "word_count": 100,
        }
        score = extractor._calculate_quality_score(meta)
        assert score == 1.0

    def test_empty_metadata(self, extractor):
        score = extractor._calculate_quality_score({})
        assert score == 0.0

    def test_partial_metadata(self, extractor):
        meta = {"title": "Short", "word_count": 10}
        score = extractor._calculate_quality_score(meta)
        assert 0.0 < score < 0.5


class TestBatchExtract:
    def test_batch(self, extractor, sample_doc):
        docs = [sample_doc, {"title": "Doc2"}]
        results = extractor.batch_extract(docs)
        assert len(results) == 2
        assert results[0]["id"] == "doc1"

    def test_empty_batch(self, extractor):
        assert extractor.batch_extract([]) == []


class TestGetMetadataSummary:
    def test_empty(self, extractor):
        assert extractor.get_metadata_summary([]) == {}

    def test_with_metadata(self, extractor, sample_doc):
        meta_list = [extractor.extract(sample_doc), extractor.extract({"title": "Doc2"})]
        summary = extractor.get_metadata_summary(meta_list)
        assert summary["total_documents"] == 2
        assert summary["has_title"] == 2
        assert "average_quality_score" in summary
        assert "title_percentage" in summary