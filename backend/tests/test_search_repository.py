"""Tests for backend/app/database/repositories/search.py.

Coverage areas:
- Search log operations (log_search, recent_for_user)
- Query analytics (count_all)
- Edge cases and error handling
"""

import pytest
from unittest.mock import AsyncMock

from app.database.repositories.search import SearchRepository


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
        self.fetchall_queries = []
        self.fetchone_queries = []
        self._rows_by_query = {}

    async def execute(self, sql, args=None):
        self.executed_queries.append((sql, args))
        return FakeCursor()

    async def commit(self):
        self.committed = True

    async def fetchone(self, sql, args=None):
        query_key = (sql, tuple(args) if args else ())
        self.fetchone_queries.append((sql, args))
        rows = self._rows_by_query.get(query_key, [{}])
        return rows[0] if rows else None

    async def fetchall(self, sql, args=None):
        query_key = (sql, tuple(args) if args else ())
        self.fetchall_queries.append((sql, args))
        return list(self._rows_by_query.get(query_key, []))


@pytest.fixture
def repo():
    db = FakeDB()
    return SearchRepository(db)


class TestSearchLogging:
    """Test search logging operations."""

    @pytest.mark.asyncio
    async def test_log_search_with_user(self, repo):
        """Should log search with authenticated user."""
        await repo.log_search(
            user_id=1,
            query="test query",
            backend="unified",
            results_count=5,
        )
        assert repo._db.committed is True
        assert any("INSERT INTO search_logs" in q[0] for q in repo._db.executed_queries)

    @pytest.mark.asyncio
    async def test_log_search_without_user(self, repo):
        """Should log search without user (anonymous)."""
        await repo.log_search(
            user_id=None,
            query="anonymous query",
            backend="bm25",
            results_count=0,
        )
        assert repo._db.committed is True
        assert any("INSERT INTO search_logs" in q[0] for q in repo._db.executed_queries)

    @pytest.mark.asyncio
    async def test_log_search_empty_query(self, repo):
        """Should log search with empty query."""
        await repo.log_search(
            user_id=1,
            query="",
            backend="semantic",
            results_count=3,
        )
        assert repo._db.committed is True

    @pytest.mark.asyncio
    async def test_log_search_no_results(self, repo):
        """Should log search with zero results."""
        await repo.log_search(
            user_id=1,
            query="no results query",
            backend="unified",
            results_count=0,
        )
        assert repo._db.committed is True

    @pytest.mark.asyncio
    async def test_log_search_high_results(self, repo):
        """Should log search with many results."""
        await repo.log_search(
            user_id=1,
            query="broad query",
            backend="unified",
            results_count=1000,
        )
        assert repo._db.committed is True


class TestRecentSearches:
    """Test recent search retrieval."""

    @pytest.mark.asyncio
    async def test_recent_for_user(self, repo):
        """Should retrieve recent searches for user."""
        repo._db._rows_by_query[("SELECT query, backend, results_count, searched_at FROM search_logs "
            "WHERE user_id = ? ORDER BY searched_at DESC LIMIT ?",
            (1, 20))] = [
            {"query": "first", "backend": "unified", "results_count": 5, "searched_at": "2024-01-01T10:00:00"},
            {"query": "second", "backend": "bm25", "results_count": 3, "searched_at": "2024-01-01T09:00:00"},
        ]
        searches = await repo.recent_for_user(1, limit=20)
        assert len(searches) == 2
        assert searches[0]["query"] == "first"
        assert searches[0]["backend"] == "unified"

    @pytest.mark.asyncio
    async def test_recent_for_user_empty(self, repo):
        """Should return empty list when user has no searches."""
        repo._db._rows_by_query[("SELECT query, backend, results_count, searched_at FROM search_logs "
            "WHERE user_id = ? ORDER BY searched_at DESC LIMIT ?",
            (999, 20))] = []
        searches = await repo.recent_for_user(999, limit=20)
        assert searches == []

    @pytest.mark.asyncio
    async def test_recent_for_user_limit(self, repo):
        """Should respect limit parameter."""
        repo._db._rows_by_query[("SELECT query, backend, results_count, searched_at FROM search_logs "
            "WHERE user_id = ? ORDER BY searched_at DESC LIMIT ?",
            (1, 10))] = []
        await repo.recent_for_user(1, limit=10)
        executed = repo._db.fetchall_queries[-1]
        assert "LIMIT ?" in executed[0]

    @pytest.mark.asyncio
    async def test_recent_for_user_default_limit(self, repo):
        """Should use default limit of 20."""
        repo._db._rows_by_query[("SELECT query, backend, results_count, searched_at FROM search_logs "
            "WHERE user_id = ? ORDER BY searched_at DESC LIMIT ?",
            (1, 20))] = []
        await repo.recent_for_user(1)
        executed = repo._db.fetchall_queries[-1]
        # Check that 20 is in the args (position 1 of tuple)
        assert executed[1] is not None
        assert 20 in executed[1]

    @pytest.mark.asyncio
    async def test_recent_for_user_ordering(self, repo):
        """Should order by searched_at descending."""
        repo._db._rows_by_query[("SELECT query, backend, results_count, searched_at FROM search_logs "
            "WHERE user_id = ? ORDER BY searched_at DESC LIMIT ?",
            (1, 20))] = []
        await repo.recent_for_user(1, limit=20)
        executed = repo._db.fetchall_queries[-1]
        assert "ORDER BY searched_at DESC" in executed[0]


class TestAnalytics:
    """Test search analytics operations."""

    @pytest.mark.asyncio
    async def test_count_all(self, repo):
        """Should count total search logs."""
        repo._db._rows_by_query[("SELECT COUNT(*) as count FROM search_logs", ())] = [
            {"count": 1250}
        ]
        count = await repo.count_all()
        assert count == 1250

    @pytest.mark.asyncio
    async def test_count_all_empty(self, repo):
        """Should return 0 when no search logs."""
        repo._db._rows_by_query[("SELECT COUNT(*) as count FROM search_logs", ())] = [
            {"count": 0}
        ]
        count = await repo.count_all()
        assert count == 0

    @pytest.mark.asyncio
    async def test_count_all_zero_row(self, repo):
        """Should handle None count row."""
        repo._db._rows_by_query[("SELECT COUNT(*) as count FROM search_logs", ())] = []
        count = await repo.count_all()
        assert count == 0


class TestMultipleBackends:
    """Test search logging with different backends."""

    @pytest.mark.asyncio
    async def test_log_search_unified_backend(self, repo):
        """Should log search with unified backend."""
        await repo.log_search(1, "query", "unified", 5)
        assert repo._db.committed is True

    @pytest.mark.asyncio
    async def test_log_search_bm25_backend(self, repo):
        """Should log search with BM25 backend."""
        await repo.log_search(1, "query", "bm25", 3)
        assert repo._db.committed is True

    @pytest.mark.asyncio
    async def test_log_search_semantic_backend(self, repo):
        """Should log search with semantic backend."""
        await repo.log_search(1, "query", "semantic", 7)
        assert repo._db.committed is True


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_log_search_with_unicode_query(self, repo):
        """Should handle Unicode query characters."""
        unicode_query = "测试查询 🌟 日本語"
        await repo.log_search(
            user_id=1,
            query=unicode_query,
            backend="unified",
            results_count=5,
        )
        assert repo._db.committed is True

    @pytest.mark.asyncio
    async def test_log_search_with_special_characters(self, repo):
        """Should handle search with special characters."""
        special_query = 'query "with" (special) [chars] <html>'
        await repo.log_search(
            user_id=1,
            query=special_query,
            backend="unified",
            results_count=5,
        )
        assert repo._db.committed is True

    @pytest.mark.asyncio
    async def test_recent_with_empty_results(self, repo):
        """Should handle recent_for_user with empty results."""
        repo._db._rows_by_query[("SELECT query, backend, results_count, searched_at FROM search_logs "
            "WHERE user_id = ? ORDER BY searched_at DESC LIMIT ?",
            (1, 1))] = []
        searches = await repo.recent_for_user(1, limit=1)
        assert searches == []

    @pytest.mark.asyncio
    async def test_count_all_with_null(self, repo):
        """Should handle null count result."""
        repo._db._rows_by_query[("SELECT COUNT(*) as count FROM search_logs", ())] = [
            {"count": None}
        ]
        count = await repo.count_all()
        assert count == 0

    @pytest.mark.asyncio
    async def test_log_search_multiple_calls(self, repo):
        """Should handle multiple log_search calls."""
        for i in range(5):
            await repo.log_search(1, f"query{i}", "unified", i)
        assert repo._db.committed is True
        assert len([q for q in repo._db.executed_queries if "INSERT INTO search_logs" in q[0]]) == 5

    @pytest.mark.asyncio
    async def test_recent_for_user_large_limit(self, repo):
        """Should handle large limit parameter."""
        repo._db._rows_by_query[("SELECT query, backend, results_count, searched_at FROM search_logs "
            "WHERE user_id = ? ORDER BY searched_at DESC LIMIT ?",
            (1, 1000))] = []
        await repo.recent_for_user(1, limit=1000)
        executed = repo._db.fetchall_queries[-1]
        assert "LIMIT ?" in executed[0]