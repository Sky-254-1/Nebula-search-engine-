"""Security headers and CSRF protection middleware."""

import secrets
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Basic security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS in production
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Content Security Policy — use config-driven values for production safety
        response.headers["Content-Security-Policy"] = settings.csp_policy

        # Cross-Origin isolation headers
        response.headers["Cross-Origin-Embedder-Policy"] = settings.cross_origin_embedder_policy
        response.headers["Cross-Origin-Opener-Policy"] = settings.cross_origin_opener_policy
        response.headers["Cross-Origin-Resource-Policy"] = settings.cross_origin_resource_policy
        
        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for state-changing operations."""
    
    EXEMPT_PATHS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    # Token expiry in seconds (30 minutes)
    _TOKEN_TTL = 1800

    def __init__(self, app):
        super().__init__(app)
        self._csrf_tokens: dict[str, tuple[str, float]] = {}  # session_id -> (token, expiry_timestamp)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip CSRF check for safe methods and exempt paths
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)
        
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Skip CSRF check for API routes with Authorization header (token-based auth)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)
        
        # Skip CSRF check if no auth header present - let auth middleware handle it
        # This allows auth middleware to return proper 401 instead of CSRF returning 403
        if not auth_header:
            return await call_next(request)
        
        # Check CSRF token for cookie-based auth
        csrf_token = request.headers.get("X-CSRF-Token", "")
        if not csrf_token:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing"},
            )
        
        # Validate CSRF token
        if not self._validate_csrf_token(csrf_token):
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid CSRF token"},
            )
        
        return await call_next(request)
    
    def _validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token with expiry check."""
        if len(token) < 32:
            return False
        import time
        now = time.time()
        # Check all tokens and clean up expired ones
        expired = [sid for sid, (tok, exp) in self._csrf_tokens.items() if exp < now]
        for sid in expired:
            del self._csrf_tokens[sid]
        # Check if token exists and is not expired
        for sid, (tok, exp) in self._csrf_tokens.items():
            if tok == token and exp > now:
                return True
        return False
    
    def generate_csrf_token(self, session_id: str) -> str:
        """Generate CSRF token for session with expiry."""
        import time
        token = secrets.token_urlsafe(32)
        self._csrf_tokens[session_id] = (token, time.time() + self._TOKEN_TTL)
        return token
    
    def get_csrf_token(self, session_id: str) -> Optional[str]:
        """Get CSRF token for session if not expired."""
        import time
        entry = self._csrf_tokens.get(session_id)
        if entry and entry[1] > time.time():
            return entry[0]
        if entry:
            del self._csrf_tokens[session_id]
        return None


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request size to prevent DoS attacks."""
    
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            return Response(
                status_code=413,
                content={"detail": "Request too large"},
                media_type="application/json",
            )
        
        # Also check actual content length
        if hasattr(request, "content_length") and request.content_length:
            if request.content_length > self.max_size:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request too large"},
                )
        
        return await call_next(request)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """IP whitelist middleware for admin routes (optional)."""
    
    def __init__(self, app, allowed_ips: list[str] = None):
        super().__init__(app)
        self.allowed_ips = allowed_ips or []
    
    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.allowed_ips:
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        if client_ip not in self.allowed_ips:
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied from this IP"},
            )
        
        return await call_next(request)


# CSRF protection instance
csrf_protection = CSRFProtectionMiddleware