"""AI service unit tests."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas import SynthesizeResponse
from app.services.ai import get_ai_answer, synthesize_snippets


@pytest.mark.asyncio
async def test_synthesize_fallback_without_openai():
    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        result = await synthesize_snippets(
            "python programming",
            ["Python is a language.", "It is popular."],
        )
    assert isinstance(result, SynthesizeResponse)
    assert len(result.synthesis) > 0


@pytest.mark.asyncio
async def test_get_ai_answer_duckduckgo_fallback():
    with patch("app.services.ai.settings") as mock_settings, patch(
        "app.services.ai.ai_duckduckgo",
        new=AsyncMock(return_value="Fallback answer"),
    ):
        mock_settings.openai_api_key = ""
        answer = await get_ai_answer("what is python")
    assert answer == "Fallback answer"


@pytest.mark.asyncio
async def test_get_ai_answer_openai_success():
    with patch("app.services.ai.settings") as mock_settings, patch(
        "app.services.ai.ai_openai",
        new=AsyncMock(return_value="OpenAI answer"),
    ):
        mock_settings.openai_api_key = "sk-test"
        answer = await get_ai_answer("test query")
    assert answer == "OpenAI answer"
