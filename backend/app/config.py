"""Application configuration loaded from environment variables."""

import os
import secrets
import sys
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


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
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"))
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
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500",
        )
    )

    @property
    def db_path(self) -> str:
        if self.database_url.startswith("postgresql"):
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
