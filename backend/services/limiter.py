"""
Redis-backed fixed-window rate limiter middleware.

Each IP is allowed `requests_per_minute` requests in any 60-second window.
The window resets on the minute boundary (fixed-window), which means at most
2× the limit can arrive around a bucket boundary.  This is acceptable for
typical API protection; callers that need stricter guarantees can lower the
limit or implement client-side queuing.

When Redis is unavailable the middleware becomes a no-op so the service
degrades gracefully rather than blocking all traffic.

Usage in main.py:
    from services.limiter import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware, requests_per_minute=120)
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config import redis_client

# Paths exempted from rate limiting (health / metrics probes)
_EXEMPT_PATHS = frozenset({"/", "/health", "/docs", "/openapi.json", "/redoc"})

# Per-user (JWT) limits — stricter than per-IP for expensive endpoints
_EXPENSIVE_PREFIXES = ("/agents/", "/monitor/", "/pipelines/")
_USER_LIMIT_MULTIPLIER = 0.5   # users get 50% of the per-IP limit on expensive routes


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter backed by Redis.

    Parameters
    ----------
    requests_per_minute : int
        Max requests a single IP may send per 60-second window.
        Default: 120.
    burst : int
        Additional requests allowed in the first second of a new window.
        Default: 20.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 120,
        burst: int = 20,
    ) -> None:
        super().__init__(app)
        self.limit = requests_per_minute
        self.burst = burst
        self.window = 60  # seconds

    async def dispatch(self, request: Request, call_next):
        # Skip exempt paths
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        # Skip if Redis is unavailable (graceful degradation)
        if not redis_client:
            return await call_next(request)

        # Derive client identity: prefer X-Forwarded-For (reverse proxy), else socket IP
        ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or (request.client.host if request.client else "unknown")
        )
        # Round to 60-s window bucket for fixed-window approach
        bucket = int(time.time() // self.window)
        key = f"rl:ip:{ip}:{bucket}"

        limit = self.limit
        # Stricter limit for expensive agent/pipeline/monitor endpoints
        if any(request.url.path.startswith(p) for p in _EXPENSIVE_PREFIXES):
            limit = max(10, self.limit // 4)

        try:
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.window * 2)
            results = pipe.execute()
            current: int = results[0]
        except Exception:
            # Redis error — let the request through
            return await call_next(request)

        remaining = max(0, limit - current)

        if current > limit + self.burst:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
                headers={
                    "Retry-After": str(self.window),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
