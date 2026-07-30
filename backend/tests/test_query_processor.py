"""Behavioral tests for query_processor.py and query understanding pipeline."""
import pytest
from unittest.mock import AsyncMock, patch

from app.search.query_understanding.query_processor import QueryProcessor


@pytest.fixture
def processor():
    return QueryProcessor()


class TestQueryProcessor:
    @pytest.mark.asyncio
    async def test_process_empty_query(self, processor):
        result = await processor.process("")
        assert result["original"] == ""
        assert result["tokens"] == []
        assert result["entities"] == []

    @pytest.mark.asyncio
    async def test_process_whitespace_query(self, processor):
        result = await processor.process("   ")
        assert result["original"] == "   "
        assert result["tokens"] == []

    @pytest.mark.asyncio
    async def test_process_basic_query(self, processor):
        result = await processor.process("python tutorial")
        assert result["original"] == "python tutorial"
        assert "language" in result
        assert "tokens" in result
        assert "entities" in result
        assert "intent" in result

    @pytest.mark.asyncio
    async def test_process_caching(self, processor):
        result1 = await processor.process("python tutorial")
        result2 = await processor.process("python tutorial")
        assert result1 is result2  # Same cached object

    @pytest.mark.asyncio
    async def test_process_for_search(self, processor):
        result = await processor.process_for_search("python tutorial")
        assert result["original"] == "python tutorial"

    @pytest.mark.asyncio
    async def test_process_for_indexing(self, processor):
        result = await processor.process_for_indexing("python tutorial")
        assert result["original"] == "python tutorial"

    def test_clear_cache(self, processor):
        processor._cache["test"] = "value"
        processor.clear_cache()
        assert len(processor._cache) == 0

    @pytest.mark.asyncio
    async def test_process_with_language(self, processor):
        result = await processor.process("python tutorial", language="fr")
        assert result["language"] == "fr"

    @pytest.mark.asyncio
    async def test_process_disable_synonyms(self, processor):
        result = await processor.process("python tutorial", enable_synonyms=False)
        assert "synonyms_added" in result

    @pytest.mark.asyncio
    async def test_process_disable_stemming(self, processor):
        result = await processor.process("python tutorial", enable_stemming=False)
        assert "stemmed_tokens" in result

    @pytest.mark.asyncio
    async def test_process_enable_stopwords(self, processor):
        result = await processor.process("the python tutorial", enable_stopwords=True)
        assert "tokens" in result