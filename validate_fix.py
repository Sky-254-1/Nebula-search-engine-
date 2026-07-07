#!/usr/bin/env python3
"""Validation script for rate limit import fix."""
import sys
import subprocess

print("=" * 60)
print("RATE LIMIT IMPORT FIX VALIDATION")
print("=" * 60)

# Test 1: Compile check
print("\n[1/3] Running compileall...")
result = subprocess.run(
    ["python", "-m", "compileall", "backend/app"],
    capture_output=True,
    text=True
)
if result.returncode == 0:
    print("✓ Compilation successful")
else:
    print("✗ Compilation failed:")
    print(result.stderr)
    sys.exit(1)

# Test 2: Import check
print("\n[2/3] Testing rate limit imports...")
sys.path.insert(0, 'backend')
try:
    from app.middleware.rate_limit import (
        get_limiter,
        rate_limit_exceeded_handler,
        slowapi_middleware,
        RateLimitHeadersMiddleware
    )
    print("✓ All required imports successful:")
    print(f"  - get_limiter: {get_limiter}")
    print(f"  - rate_limit_exceeded_handler: {rate_limit_exceeded_handler}")
    print(f"  - slowapi_middleware: {slowapi_middleware}")
    print(f"  - RateLimitHeadersMiddleware: {RateLimitHeadersMiddleware}")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 3: Verify main.py can import
print("\n[3/3] Testing main.py imports...")
try:
    # Import just the rate limit related parts from main.py
    from app.config import get_settings
    from app.middleware.rate_limit import get_limiter, rate_limit_exceeded_handler, slowapi_middleware, RateLimitHeadersMiddleware
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    
    # Verify the functions are callable
    assert callable(get_limiter), "get_limiter is not callable"
    assert callable(rate_limit_exceeded_handler), "rate_limit_exceeded_handler is not callable"
    assert slowapi_middleware is None, "slowapi_middleware should be None"
    assert RateLimitHeadersMiddleware is not None, "RateLimitHeadersMiddleware is None"
    
    print("✓ main.py rate limit imports verified")
    print("\n" + "=" * 60)
    print("ALL VALIDATION CHECKS PASSED ✓")
    print("=" * 60)
except Exception as e:
    print(f"✗ Validation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)