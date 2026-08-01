"""Tests for backend/app/services/analytics_metrics.py.

Coverage areas:
- Prometheus metrics recording (search queries, clicks, CTR, latency)
- Cache hit/miss tracking
- Dashboard timing decorator
- Error handling when Prometheus not available
- Edge cases and error handling
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.analytics_metrics import (
    record_search_query,
    record_popular_query,
    record_zero_result_query,
    record_search_latency,
    time_dashboard_generation,
    record_analytics_cache_hit,
    record_analytics_cache_miss,
    record_click_event,
    record_ctr,
    AnalyticsMetricsRecorder,
    _HAS_PROMETHEUS,
)


class TestSearchQueryRecording:
    """Test search query metrics recording."""

    @pytest.mark.asyncio
    async def test_record_search_query_happy(self):
        """Should record search query when Prometheus available."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_search_queries_total") as mock_counter:
                record_search_query("hybrid", "unified")
                mock_counter.labels.assert_called_once_with(search_type="hybrid", backend="unified")
                mock_counter.labels.return_value.inc.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_search_query_disabled(self):
        """Should not raise when Prometheus not available."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", False):
            # Should not raise
            record_search_query("hybrid", "unified")

    @pytest.mark.asyncio
    async def test_record_search_query_with_error(self):
        """Should handle Prometheus recording errors gracefully."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_search_queries_total") as mock_counter:
                mock_counter.labels.return_value.inc.side_effect = Exception("Prometheus error")
                with patch("app.services.analytics_metrics.logger") as mock_logger:
                    record_search_query("hybrid", "unified")
                    mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_record_search_query_all_backends(self):
        """Should record search query for all backends."""
        backends = ["unified", "bm25", "semantic", "hybrid"]
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            for backend in backends:
                with patch("app.services.analytics_metrics._prom_search_queries_total") as mock_counter:
                    record_search_query("web", backend)
                    mock_counter.labels.assert_called_once_with(search_type="web", backend=backend)


class TestPopularQueryRecording:
    """Test popular query metrics recording."""

    @pytest.mark.asyncio
    async def test_record_popular_query_happy(self):
        """Should record popular query."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_popular_queries_total") as mock_counter:
                record_popular_query("python", 5)
                mock_counter.labels.assert_called_once_with(query="python")
                mock_counter.labels.return_value.inc.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_record_popular_query_disabled(self):
        """Should not raise when Prometheus disabled."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", False):
            record_popular_query("test", 1)

    @pytest.mark.asyncio
    async def test_record_popular_query_count(self):
        """Should handle count parameter."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_popular_queries_total") as mock_counter:
                record_popular_query("query", 100)
                mock_counter.labels.return_value.inc.assert_called_once_with(100)


class TestZeroResultQueryRecording:
    """Test zero-result query metrics recording."""

    @pytest.mark.asyncio
    async def test_record_zero_result_query_happy(self):
        """Should record zero-result query."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_zero_result_queries_total") as mock_counter:
                record_zero_result_query("nonexistent", 1)
                mock_counter.labels.assert_called_once_with(query="nonexistent")
                mock_counter.labels.return_value.inc.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_record_zero_result_query_disabled(self):
        """Should not raise when Prometheus disabled."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", False):
            record_zero_result_query("test", 1)


class TestSearchLatencyRecording:
    """Test search latency metrics recording."""

    @pytest.mark.asyncio
    async def test_record_search_latency_happy(self):
        """Should record search latency."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_average_search_latency") as mock_gauge:
                record_search_latency(0.5)
                mock_gauge.set.assert_called_once_with(0.5)

    @pytest.mark.asyncio
    async def test_record_search_latency_disabled(self):
        """Should not raise when Prometheus disabled."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", False):
            record_search_latency(0.5)

    @pytest.mark.asyncio
    async def test_record_search_latency_edge_cases(self):
        """Should handle edge cases for latency."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_average_search_latency") as mock_gauge:
                # Zero latency
                record_search_latency(0.0)
                mock_gauge.set.assert_called_once_with(0.0)


class TestDashboardGenerationTiming:
    """Test dashboard generation timing decorator."""

    @pytest.mark.asyncio
    async def test_time_dashboard_generation_happy(self):
        """Should time dashboard generation."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_dashboard_generation_time") as mock_histogram:
                mock_histogram.labels.return_value.observe = MagicMock()

                @time_dashboard_generation("24h")
                async def dummy_dashboard():
                    return {"data": "test"}

                result = await dummy_dashboard()
                assert result == {"data": "test"}
                mock_histogram.labels.assert_called_once_with(period="24h")

    @pytest.mark.asyncio
    async def test_time_dashboard_generation_disabled(self):
        """Should still execute function when Prometheus disabled."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", False):
            @time_dashboard_generation("24h")
            async def dummy_dashboard():
                return {"data": "test"}

            result = await dummy_dashboard()
            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_time_dashboard_generation_error(self):
        """Should handle function error and log it."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_dashboard_generation_time") as mock_histogram:
                mock_histogram.labels.return_value.observe = MagicMock()

                @time_dashboard_generation("24h")
                async def failing_dashboard():
                    raise ValueError("Test error")

                with patch("app.services.analytics_metrics.logger") as mock_logger:
                    with pytest.raises(ValueError):
                        await failing_dashboard()
                    mock_logger.exception.assert_called_once()


class TestCacheMetrics:
    """Test analytics cache hit/miss metrics."""

    @pytest.mark.asyncio
    async def test_record_analytics_cache_hit_happy(self):
        """Should record cache hit."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_analytics_cache_hits") as mock_counter:
                record_analytics_cache_hit()
                mock_counter.inc.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_analytics_cache_hit_disabled(self):
        """Should not raise when Prometheus disabled."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", False):
            record_analytics_cache_hit()

    @pytest.mark.asyncio
    async def test_record_analytics_cache_miss_happy(self):
        """Should record cache miss."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_analytics_cache_misses") as mock_counter:
                record_analytics_cache_miss()
                mock_counter.inc.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_analytics_cache_miss_disabled(self):
        """Should not raise when Prometheus disabled."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", False):
            record_analytics_cache_miss()


class TestClickEventRecording:
    """Test click event metrics recording."""

    @pytest.mark.asyncio
    async def test_record_click_event_happy(self):
        """Should record click event."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_click_events_total") as mock_counter:
                record_click_event("test query")
                mock_counter.labels.assert_called_once_with(query="test query")
                mock_counter.labels.return_value.inc.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_click_event_disabled(self):
        """Should not raise when Prometheus disabled."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", False):
            record_click_event("test query")


class TestCTRRecording:
    """Test click-through rate metrics recording."""

    @pytest.mark.asyncio
    async def test_record_ctr_happy(self):
        """Should record CTR percentage."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_ctr_percentage") as mock_gauge:
                record_ctr("24h", 5.5)
                mock_gauge.labels.assert_called_once_with(period="24h")
                mock_gauge.labels.return_value.set.assert_called_once_with(5.5)

    @pytest.mark.asyncio
    async def test_record_ctr_disabled(self):
        """Should not raise when Prometheus disabled."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", False):
            record_ctr("24h", 5.5)

    @pytest.mark.asyncio
    async def test_record_ctr_edge_cases(self):
        """Should handle CTR edge cases."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_ctr_percentage") as mock_gauge:
                # Zero CTR
                record_ctr("24h", 0.0)
                mock_gauge.labels.return_value.set.assert_called_once_with(0.0)

                # 100% CTR
                record_ctr("24h", 100.0)
                mock_gauge.labels.return_value.set.assert_called_with(100.0)


class TestAnalyticsMetricsRecorder:
    """Test AnalyticsMetricsRecorder context manager."""

    @pytest.mark.asyncio
    async def test_analytics_metrics_recorder_happy(self):
        """Should record duration on successful execution."""
        with patch("app.services.analytics_metrics.time") as mock_time:
            mock_time.monotonic.side_effect = [0.0, 1.5]  # start=0, end=1.5
            
            with patch("app.services.analytics_metrics.logger") as mock_logger:
                async with AnalyticsMetricsRecorder("test_operation") as recorder:
                    assert recorder.operation == "test_operation"
                    assert recorder.start_time == 0.0

                mock_logger.debug.assert_called_once()
                assert "test_operation completed in 1.500s" in mock_logger.debug.call_args[0][0]

    @pytest.mark.asyncio
    async def test_analytics_metrics_recorder_error(self):
        """Should log error on exception."""
        with patch("app.services.analytics_metrics.time") as mock_time:
            mock_time.monotonic.side_effect = [0.0, 2.0]

            with patch("app.services.analytics_metrics.logger") as mock_logger:
                with pytest.raises(ValueError):
                    async with AnalyticsMetricsRecorder("failing_operation"):
                        raise ValueError("Test error")

                mock_logger.error.assert_called_once()
                assert "failing_operation failed after 2.000s" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_analytics_metrics_recorder_disabled(self):
        """Should still work when Prometheus not available."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", False):
            with patch("app.services.analytics_metrics.time") as mock_time:
                mock_time.monotonic.side_effect = [0.0, 1.0]

                with patch("app.services.analytics_metrics.logger") as mock_logger:
                    async with AnalyticsMetricsRecorder("operation"):
                        pass

                    mock_logger.debug.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_record_search_query_with_unicode(self):
        """Should handle Unicode backend names."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_search_queries_total") as mock_counter:
                record_search_query("搜索", "unified")
                mock_counter.labels.assert_called_once_with(search_type="搜索", backend="unified")

    @pytest.mark.asyncio
    async def test_time_dashboard_generation_all_periods(self):
        """Should handle all period values."""
        periods = ["24h", "7d", "30d", "90d"]
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            for period in periods:
                with patch("app.services.analytics_metrics._prom_dashboard_generation_time") as mock_histogram:
                    @time_dashboard_generation(period)
                    async def dummy():
                        return "ok"

                    await dummy()
                    mock_histogram.labels.assert_called_once_with(period=period)

    @pytest.mark.asyncio
    async def test_record_ctr_large_value(self):
        """Should handle large CTR values."""
        with patch("app.services.analytics_metrics._HAS_PROMETHEUS", True):
            with patch("app.services.analytics_metrics._prom_ctr_percentage") as mock_gauge:
                record_ctr("7d", 99.99)
                mock_gauge.labels.return_value.set.assert_called_once_with(99.99)