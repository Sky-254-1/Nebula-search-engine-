"""Behavioral tests for search/intelligence.py pure-logic functions."""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from app.search.intelligence import (
    SearchContext,
    QuerySuggestion,
    SpellCorrector,
    QueryExpander,
    AutocompleteEngine,
    PersonalizationEngine,
)


class TestSearchContext:
    def test_default_timestamp(self):
        ctx = SearchContext(user_id=1, query="test")
        assert ctx.timestamp is not None
        assert isinstance(ctx.timestamp, datetime)

    def test_custom_timestamp(self):
        ts = datetime(2024, 1, 1)
        ctx = SearchContext(user_id=1, query="test", timestamp=ts)
        assert ctx.timestamp == ts

    def test_defaults(self):
        ctx = SearchContext(user_id=1, query="test")
        assert ctx.language == "en"
        assert ctx.location is None
        assert ctx.device_type is None


class TestQuerySuggestion:
    def test_creation(self):
        s = QuerySuggestion(suggestion="test", score=0.9, source="history")
        assert s.suggestion == "test"
        assert s.score == 0.9
        assert s.source == "history"
        assert s.metadata is None

    def test_with_metadata(self):
        s = QuerySuggestion(suggestion="test", score=0.9, source="history", metadata={"key": "val"})
        assert s.metadata == {"key": "val"}


class TestSpellCorrector:
    def test_edit_distance_one(self):
        sc = SpellCorrector()
        result = sc._edit_distance_one("test")
        assert isinstance(result, set)
        assert len(result) > 0
        assert "tes" in result  # deletion
        assert "tets" in result  # transpose

    def test_known_words(self):
        sc = SpellCorrector()
        sc.word_freq = {"test": 1, "best": 2}
        result = sc._known({"test", "xyz", "best"})
        assert result == {"test", "best"}

    @pytest.mark.asyncio
    async def test_correct_word_known(self):
        sc = SpellCorrector()
        sc.word_freq = {"test": 1}
        sc.loaded = True
        result = await sc.correct_word("test")
        assert result == "test"

    @pytest.mark.asyncio
    async def test_correct_word_correction(self):
        sc = SpellCorrector()
        sc.word_freq = {"test": 10, "best": 5}
        sc.loaded = True
        result = await sc.correct_word("tset")
        assert result in ("test", "best")

    @pytest.mark.asyncio
    async def test_correct_word_no_correction(self):
        sc = SpellCorrector()
        sc.word_freq = {"test": 1}
        sc.loaded = True
        result = await sc.correct_word("xyzq")
        assert result == "xyzq"

    @pytest.mark.asyncio
    async def test_correct_query(self):
        sc = SpellCorrector()
        sc.word_freq = {"the": 10, "test": 5}
        sc.loaded = True
        corrected, was_corrected = await sc.correct_query("the test")
        assert isinstance(corrected, str)
        assert isinstance(was_corrected, bool)


class TestQueryExpander:
    @pytest.mark.asyncio
    async def test_expand_with_synonym(self):
        expander = QueryExpander()
        result = await expander.expand("search for data")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_expand_no_synonyms(self):
        expander = QueryExpander()
        result = await expander.expand("xyzabc")
        assert result == []

    @pytest.mark.asyncio
    async def test_add_synonym(self):
        expander = QueryExpander()
        await expander.add_synonym("custom", ["personal", "unique"])
        assert "custom" in expander.synonyms
        assert expander.synonyms["custom"] == ["personal", "unique"]

    @pytest.mark.asyncio
    async def test_expand_max_expansions(self):
        expander = QueryExpander()
        result = await expander.expand("search", max_expansions=2)
        assert len(result) <= 2


class TestAutocompleteEngine:
    def test_insert(self):
        engine = AutocompleteEngine()
        engine._insert("test", 1.0)
        assert "t" in engine.trie
        assert "e" in engine.trie["t"]

    def test_search_prefix_found(self):
        engine = AutocompleteEngine()
        engine._insert("test", 1.0)
        engine._insert("testing", 2.0)
        results = engine._search_prefix("test")
        assert len(results) == 2
        words = [r[0] for r in results]
        assert "test" in words
        assert "testing" in words

    def test_search_prefix_not_found(self):
        engine = AutocompleteEngine()
        results = engine._search_prefix("xyz")
        assert results == []

    @pytest.mark.asyncio
    async def test_suggest_short_prefix(self):
        engine = AutocompleteEngine()
        result = await engine.suggest("a")
        assert result == []

    @pytest.mark.asyncio
    async def test_suggest_empty(self):
        engine = AutocompleteEngine()
        result = await engine.suggest("")
        assert result == []

    @pytest.mark.asyncio
    async def test_train_from_queries(self):
        engine = AutocompleteEngine()
        await engine.train_from_queries([("python tutorial", 5), ("java guide", 3)])
        results = engine._search_prefix("python")
        assert len(results) == 1
        assert results[0][0] == "python tutorial"


class TestPersonalizationEngine:
    @pytest.mark.asyncio
    async def test_personalize_results_no_profile(self):
        engine = PersonalizationEngine()
        results = [{"title": "Test", "snippet": "Test", "url": "https://test.com"}]
        with patch.object(engine, "get_user_profile", new_callable=AsyncMock) as mock:
            mock.return_value = {"interests": [], "preferred_sources": []}
            personalized = await engine.personalize_results(1, "test", results)
            assert len(personalized) == 1

    @pytest.mark.asyncio
    async def test_personalize_results_with_interests(self):
        engine = PersonalizationEngine()
        results = [
            {"title": "Python guide", "snippet": "Learn Python", "url": "https://a.com"},
            {"title": "Java guide", "snippet": "Learn Java", "url": "https://b.com"},
        ]
        with patch.object(engine, "get_user_profile", new_callable=AsyncMock) as mock:
            mock.return_value = {"interests": ["python"], "preferred_sources": []}
            personalized = await engine.personalize_results(1, "python", results)
            assert personalized[0]["title"] == "Python guide"

    @pytest.mark.asyncio
    async def test_personalize_results_with_preferred_sources(self):
        engine = PersonalizationEngine()
        results = [
            {"title": "Guide 1", "snippet": "Test", "url": "https://preferred.com"},
            {"title": "Guide 2", "snippet": "Test", "url": "https://other.com"},
        ]
        with patch.object(engine, "get_user_profile", new_callable=AsyncMock) as mock:
            mock.return_value = {"interests": [], "preferred_sources": ["preferred.com"]}
            personalized = await engine.personalize_results(1, "test", results)
            assert personalized[0]["url"] == "https://preferred.com"