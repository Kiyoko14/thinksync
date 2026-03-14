"""
Request logging middleware.

Logs all incoming requests and responses for monitoring and debugging.
"""

import time
import json
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from config import redis_client


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all requests and responses.
    
    Features:
    - Logs request method, path, and timing
    - Stores metrics in Redis for monitoring
    - Tracks response status codes
    - Supports exempting certain paths from logging
    """
    
    # Paths to skip logging (to reduce noise)
    SKIP_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip logging for exempt paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Get client IP
        ip_address = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or (request.client.host if request.client else "unknown")
        )
        
        # Get user info if available
        user_id = "anonymous"
        try:
            if hasattr(request.state, "user"):
                user_id = request.state.user.get("id", "anonymous")
        except Exception:
            pass
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Create log entry
        log_entry = {
            "timestamp": time.time(),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "user_id": user_id,
            "ip_address": ip_address,
        }
        
        # Print to console
        status_emoji = "✅" if response.status_code < 400 else "❌"
        print(
            f"{status_emoji} {request.method} {request.url.path} "
            f"→ {response.status_code} ({duration_ms:.0f}ms) "
            f"[user:{user_id}, ip:{ip_address}]"
        )
        
        # Store metrics in Redis for monitoring
        if redis_client:
            try:
                # Store recent requests
                key = f"logs:requests:{request.url.path}"
                redis_client.lpush(key, json.dumps(log_entry))
                redis_client.ltrim(key, 0, 99)  # Keep last 100 requests per endpoint
                redis_client.expire(key, 3600)  # 1 hour TTL
                
                # Track response times
                if response.status_code < 500:  # Don't skew metrics with errors
                    metrics_key = f"metrics:response_time:{request.url.path}"
                    redis_client.lpush(metrics_key, duration_ms)
                    redis_client.ltrim(metrics_key, 0, 999)
                    redis_client.expire(metrics_key, 3600)
                
                # Track status codes
                status_key = f"metrics:status:{response.status_code}"
                redis_client.incr(status_key)
                redis_client.expire(status_key, 3600)
                
            except Exception as e:
                print(f"Failed to log to Redis: {e}")
        
        # Add custom headers with timing info
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        
        return response


def get_endpoint_metrics(path: str, limit: int = 100) -> list:
    """
    Get recent request metrics for an endpoint.
    
    Args:
        path: The endpoint path
        limit: Maximum number of entries to return
        
    Returns:
        List of request log entries
    """
    if not redis_client:
        return []
    
    try:
        key = f"logs:requests:{path}"
        raw = redis_client.lrange(key, 0, limit - 1)
        return [json.loads(entry) for entry in raw]
    except Exception as e:
        print(f"Failed to get endpoint metrics: {e}")
        return []


def get_response_time_stats(path: str) -> dict:
    """
    Get response time statistics for an endpoint.
    
    Args:
        path: The endpoint path
        
    Returns:
        Dictionary with min, max, avg, and p95 response times
    """
    if not redis_client:
        return {}
    
    try:
        key = f"metrics:response_time:{path}"
        times = [float(t) for t in redis_client.lrange(key, 0, -1)]
        
        if not times:
            return {}
        
        times_sorted = sorted(times)
        count = len(times_sorted)
        
        return {
            "count": count,
            "min": times_sorted[0],
            "max": times_sorted[-1],
            "avg": sum(times) / count,
            "median": times_sorted[count // 2],
            "p95": times_sorted[int(count * 0.95)] if count > 20 else times_sorted[-1],
        }
    except Exception as e:
        print(f"Failed to get response time stats: {e}")
        return {}
