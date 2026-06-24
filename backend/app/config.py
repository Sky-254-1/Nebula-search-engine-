"""Application configuration loaded from environment variables."""

import os
import secrets
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if secret:
        return secret
    generated = secrets.token_hex(32)
    if os.getenv("APP_ENV", "development") == "production":
        print(
            "WARNING: JWT_SECRET is not set in production. "
            "Tokens will be invalidated on restart.",
            file=sys.stderr,
        )
    return generated


@dataclass(frozen=True)
class Settings:
    """Validated runtime settings for Nebula Search API."""

    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "nebula.db"))
    jwt_secret: str = field(default_factory=_resolve_jwt_secret)
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = field(
        default_factory=lambda: int(os.getenv("JWT_EXPIRY_HOURS", "24"))
    )
    refresh_token_days: int = field(
        default_factory=lambda: int(os.getenv("REFRESH_TOKEN_DAYS", "30"))
    )
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"))
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2"))
    gguf_model_path: str = field(default_factory=lambda: os.getenv("GGUF_MODEL_PATH", ""))
    ai_provider: str = field(default_factory=lambda: os.getenv("AI_PROVIDER", "auto"))
    brave_api_key: str = field(default_factory=lambda: os.getenv("BRAVE_API_KEY", ""))
    serpapi_key: str = field(default_factory=lambda: os.getenv("SERPAPI_KEY", ""))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    rate_limit_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    )
    cors_origins: str = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
        )
    )
    cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("CACHE_TTL_SECONDS", "300"))
    )
    storage_root: str = field(
        default_factory=lambda: os.getenv("STORAGE_ROOT", str(_REPO_ROOT / "storage"))
    )

    @property
    def uses_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def db_path(self) -> str:
        if self.uses_postgres:
            return "nebula.db"
        return self.database_url

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def storage_uploads(self) -> Path:
        return Path(self.storage_root) / "uploads"

    @property
    def storage_cache(self) -> Path:
        return Path(self.storage_root) / "cache"

    @property
    def storage_vector(self) -> Path:
        return Path(self.storage_root) / "vector"

    @property
    def storage_indexes(self) -> Path:
        return Path(self.storage_root) / "indexes"

    @property
    def storage_exports(self) -> Path:
        return Path(self.storage_root) / "exports"


@lru_cache
def get_settings() -> Settings:
    return Settings()
