"""Targeted tests to reach 60% backend coverage."""
import pytest
from fastapi import HTTPException
from unittest.mock import patch, MagicMock

from app.services.search import (
    _validate_url,
    ALLOWED_BACKENDS,
    ALLOWED_DOMAINS,
    BLOCKED_IP_RANGES,
)


class TestURLValidation:
    """Tests for _validate_url SSRF protection."""

    def test_https_allowed(self):
        """Valid HTTPS URLs pass validation."""
        url = "https://en.wikipedia.org/wiki/Test"
        _validate_url(url)  # Should not raise

    def test_http_rejected(self):
        """Plain HTTP URLs are rejected."""
        with pytest.raises(HTTPException) as exc:
            _validate_url("http://example.com/test")
        assert exc.value.status_code == 400

    def test_localhost_allowed_in_dev(self):
        """Localhost allowed in non-production mode."""
        with patch('app.services.search.settings') as mock_settings:
            mock_settings.is_production = False
            _validate_url("http://localhost:8000/test")

    def test_localhost_rejected_in_production(self):
        """Localhost rejected in production mode."""
        with patch('app.services.search.settings') as mock_settings:
            mock_settings.is_production = True
            with pytest.raises(HTTPException) as exc:
                _validate_url("http://localhost:8000/test")
            assert "Localhost not allowed" in str(exc.value.detail)

    def test_domain_whitelist_rejection(self):
        """Non-whitelisted domains are rejected."""
        with pytest.raises(HTTPException) as exc:
            _validate_url("https://evil.com/attack")
        assert "Domain not allowed" in str(exc.value.detail)

    def test_missing_hostname_rejected(self):
        """URLs without hostname are rejected."""
        with pytest.raises(HTTPException) as exc:
            _validate_url("https:///path")
        assert "no hostname" in str(exc.value.detail)

    def test_invalid_scheme_rejected(self):
        """Non-HTTP(S) schemes are rejected."""
        with pytest.raises(HTTPException) as exc:
            _validate_url("ftp://example.com/file")
        assert "Invalid URL scheme" in str(exc.value.detail)

    def test_brave_search_allowed(self):
        """Brave search API domain is whitelisted."""
        url = "https://api.search.brave.com/res/v1/web/search?q=test"
        _validate_url(url)

    def test_serpapi_allowed(self):
        """SerpAPI domain is whitelisted."""
        url = "https://serpapi.com/search?engine=google"
        _validate_url(url)


class TestAllowedBackends:
    """Verify allowed search backends."""

    def test_allowed_backends_set(self):
        """Verify the expected backends are allowed."""
        assert ALLOWED_BACKENDS == {"wikipedia", "brave", "serpapi"}

    def test_allowed_domains_set(self):
        """Verify the expected domains are allowed."""
        assert "en.wikipedia.org" in ALLOWED_DOMAINS
        assert "api.search.brave.com" in ALLOWED_DOMAINS
        assert "serpapi.com" in ALLOWED_DOMAINS
        assert "www.google.com" in ALLOWED_DOMAINS


class TestBlockedIPRanges:
    """Verify SSRF IP blocking ranges."""

    def test_private_networks_blocked(self):
        """Verify private IP ranges are in the block list."""
        assert any("10.0.0.0/8" in str(r) for r in BLOCKED_IP_RANGES)
        assert any("172.16.0.0/12" in str(r) for r in BLOCKED_IP_RANGES)
        assert any("192.168.0.0/16" in str(r) for r in BLOCKED_IP_RANGES)
        assert any("127.0.0.0/8" in str(r) for r in BLOCKED_IP_RANGES)