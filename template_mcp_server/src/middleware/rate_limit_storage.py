"""Rate limit storage implementations for the Template MCP Server.

This module provides storage backends for rate limiting, supporting both
in-memory and PostgreSQL storage options.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

import asyncpg

from template_mcp_server.src.settings import settings
from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


class RateLimitStorage(ABC):
    """Abstract base class for rate limit storage backends."""

    @abstractmethod
    async def check_rate_limit(
        self, client_key: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int, float]:
        """Check if a request is allowed within the rate limit.

        Args:
            client_key: Unique identifier for the client
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (allowed, current_count, reset_timestamp):
                - allowed: True if request is allowed, False if rate limited
                - current_count: Current number of requests in the window
                - reset_timestamp: Unix timestamp when the window resets
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Remove expired rate limit entries.

        This method should be called periodically to prevent unbounded
        memory/storage growth.
        """
        pass


class InMemoryRateLimitStorage(RateLimitStorage):
    """In-memory rate limit storage using a sliding window algorithm.

    This storage backend is fast and simple, suitable for single-instance
    deployments. Rate limit data is lost on server restart.
    """

    def __init__(self):
        """Initialize in-memory storage."""
        self.requests: Dict[str, List[float]] = {}
        self.lock = asyncio.Lock()
        logger.debug("InMemoryRateLimitStorage initialized")

    async def check_rate_limit(
        self, client_key: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int, float]:
        """Check rate limit using sliding window algorithm.

        Args:
            client_key: Unique identifier for the client
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (allowed, current_count, reset_timestamp)
        """
        async with self.lock:
            current_time = time.time()
            window_start = current_time - window_seconds

            # Get and clean old requests outside the window
            if client_key in self.requests:
                self.requests[client_key] = [
                    ts for ts in self.requests[client_key] if ts > window_start
                ]
            else:
                self.requests[client_key] = []

            current_count = len(self.requests[client_key])

            # Check if under limit
            if current_count < max_requests:
                # Add new request timestamp
                self.requests[client_key].append(current_time)
                reset_time = current_time + window_seconds
                logger.debug(
                    f"Rate limit check: {client_key} - allowed ({current_count + 1}/{max_requests})"
                )
                return (True, current_count + 1, reset_time)
            else:
                # Calculate actual reset time (when oldest request expires)
                oldest_request = min(self.requests[client_key])
                reset_time = oldest_request + window_seconds
                logger.warning(
                    f"Rate limit exceeded: {client_key} ({current_count}/{max_requests})"
                )
                return (False, current_count, reset_time)

    async def cleanup(self) -> None:
        """Remove clients with no recent requests."""
        async with self.lock:
            current_time = time.time()
            cutoff_time = current_time - settings.RATE_LIMIT_MEMORY_RETENTION_SECONDS

            expired_keys = [
                key
                for key, timestamps in self.requests.items()
                if not timestamps or max(timestamps) < cutoff_time
            ]

            for key in expired_keys:
                del self.requests[key]

            if expired_keys:
                logger.debug(f"Rate limit cleanup: removed {len(expired_keys)} clients")


class PostgreSQLRateLimitStorage(RateLimitStorage):
    """PostgreSQL-backed rate limit storage using a sliding window algorithm.

    This storage backend is persistent and suitable for distributed deployments
    where multiple server instances share rate limit state.
    """

    def __init__(self, pool: asyncpg.Pool):
        """Initialize PostgreSQL storage.

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool
        logger.debug("PostgreSQLRateLimitStorage initialized")

    async def initialize(self) -> None:
        """Create the rate_limit_requests table if it doesn't exist."""
        if not self.pool:
            raise RuntimeError("PostgreSQL pool not initialized")

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rate_limit_requests (
                    id SERIAL PRIMARY KEY,
                    client_key VARCHAR(255) NOT NULL,
                    request_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                """
            )

            # Create indexes for efficient queries
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_rate_limit_client_timestamp
                ON rate_limit_requests (client_key, request_timestamp);
                """
            )

            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_rate_limit_cleanup
                ON rate_limit_requests (request_timestamp);
                """
            )

        logger.info("Rate limit database table initialized")

    async def check_rate_limit(
        self, client_key: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int, float]:
        """Check rate limit using PostgreSQL sliding window.

        Args:
            client_key: Unique identifier for the client
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (allowed, current_count, reset_timestamp)
        """
        if not self.pool:
            logger.error("PostgreSQL pool not available, allowing request")
            return (True, 0, time.time() + window_seconds)

        current_time = datetime.now(timezone.utc)
        window_start = current_time - timedelta(seconds=window_seconds)

        try:
            async with self.pool.acquire() as conn:
                # Count requests in the current window
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM rate_limit_requests
                    WHERE client_key = $1 AND request_timestamp > $2
                    """,
                    client_key,
                    window_start,
                )

                reset_time = (
                    current_time + timedelta(seconds=window_seconds)
                ).timestamp()

                if count < max_requests:
                    # Record this request
                    await conn.execute(
                        """
                        INSERT INTO rate_limit_requests (client_key, request_timestamp)
                        VALUES ($1, $2)
                        """,
                        client_key,
                        current_time,
                    )
                    logger.debug(
                        f"Rate limit check (PostgreSQL): {client_key} - allowed ({count + 1}/{max_requests})"
                    )
                    return (True, count + 1, reset_time)
                else:
                    # Get oldest request to calculate accurate reset time
                    oldest = await conn.fetchval(
                        """
                        SELECT request_timestamp FROM rate_limit_requests
                        WHERE client_key = $1 AND request_timestamp > $2
                        ORDER BY request_timestamp ASC LIMIT 1
                        """,
                        client_key,
                        window_start,
                    )

                    if oldest:
                        reset_time = (
                            oldest + timedelta(seconds=window_seconds)
                        ).timestamp()

                    logger.warning(
                        f"Rate limit exceeded (PostgreSQL): {client_key} ({count}/{max_requests})"
                    )
                    return (False, count, reset_time)

        except Exception as e:
            logger.error(f"Rate limit check failed (PostgreSQL): {e}")
            # Fail open - allow the request if storage fails
            return (True, 0, time.time() + window_seconds)

    async def cleanup(self) -> None:
        """Delete old rate limit records from database."""
        if not self.pool:
            logger.warning("PostgreSQL pool not available for cleanup")
            return

        cutoff_time = datetime.now(timezone.utc) - timedelta(
            hours=settings.RATE_LIMIT_DB_RETENTION_HOURS
        )

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM rate_limit_requests
                    WHERE request_timestamp < $1
                    """,
                    cutoff_time,
                )

                # Extract number of rows deleted from result string
                if result:
                    rows_deleted = int(result.split()[-1]) if result.split() else 0
                    if rows_deleted > 0:
                        logger.debug(
                            f"Rate limit cleanup (PostgreSQL): removed {rows_deleted} records"
                        )

        except Exception as e:
            logger.error(f"Rate limit cleanup failed (PostgreSQL): {e}")
