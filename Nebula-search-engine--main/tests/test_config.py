"""Configuration tests: default values, env overrides, production validation, CORS parsing, CSP generation."""

import os
import pytest
from unittest.mock import patch


def _reset_settings():
    from app.config import get_settings
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_settings():
    _reset_settings()
    yield
    _reset_settings()


class TestDefaultValues:
    def test_default_db_path(self):
        from app.config import get_settings
        s = get_settings()
        assert s.database_url is not None

    def test_default_jwt_algorithm(self):
        from app.config import get_settings
        assert get_settings().jwt_algorithm == "HS256"

    def test_default_app_env(self):
        from app.config import get_settings
        assert get_settings().app_env == "testing"

    def test_default_jwt_expiry_hours(self):
        from app.config import get_settings
        assert get_settings().jwt_expiry_hours == 24

    def test_default_refresh_token_days(self):
        from app.config import get_settings
        assert get_settings().refresh_token_days == 30

    def test_default_cache_ttl(self):
        from app.config import get_settings
        assert get_settings().cache_ttl_seconds == 300

    def test_default_rate_limit(self):
        from app.config import get_settings
        assert get_settings().rate_limit_per_minute == 60


class TestEnvironmentVariableOverride:
    def test_database_url_override(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        _reset_settings()
        from app.config import get_settings
        assert get_settings().database_url == "postgresql://user:pass@localhost/db"

    def test_jwt_secret_override(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("JWT_SECRET", "custom-secret")
        _reset_settings()
        from app.config import get_settings
        assert get_settings().jwt_secret == "custom-secret"

    def test_openai_key_override(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        _reset_settings()
        from app.config import get_settings
        assert get_settings().openai_api_key == "sk-test"

    def test_cors_origins_override(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CORS_ORIGINS", "https://example.com")
        _reset_settings()
        from app.config import get_settings
        assert get_settings().cors_origins == "https://example.com"

    def test_rate_limit_override(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "120")
        _reset_settings()
        from app.config import get_settings
        assert get_settings().rate_limit_per_minute == 120


class TestProductionValidation:
    def test_is_production_true(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_ENV", "production")
        _reset_settings()
        from app.config import get_settings
        assert get_settings().is_production is True

    def test_is_production_false(self):
        from app.config import get_settings
        assert get_settings().is_production is False

    def test_uses_postgres(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/db")
        _reset_settings()
        from app.config import get_settings
        assert get_settings().uses_postgres is True

    def test_db_path_for_sqlite(self):
        from app.config import get_settings
        assert get_settings().db_path == get_settings().database_url


class TestCORSParsing:
    def test_cors_origin_list(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CORS_ORIGINS", "http://a.com,http://b.com,http://c.com")
        _reset_settings()
        from app.config import get_settings
        origins = get_settings().cors_origin_list
        assert len(origins) == 3
        parsed = {__import__("urllib.parse").urlparse(o).netloc.lower() for o in origins}
        assert "a.com" in parsed

    def test_cors_wildcard(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CORS_ORIGINS", "*")
        _reset_settings()
        from app.config import get_settings
        assert get_settings().cors_origin_list == ["*"]

    def test_cors_empty_string(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CORS_ORIGINS", "")
        _reset_settings()
        from app.config import get_settings
        assert get_settings().cors_origin_list == []


class TestCSPPolicyGeneration:
    def test_csp_policy_basic(self):
        from app.config import get_settings
        policy = get_settings().csp_policy
        assert "default-src 'self'" in policy
        assert "script-src" in policy
        assert "style-src" in policy
        assert "img-src" in policy

    def test_csp_policy_with_report_uri(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CSP_REPORT_URI", "https://example.com/csp")
        _reset_settings()
        from app.config import get_settings
        policy = get_settings().csp_policy
        assert "report-uri" in policy
        assert "report-to" in policy

    def test_csp_policy_custom_directives(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CSP_DEFAULT_SRC", "'none'")
        monkeypatch.setenv("CSP_SCRIPT_SRC", "'self' https://cdn.example.com")
        _reset_settings()
        from app.config import get_settings
        policy = get_settings().csp_policy
        assert "default-src 'none'" in policy
        parsed_directives = [d.strip() for d in policy.split(";")]
        assert any("cdn.example.com" in d for d in parsed_directives)


class TestStoragePaths:
    def test_storage_uploads_path(self):
        from app.config import get_settings
        assert "uploads" in str(get_settings().storage_uploads)

    def test_storage_exports_path(self):
        from app.config import get_settings
        assert "exports" in str(get_settings().storage_exports)

    def test_encryption_key_bytes_padded(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("ENCRYPTION_KEY", "short")
        _reset_settings()
        from app.config import get_settings
        key = get_settings().encryption_key_bytes
        assert len(key) == 32
