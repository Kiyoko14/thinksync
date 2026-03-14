"""
Global error handling middleware.

Catches all unhandled exceptions and returns consistent error responses.
Logs errors for monitoring and debugging.
"""

import traceback
import uuid
from typing import Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from security.audit import log_security_event, SecurityEventType


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that catches all unhandled exceptions and returns
    consistent error responses.
    
    Features:
    - Generates unique error IDs for tracking
    - Logs detailed error information
    - Returns sanitized error messages to clients
    - Handles specific exception types appropriately
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Generate unique error ID for tracking
            error_id = str(uuid.uuid4())
            
            # Get client IP for logging
            ip_address = (
                request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or (request.client.host if request.client else "unknown")
            )
            
            # Get user info if available
            user_id = None
            try:
                if hasattr(request.state, "user"):
                    user_id = request.state.user.get("id")
            except Exception:
                pass
            
            # Log the error
            error_details = {
                "error_id": error_id,
                "path": request.url.path,
                "method": request.method,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback": traceback.format_exc(),
            }
            
            # Log to security audit system
            log_security_event(
                SecurityEventType.INCIDENT_SUSPICIOUS_ACTIVITY,
                user_id=user_id,
                details=error_details,
                ip_address=ip_address,
                severity="error",
            )
            
            # Print detailed error for server logs
            print(f"[ERROR {error_id}] Unhandled exception on {request.method} {request.url.path}")
            print(f"User: {user_id}, IP: {ip_address}")
            print(f"Exception: {type(exc).__name__}: {str(exc)}")
            print(traceback.format_exc())
            
            # Determine appropriate status code
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            error_message = "An unexpected error occurred. Please try again later."
            
            # Handle specific exception types
            if "authentication" in str(exc).lower() or "unauthorized" in str(exc).lower():
                status_code = status.HTTP_401_UNAUTHORIZED
                error_message = "Authentication failed"
            elif "permission" in str(exc).lower() or "forbidden" in str(exc).lower():
                status_code = status.HTTP_403_FORBIDDEN
                error_message = "Access denied"
            elif "not found" in str(exc).lower():
                status_code = status.HTTP_404_NOT_FOUND
                error_message = "Resource not found"
            elif "timeout" in str(exc).lower():
                status_code = status.HTTP_504_GATEWAY_TIMEOUT
                error_message = "Request timed out"
            elif "validation" in str(exc).lower():
                status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
                error_message = "Invalid input data"
            
            # Return error response
            return JSONResponse(
                status_code=status_code,
                content={
                    "detail": error_message,
                    "error_id": error_id,
                    "type": type(exc).__name__,
                },
            )
