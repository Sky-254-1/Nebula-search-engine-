"""Tests for the suggestion service layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSuggestionService:
    """Tests for SuggestionService."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.fetchall = AsyncMock(return_value=[])
        return db

    @pytest.fixture
    def mock_repo(self):
        repo = MagicMock()
        repo.record_search = AsyncMock()
        repo.increment_trending_query = AsyncMock()
        repo.get_related_searches = AsyncMock(return_value=[])
        repo.get_user_search_history = AsyncMock(return_value=[])
        repo.get_session_searches = AsyncMock(return_value=[])
        repo.increment_related_search_clicks = AsyncMock()
        repo.update_trending_metrics = AsyncMock(return_value=5)
        repo.rebuild_related_searches = AsyncMock(return_value=10)
        return repo

    @pytest.fixture
    def service(self, mock_db, mock_repo):
        with patch(
            "app.services.suggestion_service.SuggestionRepository",
            return_value=mock_repo,
        ):
            from app.services.suggestion_service import SuggestionService
            svc = SuggestionService(mock_db)
            svc._repo = mock_repo
            return svc

    @pytest.mark.asyncio
    async def test_get_suggestions_cache_hit(self, service, mock_db):
        """Cache hit returns cached data immediately."""
        from app.services.cache import cache_service
        cached_data = {
            "query": "test",
            "suggestions": [{"text": "test query", "type": "trending", "score": 0.9}],
            "cache_hit": True,
            "latency_ms": 0,
        }
        await cache_service.set("suggestions:test", cached_data, ttl=30)

        result = await service.get_suggestions("test")
        assert result["cache_hit"] is True
        assert result["query"] == "test"
        assert len(result["suggestions"]) == 1

    @pytest.mark.asyncio
    async def test_get_suggestions_cache_miss(self, service, mock_db):
        """Cache miss gathers from all sources."""
        from app.services.cache import cache_service
        await cache_service.delete("suggestions:test")
        result = await service.get_suggestions("test")
        assert result["cache_hit"] is False
        assert result["query"] == "test"
        assert isinstance(result["suggestions"], list)
        assert "latency_ms" in result

    @pytest.mark.asyncio
    async def test_get_suggestions_with_user_id(self, service, mock_repo):
        """Authenticated user gets personalized suggestions included."""
        from app.services.cache import cache_service
        await cache_service.delete("suggestions:test")
        mock_repo.get_user_search_history.return_value = [
            {"query": "testing framework"},
            {"query": "test driven development"},
        ]
        result = await service.get_suggestions("test", user_id=42)
        assert result["cache_hit"] is False

    @pytest.mark.asyncio
    async def test_get_suggestions_records_search_with_session(self, service, mock_repo):
        """Search is recorded when session_id is provided."""
        # Clear cache so we get a cache miss and the record_search path runs
        from app.services.cache import cache_service
        await cache_service.delete("suggestions:test")
        result = await service.get_suggestions("test", session_id="sess-1")
        mock_repo.record_search.assert_called_once_with(
            query="test", user_id=None, session_id="sess-1"
        )

    @pytest.mark.asyncio
    async def test_get_suggestions_empty_query(self, service, mock_db):
        """Empty query returns empty suggestions gracefully."""
        mock_db.fetchall.return_value = []
        result = await service.get_suggestions("")
        assert isinstance(result["suggestions"], list)

    @pytest.mark.asyncio
    async def test_get_trending_suggestions(self, service, mock_db):
        """Trending suggestions are fetched and cached."""
        mock_db.fetchall.return_value = [
            {"suggestion": "nebula search", "score": 85.0, "frequency": 12, "last_used": "2026-01-01"},
        ]
        result = await service.get_trending_suggestions("nebula")
        assert len(result) == 1
        assert result[0]["text"] == "nebula search"
        assert result[0]["type"] == "trending"

    @pytest.mark.asyncio
    async def test_get_related_suggestions(self, service, mock_repo):
        """Related suggestions are fetched from repo."""
        mock_repo.get_related_searches.return_value = [
            {"related_query": "ai search", "score": 8.0, "co_occurrence_count": 5, "click_count": 3},
        ]
        result = await service.get_related_suggestions("search")
        assert len(result) == 1
        assert result[0]["text"] == "ai search"
        assert result[0]["type"] == "related"

    @pytest.mark.asyncio
    async def test_record_search_empty_query(self, service, mock_repo):
        """Empty query is rejected without calling repo."""
        await service.record_search("", user_id=1, session_id="sess-1")
        mock_repo.record_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_search_with_click(self, service, mock_repo):
        """Click-through triggers related search update."""
        mock_repo.get_session_searches.return_value = ["previous query"]
        await service.record_search(
            "test query", user_id=1, session_id="sess-1", clicked_result_id=42
        )
        mock_repo.record_search.assert_called_once()
        mock_repo.increment_trending_query.assert_called_once_with("test query")
        mock_repo.increment_related_search_clicks.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_trending(self, service, mock_repo):
        """Refresh trending returns row count and duration."""
        result = await service.refresh_trending()
        assert result["rows_updated"] == 5
        assert "duration_ms" in result
        mock_repo.update_trending_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_related_searches(self, service, mock_repo):
        """Refresh related returns relationship count."""
        result = await service.refresh_related_searches()
        assert result["relationships"] == 10
        assert "duration_ms" in result
        mock_repo.rebuild_related_searches.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_semantic_suggestions(self, service):
        """Refresh semantic returns count (placeholder returns 0)."""
        result = await service.refresh_semantic_suggestions()
        assert result["suggestions"] == 0
        assert "duration_ms" in result

    @pytest.mark.asyncio
    async def test_rank_and_deduplicate_removes_duplicates(self, service):
        """Duplicate suggestions are deduplicated, keeping higher score."""
        suggestions = [
            {"text": "test query", "type": "trending", "score": 0.5},
            {"text": "Test Query", "type": "semantic", "score": 0.9},
        ]
        result = await service._rank_and_deduplicate(suggestions, limit=5)
        assert len(result) == 1
        assert result[0]["score"] == 1.0  # Normalized

    @pytest.mark.asyncio
    async def test_rank_and_deduplicate_empty(self, service):
        """Empty suggestions list returns empty."""
        result = await service._rank_and_deduplicate([], limit=5)
        assert result == []

    @pytest.mark.asyncio
    async def test_rank_and_deduplicate_respects_limit(self, service):
        """Result is limited to specified count."""
        suggestions = [
            {"text": f"query {i}", "type": "trending", "score": float(i)}
            for i in range(10)
        ]
        result = await service._rank_and_deduplicate(suggestions, limit=3)
        assert len(result) == 3