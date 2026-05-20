"""Rate limiting middleware for the Template MCP Server.

This module provides HTTP rate limiting middleware to protect against
abuse and ensure fair API usage across clients.
"""

import hashlib
import json
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from template_mcp_server.src.middleware.rate_limit_storage import RateLimitStorage
from template_mcp_server.src.settings import settings
from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()

# Global storage instance - set by api.py lifespan
_storage_instance: RateLimitStorage | None = None


def set_storage(storage: RateLimitStorage) -> None:
    """Set the global rate limit storage instance."""
    global _storage_instance
    _storage_instance = storage


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting on API requests.

    Uses a sliding window algorithm to track and limit requests per client.
    Clients are identified by auth token (when available) or IP address.
    """

    def __init__(self, app):
        """Initialize rate limiting middleware.

        Args:
            app: FastAPI application instance
        """
        super().__init__(app)
        logger.info("RateLimitMiddleware initialized")

    async def dispatch(self, request: Request, call_next: Callable):
        """Process incoming requests and apply rate limiting.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or endpoint handler

        Returns:
            HTTP response (200 with headers if allowed, 429 if rate limited)
        """
        # Early exit if rate limiting is disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip excluded paths (health checks, docs, etc.)
        if request.url.path in settings.RATE_LIMIT_EXCLUDE_PATHS:
            return await call_next(request)

        # Check if storage is initialized
        if _storage_instance is None:
            logger.warning("Rate limit storage not initialized, allowing request")
            return await call_next(request)

        # Get client identifier
        client_key = self._get_client_key(request)

        # Check rate limit
        allowed, current_count, reset_time = await _storage_instance.check_rate_limit(
            client_key, settings.RATE_LIMIT_REQUESTS, settings.RATE_LIMIT_WINDOW_SECONDS
        )

        # Rate limit exceeded - return 429
        if not allowed:
            retry_after = max(0, int(reset_time - time.time()))

            logger.warning(
                f"Rate limit exceeded for {client_key} on {request.url.path} "
                f"({current_count}/{settings.RATE_LIMIT_REQUESTS} requests)"
            )

            return Response(
                content=json.dumps(
                    {
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Try again in {retry_after}s",
                        "retry_after": retry_after,
                    }
                ),
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_REQUESTS),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_time)),
                    "Retry-After": str(retry_after),
                    "Content-Type": "application/json",
                },
            )

        # Allow request and add rate limit headers
        response = await call_next(request)

        # Add rate limit information to response headers
        remaining = max(0, settings.RATE_LIMIT_REQUESTS - current_count)
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))

        return response

    def _get_client_key(self, request: Request) -> str:
        """Extract client identifier from request.

        Priority:
        1. Auth token hash (if authentication is enabled and token present)
        2. Client IP address (fallback)

        Args:
            request: HTTP request

        Returns:
            Client identifier string (e.g., "token:abc123" or "ip:192.168.1.1")
        """
        # Try to get from authorization header first
        if settings.ENABLE_AUTH:
            auth_header = request.headers.get("authorization")
            if auth_header:
                # Hash the token for privacy
                token_hash = hashlib.sha256(auth_header.encode()).hexdigest()[:16]
                return f"token:{token_hash}"

        # Fallback to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
