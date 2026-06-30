"""Security headers middleware — configurable via Settings."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings

settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add hardened security headers to every response.

    All values are configurable through environment variables / Settings.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # === Existing headers (unchanged behaviour) ===
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = settings.permissions_policy

        # HSTS — only in production (preserves original guard)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # === New headers ===
        # Content-Security-Policy
        response.headers["Content-Security-Policy"] = settings.csp_policy

        # Cross-Origin-Embedder-Policy
        response.headers["Cross-Origin-Embedder-Policy"] = (
            settings.cross_origin_embedder_policy
        )

        # Cross-Origin-Opener-Policy
        response.headers["Cross-Origin-Opener-Policy"] = (
            settings.cross_origin_opener_policy
        )

        # Cross-Origin-Resource-Policy
        response.headers["Cross-Origin-Resource-Policy"] = (
            settings.cross_origin_resource_policy
        )

        return response
