"""Tests for AI provider base interface.

Focus areas:
- Abstract base class compliance
- Provider interface methods
- Streaming interface
- Provider implementations
"""

from abc import ABC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.providers.ai.base import AIProvider


class TestAIProviderAbstract:
    """Test AIProvider abstract base class."""

    def test_is_abstract_class(self):
        """AIProvider should be an abstract base class."""
        assert issubclass(AIProvider, ABC)

    def test_cannot_instantiate_abstract(self):
        """Should not be able to instantiate abstract base class."""
        with pytest.raises(TypeError):
            AIProvider()

    def test_has_name_attribute(self):
        """Should have name class attribute."""
        assert hasattr(AIProvider, "name")
        assert AIProvider.name == "base"


class TestAIProviderMethods:
    """Test AIProvider abstract methods."""

    def test_complete_is_abstract(self):
        """complete method should be abstract."""
        import inspect

        # Get the complete method
        complete_method = getattr(AIProvider, "complete")

        # Check if it's an abstract method
        assert getattr(complete_method, "__isabstractmethod__", False) is True

    def test_stream_is_abstract(self):
        """stream method should be abstract."""
        import inspect

        # Get the stream method
        stream_method = getattr(AIProvider, "stream")

        # Check if it's an abstract method
        assert getattr(stream_method, "__isabstractmethod__", False) is True


class TestAIProviderImplementation:
    """Test concrete AIProvider implementations."""

    @pytest_asyncio.fixture
    def mock_provider(self):
        """Create a concrete provider for testing."""

        class TestProvider(AIProvider):
            name = "test"

            async def complete(self, prompt: str, system: str | None = None) -> str | None:
                if prompt == "error":
                    raise ValueError("Test error")
                return f"Response to: {prompt}"

        return TestProvider()

    @pytest_asyncio.fixture
    def streaming_provider(self):
        """Create a streaming provider for testing."""

        class StreamingProvider(AIProvider):
            name = "streaming"

            async def complete(self, prompt: str, system: str | None = None) -> str | None:
                return f"Complete: {prompt}"

            async def stream(self, prompt: str, system: str | None = None):
                for i, char in enumerate(prompt):
                    yield f"char_{i}: {char}"

        return StreamingProvider()

    @pytest.mark.asyncio
    async def test_complete_success(self, mock_provider):
        """Should complete successfully."""
        result = await mock_provider.complete("Hello")
        assert result == "Response to: Hello"

    @pytest.mark.asyncio
    async def test_complete_with_system_prompt(self, mock_provider):
        """Should handle system prompt."""
        result = await mock_provider.complete("Hello", system="You are a helpful assistant")
        assert result == "Response to: Hello"

    @pytest.mark.asyncio
    async def test_complete_error(self, mock_provider):
        """Should propagate errors from implementation."""
        with pytest.raises(ValueError, match="Test error"):
            await mock_provider.complete("error")

    @pytest.mark.asyncio
    async def test_complete_returns_none(self, mock_provider):
        """Should handle None return."""
        # Modify provider to return None
        class NoneProvider(AIProvider):
            name = "none"

            async def complete(self, prompt: str, system: str | None = None) -> str | None:
                return None

        none_provider = NoneProvider()
        result = await none_provider.complete("test")
        assert result is None

    @pytest.mark.asyncio
    async def test_stream_success(self, streaming_provider):
        """Should stream content."""
        chunks = []
        async for chunk in streaming_provider.stream("Hello"):
            chunks.append(chunk)

        assert len(chunks) == 5  # H, e, l, l, o
        assert chunks[0] == "char_0: H"
        assert chunks[4] == "char_4: o"

    @pytest.mark.asyncio
    async def test_stream_with_system_prompt(self, streaming_provider):
        """Should handle system prompt in streaming."""
        chunks = []
        async for chunk in streaming_provider.stream("Hi", system="Be concise"):
            chunks.append(chunk)

        assert len(chunks) == 2  # H, i

    @pytest.mark.asyncio
    async def test_stream_empty_prompt(self, streaming_provider):
        """Should handle empty prompt."""
        chunks = []
        async for chunk in streaming_provider.stream("", system="test"):
            chunks.append(chunk)

        assert len(chunks) == 0


class TestAIProviderRouterIntegration:
    """Test AIProvider with router."""

    @pytest_asyncio.fixture
    def mock_router(self):
        """Create a mock router for testing."""
        with patch("app.providers.ai.router.get_settings") as mock_settings:
            mock_settings.return_value.ai_provider = "auto"
            mock_settings.return_value.openai_api_key = ""
            from app.providers.ai.router import AIProviderRouter

            return AIProviderRouter()

    @pytest.mark.asyncio
    async def test_ordered_providers_auto(self, mock_router):
        """Should order providers correctly for auto mode."""
        providers = mock_router._ordered_providers()
        assert "ollama" in providers
        assert "ollama_free" in providers
        assert "gguf" in providers

    @pytest.mark.asyncio
    async def test_ordered_providers_openai(self, mock_router):
        """Should prioritize OpenAI when configured."""
        with patch("app.providers.ai.router.get_settings") as mock_settings:
            mock_settings.return_value.ai_provider = "openai"
            mock_settings.return_value.openai_api_key = "test-key"
            from app.providers.ai.router import AIProviderRouter

            router = AIProviderRouter()
            providers = router._ordered_providers()
            assert providers[0] == "openai"

    @pytest.mark.asyncio
    async def test_complete_fallback(self, mock_router):
        """Should fallback through providers."""
        with patch("app.providers.ai.router.get_settings") as mock_settings:
            mock_settings.return_value.ai_provider = "auto"
            from app.providers.ai.router import AIProviderRouter

            router = AIProviderRouter()

            # Test with no providers returning results
            result, provider_name = await router.complete("test")
            assert provider_name == "none"
            assert result is None

    @pytest.mark.asyncio
    async def test_complete_success_first_provider(self, mock_router):
        """Should use first provider that succeeds."""
        with patch("app.providers.ai.router.get_settings") as mock_settings:
            mock_settings.return_value.ai_provider = "ollama"
            from app.providers.ai.router import AIProviderRouter
            from app.providers.ai.ollama import OllamaProvider

            # Mock provider response
            with patch.object(OllamaProvider, "complete", new_callable=AsyncMock) as mock_complete:
                mock_complete.return_value = "Test response"
                router = AIProviderRouter()

                result, provider_name = await router.complete("test")
                assert result == "Test response"
                assert provider_name == "ollama"

    @pytest.mark.asyncio
    async def test_stream_fallback(self, mock_router):
        """Should fallback through streaming providers."""
        with patch("app.providers.ai.router.get_settings") as mock_settings:
            mock_settings.return_value.ai_provider = "auto"
            from app.providers.ai.router import AIProviderRouter

            router = AIProviderRouter()

            chunks = []
            async for chunk in router.stream("test"):
                chunks.append(chunk)

            # Should return complete response as fallback
            assert len(chunks) == 1


class TestProviderNameAttribute:
    """Test provider name attributes."""

    @pytest.mark.asyncio
    async def test_provider_name_default(self):
        """Should have base name by default."""
        from app.providers.ai.base import AIProvider

        # Check class attribute
        assert AIProvider.name == "base"

    @pytest.mark.asyncio
    async def test_provider_name_override(self):
        """Should allow name override in subclasses."""
        from app.providers.ai.base import AIProvider

        class CustomProvider(AIProvider):
            name = "custom"

            async def complete(self, prompt: str, system: str | None = None) -> str | None:
                return "test"

        assert CustomProvider.name == "custom"