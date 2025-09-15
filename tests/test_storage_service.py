import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from template_mcp_server.src.storage.storage_service import StorageService


class TestStorageServiceInit:
    """Test StorageService initialization."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        service = StorageService()

        assert service.host == "localhost"
        assert service.port == 5432
        assert service.database == "postgres"
        assert service.username == "postgres"
        assert service.password == ""
        assert service.pool_size == 10
        assert service.max_connections == 20
        assert service.pool is None

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        service = StorageService(
            host="custom_host",
            port=5433,
            database="custom_db",
            username="custom_user",
            password="custom_pass",
            pool_size=5,
            max_connections=15,
        )

        assert service.host == "custom_host"
        assert service.port == 5433
        assert service.database == "custom_db"
        assert service.username == "custom_user"
        assert service.password == "custom_pass"
        assert service.pool_size == 5
        assert service.max_connections == 15


class TestStorageServiceConnection:
    """Test StorageService connection management."""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful database connection."""
        service = StorageService()
        mock_pool = AsyncMock()

        async def mock_create_pool(*args, **kwargs):
            return mock_pool

        with patch(
            "template_mcp_server.src.storage.storage_service.asyncpg.create_pool",
            side_effect=mock_create_pool,
        ) as mock_create:
            with patch.object(
                service, "_create_table", new_callable=AsyncMock
            ) as mock_create_table:
                await service.connect()

                mock_create.assert_called_once()
                mock_create_table.assert_called_once()
                assert service.pool == mock_pool

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test database connection failure."""
        service = StorageService()

        with patch(
            "template_mcp_server.src.storage.storage_service.asyncpg.create_pool",
            side_effect=Exception("Connection failed"),
        ):
            with pytest.raises(ConnectionError, match="PostgreSQL connection failed"):
                await service.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test database disconnection."""
        service = StorageService()
        mock_pool = AsyncMock()
        service.pool = mock_pool

        await service.disconnect()

        mock_pool.close.assert_called_once()
        assert service.pool is None

    @pytest.mark.asyncio
    async def test_disconnect_no_pool(self):
        """Test disconnection when no pool exists."""
        service = StorageService()
        # Should not raise exception
        await service.disconnect()

    @pytest.mark.asyncio
    async def test_is_healthy_with_pool(self):
        """Test health check with active pool."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()

        # Create a proper async context manager mock
        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire

        service.pool = mock_pool

        result = await service.is_healthy()

        assert result is True
        mock_conn.execute.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_is_healthy_no_pool(self):
        """Test health check without pool."""
        service = StorageService()

        result = await service.is_healthy()
        assert result is False

    @pytest.mark.asyncio
    async def test_is_healthy_exception(self):
        """Test health check with exception."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = Exception("Query failed")
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        result = await service.is_healthy()
        assert result is False


class TestStorageServiceTables:
    """Test table creation and management."""

    @pytest.mark.asyncio
    async def test_create_table_success(self):
        """Test successful table creation."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        await service._create_table()

        # Should call execute multiple times for table and index creation
        assert mock_conn.execute.call_count >= 4  # 4 tables + indexes

    @pytest.mark.asyncio
    async def test_create_table_no_pool(self):
        """Test table creation without pool."""
        service = StorageService()

        with pytest.raises(RuntimeError, match="Not connected to PostgreSQL"):
            await service._create_table()


class TestStorageServiceStatus:
    """Test storage service status."""

    @pytest.mark.asyncio
    async def test_get_status_healthy(self):
        """Test getting status when healthy."""
        service = StorageService("test_host", 5433, "test_db")
        mock_pool = Mock()
        mock_pool.get_size.return_value = 5
        service.pool = mock_pool

        with patch.object(service, "is_healthy", return_value=True):
            result = await service.get_status()

            assert result["type"] == "postgresql"
            assert result["healthy"] is True
            assert result["host"] == "test_host"
            assert result["port"] == 5433
            assert result["database"] == "test_db"
            assert result["pool_size"] == 5
            assert result["pool_max_size"] == 20

    @pytest.mark.asyncio
    async def test_get_status_unhealthy(self):
        """Test getting status when unhealthy."""
        service = StorageService()

        with patch.object(service, "is_healthy", return_value=False):
            result = await service.get_status()

            assert result["type"] == "postgresql"
            assert result["healthy"] is False

    @pytest.mark.asyncio
    async def test_get_status_exception(self):
        """Test getting status with exception."""
        service = StorageService()

        with patch.object(service, "is_healthy", side_effect=Exception("Status error")):
            result = await service.get_status()

            assert result["type"] == "postgresql"
            assert result["healthy"] is False
            assert "Status error" in result["error"]


class TestClientMethods:
    """Test OAuth client methods."""

    @pytest.mark.asyncio
    async def test_get_client_by_name_and_redirect_uris_found(self):
        """Test finding client by name and redirect URIs."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_result = {
            "client_id": "client123",
            "client_secret": "secret123",
            "client_name": "Test Client",
            "redirect_uris": '["http://localhost:3000"]',
            "grant_types": '["authorization_code"]',
            "response_types": '["code"]',
            "scope": "read write",
            "created_at": datetime.now(timezone.utc),
        }
        mock_conn.fetchrow.return_value = mock_result
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        result = await service.get_client_by_name_and_redirect_uris(
            "Test Client", ["http://localhost:3000"]
        )

        assert result["id"] == "client123"
        assert result["name"] == "Test Client"
        assert result["redirect_uris"] == ["http://localhost:3000"]

    @pytest.mark.asyncio
    async def test_get_client_by_name_and_redirect_uris_not_found(self):
        """Test not finding client by name and redirect URIs."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        result = await service.get_client_by_name_and_redirect_uris(
            "Non-existent Client", ["http://localhost:3000"]
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_client_by_name_and_redirect_uris_no_pool(self):
        """Test finding client without pool."""
        service = StorageService()

        result = await service.get_client_by_name_and_redirect_uris(
            "Test Client", ["http://localhost:3000"]
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_client_by_name_and_redirect_uris_exception(self):
        """Test finding client with exception."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = Exception("Query error")
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        result = await service.get_client_by_name_and_redirect_uris(
            "Test Client", ["http://localhost:3000"]
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_store_client_success(self):
        """Test successful client storage."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        client_data = {
            "id": "client123",
            "secret": "secret123",
            "name": "Test Client",
            "redirect_uris": ["http://localhost:3000"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "read write",
        }

        result = await service.store_client(client_data)

        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_client_no_pool(self):
        """Test client storage without pool."""
        service = StorageService()

        client_data = {"id": "client123", "secret": "secret123"}
        result = await service.store_client(client_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_store_client_exception(self):
        """Test client storage with exception."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = Exception("Insert error")
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        client_data = {"id": "client123", "secret": "secret123"}
        result = await service.store_client(client_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_client_success(self):
        """Test successful client retrieval."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_result = {
            "client_id": "client123",
            "client_secret": "secret123",
            "client_name": "Test Client",
            "redirect_uris": '["http://localhost:3000"]',
            "grant_types": '["authorization_code"]',
            "response_types": '["code"]',
            "scope": "read write",
            "created_at": datetime.now(timezone.utc),
        }
        mock_conn.fetchrow.return_value = mock_result
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        result = await service.get_client("client123")

        assert result["id"] == "client123"
        assert result["name"] == "Test Client"

    @pytest.mark.asyncio
    async def test_get_client_not_found(self):
        """Test client retrieval when not found."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        result = await service.get_client("client123")

        assert result is None


class TestAuthorizationCodeMethods:
    """Test authorization code methods."""

    @pytest.mark.asyncio
    async def test_store_authorization_code_success(self):
        """Test successful authorization code storage."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        code_data = {
            "client_id": "client123",
            "redirect_uri": "http://localhost:3000/callback",
            "scope": "read",
            "code_challenge": "challenge123",
            "code_challenge_method": "S256",
            "expires_at": time.time() + 600,
            "state": "state_123",
        }

        result = await service.store_authorization_code("code123", code_data)

        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_authorization_code_success(self):
        """Test successful authorization code retrieval."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_result = {
            "code": "code123",
            "client_id": "client123",
            "redirect_uri": "http://localhost:3000/callback",
            "scope": "read",
            "code_challenge": "challenge123",
            "code_challenge_method": "S256",
            "snowflake_token": '{"access_token": "token123"}',
            "expires_at": datetime.now(timezone.utc),
            "state": "state_123",
        }
        mock_conn.fetchrow.return_value = mock_result
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        result = await service.get_authorization_code("code123")

        assert result["client_id"] == "client123"
        assert result["snowflake_token"]["access_token"] == "token123"

    @pytest.mark.asyncio
    async def test_get_authorization_code_no_snowflake_token(self):
        """Test authorization code retrieval without snowflake token."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_result = {
            "code": "code123",
            "client_id": "client123",
            "redirect_uri": "http://localhost:3000/callback",
            "scope": "read",
            "code_challenge": "challenge123",
            "code_challenge_method": "S256",
            "snowflake_token": None,
            "expires_at": datetime.now(timezone.utc),
            "state": "state_123",
        }
        mock_conn.fetchrow.return_value = mock_result
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        result = await service.get_authorization_code("code123")

        assert result["client_id"] == "client123"
        assert result["snowflake_token"] is None

    @pytest.mark.asyncio
    async def test_update_authorization_code_token_success(self):
        """Test successful authorization code token update."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        snowflake_token = {"access_token": "token123", "refresh_token": "refresh123"}

        result = await service.update_authorization_code_token(
            "code123", snowflake_token
        )

        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_authorization_code_success(self):
        """Test successful authorization code deletion."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 1"
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        result = await service.delete_authorization_code("code123")

        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_authorization_code_not_found(self):
        """Test authorization code deletion when not found."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 0"
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        result = await service.delete_authorization_code("code123")

        assert result is False


class TestAccessTokenMethods:
    """Test access token methods."""

    @pytest.mark.asyncio
    async def test_store_access_token_success(self):
        """Test successful access token storage."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        token_data = {
            "client_id": "client123",
            "scope": "read write",
            "expires_at": time.time() + 3600,
        }

        result = await service.store_access_token("token123", token_data)

        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_access_token_success(self):
        """Test successful access token retrieval."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_result = {
            "token": "token123",
            "client_id": "client123",
            "scope": "read write",
            "token_type": "Bearer",
            "expires_at": datetime.now(timezone.utc),
        }
        mock_conn.fetchrow.return_value = mock_result
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        result = await service.get_access_token("token123")

        assert result["client_id"] == "client123"
        assert result["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_delete_access_token_success(self):
        """Test successful access token deletion."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 1"
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        result = await service.delete_access_token("token123")

        assert result is True
        mock_conn.execute.assert_called_once()


class TestRefreshTokenMethods:
    """Test refresh token methods."""

    @pytest.mark.asyncio
    async def test_store_refresh_token_success(self):
        """Test successful refresh token storage."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        token_data = {
            "client_id": "client123",
            "access_token": "access123",
            "scope": "read write",
            "expires_at": time.time() + 86400,
        }

        result = await service.store_refresh_token("refresh123", token_data)

        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_refresh_token_success(self):
        """Test successful refresh token retrieval."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_result = {
            "token": "refresh123",
            "client_id": "client123",
            "access_token": "access123",
            "scope": "read write",
            "expires_at": datetime.now(timezone.utc),
        }
        mock_conn.fetchrow.return_value = mock_result
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        result = await service.get_refresh_token("refresh123")

        assert result["client_id"] == "client123"
        assert result["access_token"] == "access123"

    @pytest.mark.asyncio
    async def test_delete_refresh_token_success(self):
        """Test successful refresh token deletion."""
        service = StorageService()
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 1"
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        result = await service.delete_refresh_token("refresh123")

        assert result is True
        mock_conn.execute.assert_called_once()


class TestStorageServiceIntegration:
    """Integration tests for StorageService."""

    @pytest.mark.asyncio
    async def test_full_oauth_storage_flow(self):
        """Test a complete OAuth storage flow."""
        service = StorageService()

        # Mock database interactions
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        def acquire():
            return AsyncContextManagerMock(mock_conn)

        mock_pool.acquire = acquire
        service.pool = mock_pool

        # Setup different responses for different operations
        def mock_fetchrow_side_effect(*args):
            query = args[0]
            if "oauth_clients" in query and "WHERE client_id" in query:
                # This is a get_client call
                return {
                    "client_id": "client123",
                    "client_secret": "secret123",
                    "client_name": "Test Client",
                    "redirect_uris": '["http://localhost:3000"]',
                    "grant_types": '["authorization_code"]',
                    "response_types": '["code"]',
                    "scope": "read write",
                    "created_at": datetime.now(timezone.utc),
                }
            elif (
                "oauth_clients" in query
                and "client_name" in query
                and "redirect_uris" in query
            ):
                # This is a get_client_by_name_and_redirect_uris call
                return None  # No existing client
            elif "oauth_authorization_codes" in query:
                return {
                    "client_id": "client123",
                    "redirect_uri": "http://localhost:3000",
                    "scope": "read",
                    "code_challenge": "challenge123",
                    "code_challenge_method": "S256",
                    "snowflake_token": None,
                    "expires_at": datetime.now(timezone.utc),
                    "state": "test_state_123",
                }
            return None

        mock_conn.fetchrow.side_effect = mock_fetchrow_side_effect
        mock_conn.execute.return_value = "DELETE 1"

        # Test client operations
        client_data = {
            "id": "client123",
            "secret": "secret123",
            "name": "Test Client",
            "redirect_uris": ["http://localhost:3000"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "read write",
        }

        # Store client
        result = await service.store_client(client_data)
        assert result is True

        # Get client
        client = await service.get_client("client123")
        assert client["id"] == "client123"

        # Test authorization code operations
        code_data = {
            "client_id": "client123",
            "redirect_uri": "http://localhost:3000",
            "scope": "read",
            "code_challenge": "challenge123",
            "code_challenge_method": "S256",
            "expires_at": time.time() + 600,
            "state": "test_state_123",
        }

        # Store authorization code
        result = await service.store_authorization_code("code123", code_data)
        assert result is True

        # Get authorization code
        code = await service.get_authorization_code("code123")
        assert code["client_id"] == "client123"

        # Delete authorization code
        result = await service.delete_authorization_code("code123")
        assert result is True
