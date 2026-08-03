"""Behavioral tests for hybrid/dedupe.py pure-logic functions."""
import pytest
from app.hybrid.dedupe import Deduplicator


@pytest.fixture
def deduplicator():
    return Deduplicator()


@pytest.fixture
def sample_results():
    return [
        {"id": "1", "url": "https://example.com/page1", "title": "Python", "snippet": "Python tutorial", "score": 0.9},
        {"id": "2", "url": "https://example.com/page2", "title": "Java", "snippet": "Java guide", "score": 0.8},
        {"id": "3", "url": "https://example.com/page3", "title": "Ruby", "snippet": "Ruby on Rails", "score": 0.7},
    ]


class TestDeduplicate:
    def test_empty_results(self, deduplicator):
        assert deduplicator.deduplicate([]) == []

    def test_no_duplicates(self, deduplicator, sample_results):
        result = deduplicator.deduplicate(sample_results)
        assert len(result) == 3

    def test_duplicate_by_id(self, deduplicator):
        results = [
            {"id": "1", "url": "https://a.com", "title": "A", "snippet": "A", "score": 0.9},
            {"id": "1", "url": "https://b.com", "title": "B", "snippet": "B", "score": 0.8},
        ]
        result = deduplicator.deduplicate(results)
        assert len(result) == 1
        assert result[0]["score"] == 0.9

    def test_duplicate_by_url(self, deduplicator):
        results = [
            {"id": "1", "url": "https://example.com/page", "title": "A", "snippet": "A", "score": 0.9},
            {"id": "2", "url": "https://example.com/page", "title": "B", "snippet": "B", "score": 0.8},
        ]
        result = deduplicator.deduplicate(results)
        assert len(result) == 1

    def test_duplicate_by_content_hash(self, deduplicator):
        results = [
            {"id": "1", "url": "https://a.com", "title": "Same", "snippet": "Same content", "score": 0.9},
            {"id": "2", "url": "https://b.com", "title": "Same", "snippet": "Same content", "score": 0.8},
        ]
        result = deduplicator.deduplicate(results)
        assert len(result) == 1

    def test_duplicate_by_vector_id(self, deduplicator):
        results = [
            {"id": "1", "url": "https://a.com", "title": "A", "snippet": "A", "vector_id": "v1", "score": 0.9},
            {"id": "2", "url": "https://b.com", "title": "B", "snippet": "B", "vector_id": "v1", "score": 0.8},
        ]
        result = deduplicator.deduplicate(results)
        assert len(result) == 1

    def test_keeps_highest_score(self, deduplicator):
        results = [
            {"id": "1", "url": "https://a.com", "title": "A", "snippet": "A", "score": 0.5},
            {"id": "1", "url": "https://b.com", "title": "B", "snippet": "B", "score": 0.9},
        ]
        result = deduplicator.deduplicate(results)
        assert len(result) == 1
        assert result[0]["score"] == 0.9


class TestCanonicalizeUrl:
    def test_empty_url(self, deduplicator):
        assert deduplicator._canonicalize_url("") == ""

    def test_lowercase(self, deduplicator):
        assert deduplicator._canonicalize_url("HTTP://EXAMPLE.COM") == "http://example.com"

    def test_remove_trailing_slash(self, deduplicator):
        assert deduplicator._canonicalize_url("https://example.com/") == "https://example.com"

    def test_remove_utm_params(self, deduplicator):
        url = "https://example.com/page?utm_source=google&id=123"
        result = deduplicator._canonicalize_url(url)
        assert "utm_source" not in result
        assert "id=123" in result

    def test_remove_all_tracking_params(self, deduplicator):
        url = "https://example.com/page?utm_source=google&fbclid=abc&gclid=xyz"
        result = deduplicator._canonicalize_url(url)
        assert "?" not in result


class TestComputeContentHash:
    def test_hash_with_content(self, deduplicator):
        result = {"title": "Test", "content": "Some content here"}
        hash_val = deduplicator._compute_content_hash(result)
        assert len(hash_val) == 32

    def test_hash_with_snippet_fallback(self, deduplicator):
        result = {"title": "Test", "snippet": "Snippet content"}
        hash_val = deduplicator._compute_content_hash(result)
        assert len(hash_val) == 32

    def test_hash_empty(self, deduplicator):
        result = {}
        hash_val = deduplicator._compute_content_hash(result)
        assert len(hash_val) == 32


class TestFindDuplicates:
    def test_no_duplicates(self, deduplicator, sample_results):
        dups = deduplicator.find_duplicates(sample_results)
        assert len(dups) == 0

    def test_find_id_duplicate(self, deduplicator):
        results = [
            {"id": "1", "url": "https://a.com", "title": "A", "snippet": "A"},
            {"id": "1", "url": "https://b.com", "title": "B", "snippet": "B"},
        ]
        dups = deduplicator.find_duplicates(results)
        assert len(dups) == 1
        assert dups[0][2] == "document_id"

    def test_find_url_duplicate(self, deduplicator):
        results = [
            {"id": "1", "url": "https://example.com/page", "title": "A", "snippet": "A"},
            {"id": "2", "url": "https://example.com/page", "title": "B", "snippet": "B"},
        ]
        dups = deduplicator.find_duplicates(results)
        assert len(dups) == 1
        assert dups[0][2] == "url"

    def test_find_content_hash_duplicate(self, deduplicator):
        results = [
            {"id": "1", "url": "https://a.com", "title": "Same", "snippet": "Same content"},
            {"id": "2", "url": "https://b.com", "title": "Same", "snippet": "Same content"},
        ]
        dups = deduplicator.find_duplicates(results)
        assert len(dups) == 1
        assert dups[0][2] == "content_hash"


class TestMergeDuplicates:
    def test_empty(self, deduplicator):
        assert deduplicator.merge_duplicates([]) == []

    def test_no_duplicates(self, deduplicator, sample_results):
        result = deduplicator.merge_duplicates(sample_results)
        assert len(result) == 3

    def test_merge_combines_scores(self, deduplicator):
        results = [
            {"id": "1", "url": "https://a.com", "title": "A", "snippet": "A", "score": 0.5},
            {"id": "1", "url": "https://b.com", "title": "B", "snippet": "B", "score": 0.3},
        ]
        result = deduplicator.merge_duplicates(results)
        assert len(result) == 1
        assert result[0]["score"] == 0.8
        assert result[0]["merged_from"] == 2

    def test_merge_sorted_by_score(self, deduplicator):
        results = [
            {"id": "1", "url": "https://a.com", "title": "A", "snippet": "A", "score": 0.3},
            {"id": "2", "url": "https://b.com", "title": "B", "snippet": "B", "score": 0.9},
        ]
        result = deduplicator.merge_duplicates(results)
        assert result[0]["score"] == 0.9


class TestGetStatistics:
    def test_empty(self, deduplicator):
        assert deduplicator.get_statistics([]) == {}

    def test_with_results(self, deduplicator, sample_results):
        stats = deduplicator.get_statistics(sample_results)
        assert "total_results" in stats
        assert stats["total_results"] == 3
        assert "duplicate_pairs" in stats