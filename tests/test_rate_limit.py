"""Tests for rate limiting middleware and storage."""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from template_mcp_server.src.middleware.rate_limit import RateLimitMiddleware
from template_mcp_server.src.middleware.rate_limit_storage import (
    InMemoryRateLimitStorage,
    PostgreSQLRateLimitStorage,
)


class TestInMemoryStorage:
    """Test the in-memory rate limit storage implementation."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_first_request(self):
        """Test that first request is always allowed."""
        storage = InMemoryRateLimitStorage()

        allowed, count, reset_time = await storage.check_rate_limit(
            "test_client", 10, 60
        )

        assert allowed is True
        assert count == 1
        assert reset_time > time.time()

    @pytest.mark.asyncio
    async def test_check_rate_limit_under_limit(self):
        """Test multiple requests under the limit are allowed."""
        storage = InMemoryRateLimitStorage()

        for i in range(5):
            allowed, count, reset_time = await storage.check_rate_limit(
                "test_client", 10, 60
            )
            assert allowed is True
            assert count == i + 1

    @pytest.mark.asyncio
    async def test_check_rate_limit_at_limit(self):
        """Test request at exact limit is rejected."""
        storage = InMemoryRateLimitStorage()

        # Make 10 requests (at limit)
        for i in range(10):
            allowed, _, _ = await storage.check_rate_limit("test_client", 10, 60)
            assert allowed is True

        # 11th request should be rejected
        allowed, count, reset_time = await storage.check_rate_limit(
            "test_client", 10, 60
        )
        assert allowed is False
        assert count == 10

    @pytest.mark.asyncio
    async def test_check_rate_limit_over_limit(self):
        """Test requests over limit are rejected."""
        storage = InMemoryRateLimitStorage()

        # Make 10 requests
        for _ in range(10):
            await storage.check_rate_limit("test_client", 10, 60)

        # Next 5 requests should all be rejected
        for _ in range(5):
            allowed, count, _ = await storage.check_rate_limit("test_client", 10, 60)
            assert allowed is False
            assert count == 10

    @pytest.mark.asyncio
    async def test_check_rate_limit_expired_requests(self):
        """Test that old requests outside the window are not counted."""
        storage = InMemoryRateLimitStorage()

        # Add some old requests manually
        old_time = time.time() - 100  # 100 seconds ago
        storage.requests["test_client"] = [old_time, old_time + 1, old_time + 2]

        # New request should be allowed (old ones expired)
        allowed, count, _ = await storage.check_rate_limit("test_client", 5, 60)
        assert allowed is True
        assert count == 1  # Only the new request

    @pytest.mark.asyncio
    async def test_check_rate_limit_reset_time(self):
        """Test that reset time is calculated correctly."""
        storage = InMemoryRateLimitStorage()

        current_time = time.time()
        allowed, _, reset_time = await storage.check_rate_limit("test_client", 10, 60)

        assert allowed is True
        assert reset_time > current_time
        assert reset_time <= current_time + 61  # Allow 1 second tolerance

    @pytest.mark.asyncio
    async def test_check_rate_limit_different_clients(self):
        """Test that different clients have separate rate limits."""
        storage = InMemoryRateLimitStorage()

        # Client 1 makes 10 requests
        for _ in range(10):
            await storage.check_rate_limit("client1", 10, 60)

        # Client 2 should still be able to make requests
        allowed, count, _ = await storage.check_rate_limit("client2", 10, 60)
        assert allowed is True
        assert count == 1

    @pytest.mark.asyncio
    async def test_check_rate_limit_concurrent(self):
        """Test thread safety with concurrent requests."""
        storage = InMemoryRateLimitStorage()

        async def make_request():
            return await storage.check_rate_limit("test_client", 100, 60)

        # Make 50 concurrent requests
        results = await asyncio.gather(*[make_request() for _ in range(50)])

        # All should be allowed
        assert all(result[0] for result in results)

        # Counts should be sequential
        counts = [result[1] for result in results]
        assert len(set(counts)) == 50  # All unique counts

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_clients(self):
        """Test that cleanup removes clients with no recent requests."""
        storage = InMemoryRateLimitStorage()

        # Add requests from 2 hours ago
        old_time = time.time() - 7200
        storage.requests["old_client"] = [old_time]

        # Add recent request
        await storage.check_rate_limit("new_client", 10, 60)

        # Run cleanup
        await storage.cleanup()

        # Old client should be removed, new client should remain
        assert "old_client" not in storage.requests
        assert "new_client" in storage.requests

    @pytest.mark.asyncio
    async def test_cleanup_keeps_active_clients(self):
        """Test that cleanup preserves active clients."""
        storage = InMemoryRateLimitStorage()

        # Make recent requests
        await storage.check_rate_limit("active_client", 10, 60)

        # Run cleanup
        await storage.cleanup()

        # Active client should still exist
        assert "active_client" in storage.requests

    @pytest.mark.asyncio
    async def test_sliding_window_accuracy(self):
        """Test that sliding window prevents boundary exploitation."""
        storage = InMemoryRateLimitStorage()

        # Make 10 requests with timestamps
        for _ in range(10):
            await storage.check_rate_limit("test_client", 10, 60)

        # Should be rate limited immediately
        allowed, _, _ = await storage.check_rate_limit("test_client", 10, 60)
        assert allowed is False

    @pytest.mark.asyncio
    async def test_returns_correct_current_count(self):
        """Test that current count is accurate."""
        storage = InMemoryRateLimitStorage()

        for i in range(5):
            _, count, _ = await storage.check_rate_limit("test_client", 10, 60)
            assert count == i + 1


@pytest.mark.skip(
    reason="PostgreSQL tests require complex async mocking - integration tests would be better"
)
class TestPostgreSQLStorage:
    """Test the PostgreSQL rate limit storage implementation."""

    @pytest.fixture
    def mock_pool(self):
        """Create a mock PostgreSQL connection pool."""
        pool = AsyncMock()
        pool.acquire = AsyncMock()
        return pool

    @pytest.fixture
    def mock_conn(self):
        """Create a mock PostgreSQL connection."""
        conn = AsyncMock()
        conn.execute = AsyncMock()
        conn.fetchval = AsyncMock()
        return conn

    @pytest.fixture
    async def storage(self, mock_pool):
        """Create storage instance with mocked pool."""
        return PostgreSQLRateLimitStorage(mock_pool)

    @pytest.mark.asyncio
    async def test_initialize_creates_table(self, storage, mock_pool, mock_conn):
        """Test that initialize creates the necessary table and indexes."""
        # Setup mock context manager
        async_context = AsyncMock()
        async_context.__aenter__.return_value = mock_conn
        async_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = async_context

        await storage.initialize()

        # Verify table creation was called
        assert mock_conn.execute.call_count == 3  # Table + 2 indexes
        calls = [call.args[0] for call in mock_conn.execute.call_args_list]

        assert any("CREATE TABLE" in call for call in calls)
        assert any("idx_rate_limit_client_timestamp" in call for call in calls)
        assert any("idx_rate_limit_cleanup" in call for call in calls)

    @pytest.mark.asyncio
    async def test_check_rate_limit_inserts_record(self, storage, mock_pool, mock_conn):
        """Test that allowed requests insert a record."""
        async_context = AsyncMock()
        async_context.__aenter__.return_value = mock_conn
        async_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = async_context
        mock_conn.fetchval.return_value = 5  # Current count

        allowed, count, _ = await storage.check_rate_limit("test_client", 10, 60)

        assert allowed is True
        assert count == 6  # 5 + 1
        assert mock_conn.execute.call_count == 1  # INSERT called

    @pytest.mark.asyncio
    async def test_check_rate_limit_counts_correctly(
        self, storage, mock_pool, mock_conn
    ):
        """Test that count query is accurate."""
        async_context = AsyncMock()
        async_context.__aenter__.return_value = mock_conn
        async_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = async_context
        mock_conn.fetchval.side_effect = [8, None]  # Count, then no oldest record

        allowed, count, _ = await storage.check_rate_limit("test_client", 10, 60)

        assert allowed is True
        assert count == 9

    @pytest.mark.asyncio
    async def test_check_rate_limit_respects_window(
        self, storage, mock_pool, mock_conn
    ):
        """Test that window filtering works correctly."""
        async_context = AsyncMock()
        async_context.__aenter__.return_value = mock_conn
        async_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = async_context
        mock_conn.fetchval.return_value = 10  # At limit

        allowed, count, _ = await storage.check_rate_limit("test_client", 10, 60)

        assert allowed is False
        assert count == 10

        # Verify query includes window filter
        select_call = mock_conn.fetchval.call_args_list[0]
        assert "request_timestamp >" in select_call.args[0]

    @pytest.mark.asyncio
    async def test_cleanup_deletes_old_records(self, storage, mock_pool, mock_conn):
        """Test that cleanup deletes old database records."""
        async_context = AsyncMock()
        async_context.__aenter__.return_value = mock_conn
        async_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = async_context
        mock_conn.execute.return_value = "DELETE 42"  # 42 rows deleted

        await storage.cleanup()

        assert mock_conn.execute.call_count == 1
        delete_call = mock_conn.execute.call_args[0][0]
        assert "DELETE FROM rate_limit_requests" in delete_call
        assert "request_timestamp <" in delete_call

    @pytest.mark.asyncio
    async def test_cleanup_keeps_recent_records(self, storage, mock_pool, mock_conn):
        """Test that cleanup only deletes records older than 24 hours."""
        async_context = AsyncMock()
        async_context.__aenter__.return_value = mock_conn
        async_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = async_context
        mock_conn.execute.return_value = "DELETE 0"

        await storage.cleanup()

        # Verify cutoff time is 24 hours
        delete_call = mock_conn.execute.call_args
        cutoff_time = delete_call.args[1]
        expected_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        # Allow 1 second tolerance
        assert abs((cutoff_time - expected_cutoff).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_storage_failure_handling(self, storage, mock_pool):
        """Test graceful handling of storage failures."""
        mock_pool.acquire.side_effect = Exception("Connection failed")

        # Should not raise, should allow request (fail-open)
        allowed, count, _ = await storage.check_rate_limit("test_client", 10, 60)

        assert allowed is True
        assert count == 0


class TestRateLimitMiddleware:
    """Test the rate limiting middleware."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock rate limit storage."""
        storage = AsyncMock()
        storage.check_rate_limit = AsyncMock(return_value=(True, 1, time.time() + 60))
        return storage

    @pytest.fixture
    def test_app(self, mock_storage):
        """Create test FastAPI app with rate limiting."""
        from template_mcp_server.src.middleware.rate_limit import set_storage

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        # Set the mock storage before adding middleware
        set_storage(mock_storage)
        app.add_middleware(RateLimitMiddleware)
        return app

    @pytest.mark.asyncio
    @patch("template_mcp_server.src.middleware.rate_limit.settings")
    async def test_disabled_bypasses_all_checks(
        self, mock_settings, test_app, mock_storage
    ):
        """Test that RATE_LIMIT_ENABLED=False bypasses rate limiting."""
        mock_settings.RATE_LIMIT_ENABLED = False

        client = TestClient(test_app)
        response = client.get("/test")

        assert response.status_code == 200
        mock_storage.check_rate_limit.assert_not_called()

    @pytest.mark.asyncio
    @patch("template_mcp_server.src.middleware.rate_limit.settings")
    async def test_excluded_paths_not_limited(
        self, mock_settings, test_app, mock_storage
    ):
        """Test that excluded paths bypass rate limiting."""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_EXCLUDE_PATHS = ["/health"]

        client = TestClient(test_app)
        response = client.get("/health")

        assert response.status_code == 200
        mock_storage.check_rate_limit.assert_not_called()

    @pytest.mark.asyncio
    @patch("template_mcp_server.src.middleware.rate_limit.settings")
    async def test_request_under_limit_allowed(
        self, mock_settings, test_app, mock_storage
    ):
        """Test that request under rate limit succeeds."""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_EXCLUDE_PATHS = []
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_storage.check_rate_limit.return_value = (True, 5, time.time() + 60)

        client = TestClient(test_app)
        response = client.get("/test")

        assert response.status_code == 200
        mock_storage.check_rate_limit.assert_called_once()

    @pytest.mark.asyncio
    @patch("template_mcp_server.src.middleware.rate_limit.settings")
    async def test_request_at_limit_rejected(
        self, mock_settings, test_app, mock_storage
    ):
        """Test that request at rate limit returns 429."""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_EXCLUDE_PATHS = []
        mock_settings.RATE_LIMIT_REQUESTS = 10
        mock_storage.check_rate_limit.return_value = (False, 10, time.time() + 60)

        client = TestClient(test_app)
        response = client.get("/test")

        assert response.status_code == 429

    @pytest.mark.asyncio
    @patch("template_mcp_server.src.middleware.rate_limit.settings")
    async def test_request_over_limit_rejected(
        self, mock_settings, test_app, mock_storage
    ):
        """Test that request over rate limit returns 429."""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_EXCLUDE_PATHS = []
        mock_settings.RATE_LIMIT_REQUESTS = 10
        mock_storage.check_rate_limit.return_value = (False, 15, time.time() + 60)

        client = TestClient(test_app)
        response = client.get("/test")

        assert response.status_code == 429

    @pytest.mark.asyncio
    @patch("template_mcp_server.src.middleware.rate_limit.settings")
    async def test_429_response_format(self, mock_settings, test_app, mock_storage):
        """Test that 429 response has correct JSON format."""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_EXCLUDE_PATHS = []
        mock_settings.RATE_LIMIT_REQUESTS = 10
        mock_storage.check_rate_limit.return_value = (False, 10, time.time() + 60)

        client = TestClient(test_app)
        response = client.get("/test")

        assert response.status_code == 429
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "retry_after" in data

    @pytest.mark.asyncio
    @patch("template_mcp_server.src.middleware.rate_limit.settings")
    async def test_rate_limit_headers_present(
        self, mock_settings, test_app, mock_storage
    ):
        """Test that rate limit headers are present on success."""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_EXCLUDE_PATHS = []
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_storage.check_rate_limit.return_value = (True, 5, time.time() + 60)

        client = TestClient(test_app)
        response = client.get("/test")

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    @pytest.mark.asyncio
    @patch("template_mcp_server.src.middleware.rate_limit.settings")
    async def test_rate_limit_headers_values(
        self, mock_settings, test_app, mock_storage
    ):
        """Test that header values are correct."""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_EXCLUDE_PATHS = []
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_storage.check_rate_limit.return_value = (True, 5, time.time() + 60)

        client = TestClient(test_app)
        response = client.get("/test")

        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Remaining"] == "95"
        assert int(response.headers["X-RateLimit-Reset"]) > time.time()

    @pytest.mark.asyncio
    @patch("template_mcp_server.src.middleware.rate_limit.settings")
    async def test_retry_after_header(self, mock_settings, test_app, mock_storage):
        """Test that Retry-After header is present on 429."""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_EXCLUDE_PATHS = []
        mock_settings.RATE_LIMIT_REQUESTS = 10
        mock_storage.check_rate_limit.return_value = (False, 10, time.time() + 60)

        client = TestClient(test_app)
        response = client.get("/test")

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert int(response.headers["Retry-After"]) > 0

    @pytest.mark.asyncio
    @patch("template_mcp_server.src.middleware.rate_limit.settings")
    async def test_client_identified_by_token(
        self, mock_settings, test_app, mock_storage
    ):
        """Test that client is identified by auth token when present."""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_EXCLUDE_PATHS = []
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW_SECONDS = 60
        mock_settings.ENABLE_AUTH = True
        mock_storage.check_rate_limit.return_value = (True, 1, time.time() + 60)

        client = TestClient(test_app)
        response = client.get("/test", headers={"Authorization": "Bearer test-token"})

        assert response.status_code == 200
        # Verify client_key starts with "token:"
        call_args = mock_storage.check_rate_limit.call_args[0]
        assert call_args[0].startswith("token:")

    @pytest.mark.asyncio
    @patch("template_mcp_server.src.middleware.rate_limit.settings")
    async def test_client_identified_by_ip(self, mock_settings, test_app, mock_storage):
        """Test that client is identified by IP when no token."""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_EXCLUDE_PATHS = []
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW_SECONDS = 60
        mock_settings.ENABLE_AUTH = False
        mock_storage.check_rate_limit.return_value = (True, 1, time.time() + 60)

        client = TestClient(test_app)
        response = client.get("/test")

        assert response.status_code == 200
        # Verify client_key starts with "ip:"
        call_args = mock_storage.check_rate_limit.call_args[0]
        assert call_args[0].startswith("ip:")

    @pytest.mark.asyncio
    @patch("template_mcp_server.src.middleware.rate_limit.settings")
    async def test_different_clients_separate_limits(
        self, mock_settings, test_app, mock_storage
    ):
        """Test that different clients have separate rate limits."""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_EXCLUDE_PATHS = []
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW_SECONDS = 60
        mock_settings.ENABLE_AUTH = True
        mock_storage.check_rate_limit.return_value = (True, 1, time.time() + 60)

        client = TestClient(test_app)

        # Request from client 1
        client.get("/test", headers={"Authorization": "Bearer token1"})
        client_key_1 = mock_storage.check_rate_limit.call_args[0][0]

        # Request from client 2
        client.get("/test", headers={"Authorization": "Bearer token2"})
        client_key_2 = mock_storage.check_rate_limit.call_args[0][0]

        # Should have different client keys
        assert client_key_1 != client_key_2

    @pytest.mark.asyncio
    @patch("template_mcp_server.src.middleware.rate_limit.settings")
    async def test_reset_time_calculation(self, mock_settings, test_app, mock_storage):
        """Test that reset time is calculated and returned correctly."""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_EXCLUDE_PATHS = []
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW_SECONDS = 60
        reset_time = time.time() + 120
        mock_storage.check_rate_limit.return_value = (True, 1, reset_time)

        client = TestClient(test_app)
        response = client.get("/test")

        assert response.status_code == 200
        assert int(response.headers["X-RateLimit-Reset"]) == int(reset_time)
