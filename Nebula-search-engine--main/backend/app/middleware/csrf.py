"""CSRF protection middleware using the double-submit cookie pattern."""

import logging
import secrets
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

logger = logging.getLogger("nebula.csrf")

settings = get_settings()

# Safe methods per RFC 7231
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Paths that are exempt from CSRF checks (e.g. webhook callbacks)
_CSRF_EXEMPT_PATHS = frozenset({
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/signup",
    "/api/v1/auth/refresh",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/metrics",
})


def generate_csrf_token() -> str:
    """Generate a cryptographically random CSRF token."""
    return secrets.token_urlsafe(32)


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie CSRF protection.

    On every safe response the middleware sets a ``csrf_token`` cookie.
    Unsafe requests (POST, PUT, DELETE, PATCH) must include the same
    value in either an ``X-CSRF-Token`` header or a ``csrf_token``
    form field.

    When ``ENABLE_CSRF=false`` the middleware is a no-op.
    """

    def __init__(
        self,
        app,
        exempt_paths: Optional[set[str]] = None,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        form_field: str = "csrf_token",
    ) -> None:
        super().__init__(app)
        self._exempt_paths = _CSRF_EXEMPT_PATHS if exempt_paths is None else exempt_paths
        self._cookie_name = cookie_name
        self._header_name = header_name
        self._form_field = form_field

    async def dispatch(self, request: Request, call_next) -> Response:
        # Feature flag gate
        if not settings.enable_csrf:
            return await call_next(request)

        path = request.url.path

        # Exempt paths
        if path in self._exempt_paths or path.startswith("/api/v1/auth/"):
            return await call_next(request)

        # Unsafe request → validate token
        if request.method not in _SAFE_METHODS:
            cookie_token = request.cookies.get(self._cookie_name)
            header_token = request.headers.get(self._header_name)
            body_token = None

            if request.headers.get("content-type", "").startswith(
                "application/x-www-form-urlencoded"
            ) or request.headers.get("content-type", "").startswith("multipart/form-data"):
                try:
                    form = await request.form()
                    body_token = form.get(self._form_field)
                except Exception as exc:
                    logger.warning("Failed to parse form data for CSRF check: %s", exc)

            submitted_token = header_token or body_token

            if not cookie_token or not submitted_token:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token missing"},
                )

            if not secrets.compare_digest(cookie_token, submitted_token):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token mismatch"},
                )

        # Safe request — ensure a cookie is present
        response: Response = await call_next(request)

        if not request.cookies.get(self._cookie_name):
            token = generate_csrf_token()
            response.set_cookie(
                key=self._cookie_name,
                value=token,
                httponly=True,
                secure=settings.cookie_secure,
                samesite=settings.cookie_samesite,
                max_age=3600,  # 1 hour
            )

        return response
