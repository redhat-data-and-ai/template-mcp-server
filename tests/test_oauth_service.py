import hashlib
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from template_mcp_server.src.oauth.service import (
    add_token_to_code,
    base64url_encode,
    cleanup_storage,
    create_authorization_code,
    generate_random_string,
    get_storage_service,
    get_storage_status,
    initialize_storage,
    mark_code_as_used,
    register_client,
    retrieve_access_token,
    retrieve_refresh_token,
    revoke_access_token,
    revoke_refresh_token,
    store_access_token,
    store_refresh_token,
    validate_authorization_code,
    validate_client,
    validate_refresh_token,
    verify_code_challenge,
)


class TestUtilityFunctions:
    """Test utility functions in oauth_service."""

    def test_generate_random_string_default_length(self):
        """Test generating random string with default length."""
        result = generate_random_string()
        assert len(result) == 32
        assert all(
            c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
            for c in result
        )

    def test_generate_random_string_custom_length(self):
        """Test generating random string with custom length."""
        result = generate_random_string(16)
        assert len(result) == 16

        result = generate_random_string(64)
        assert len(result) == 64

    def test_generate_random_string_uniqueness(self):
        """Test that generated strings are unique."""
        results = [generate_random_string() for _ in range(100)]
        assert len(set(results)) == 100  # All should be unique

    def test_base64url_encode(self):
        """Test base64 URL-safe encoding."""
        test_data = b"hello world"
        result = base64url_encode(test_data)

        # Should not contain padding
        assert "=" not in result
        # Should be URL-safe
        assert "+" not in result
        assert "/" not in result

    def test_base64url_encode_empty(self):
        """Test base64 URL-safe encoding with empty data."""
        result = base64url_encode(b"")
        assert result == ""

    def test_verify_code_challenge_valid(self):
        """Test PKCE code challenge verification with valid data."""
        code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        # Compute expected challenge
        hash_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        expected_challenge = base64url_encode(hash_bytes)

        result = verify_code_challenge(code_verifier, expected_challenge)
        assert result is True

    def test_verify_code_challenge_invalid(self):
        """Test PKCE code challenge verification with invalid data."""
        code_verifier = "valid_verifier"
        wrong_challenge = "wrong_challenge"

        result = verify_code_challenge(code_verifier, wrong_challenge)
        assert result is False

    def test_verify_code_challenge_error_handling(self):
        """Test PKCE code challenge verification error handling."""
        # Test with invalid input that causes an exception
        with patch(
            "template_mcp_server.src.oauth.service.hashlib.sha256"
        ) as mock_sha256:
            mock_sha256.side_effect = Exception("Hash error")

            result = verify_code_challenge("verifier", "challenge")
            assert result is False


class TestStorageService:
    """Test storage service management."""

    @pytest.mark.asyncio
    async def test_get_storage_service_not_initialized(self):
        """Test getting storage service when not initialized."""
        with patch("template_mcp_server.src.oauth.service._storage_service", None):
            with pytest.raises(RuntimeError, match="Storage service not initialized"):
                await get_storage_service()

    @pytest.mark.asyncio
    async def test_get_storage_service_initialized(self):
        """Test getting storage service when initialized."""
        mock_storage = Mock()
        with patch(
            "template_mcp_server.src.oauth.service._storage_service", mock_storage
        ):
            result = await get_storage_service()
            assert result == mock_storage

    @pytest.mark.asyncio
    async def test_initialize_storage_success(self):
        """Test successful storage initialization."""
        mock_storage = AsyncMock()
        mock_storage.connect = AsyncMock()

        with patch(
            "template_mcp_server.src.oauth.service.StorageService"
        ) as mock_storage_class:
            mock_storage_class.return_value = mock_storage
            with patch(
                "template_mcp_server.src.oauth.service.settings"
            ) as mock_settings:
                mock_settings.POSTGRES_HOST = "localhost"
                mock_settings.POSTGRES_PORT = 5432
                mock_settings.POSTGRES_DB = "testdb"
                mock_settings.POSTGRES_USER = "testuser"
                mock_settings.POSTGRES_PASSWORD = "testpass"
                mock_settings.POSTGRES_POOL_SIZE = 10
                mock_settings.POSTGRES_MAX_CONNECTIONS = 20

                result = await initialize_storage()

                mock_storage_class.assert_called_once_with(
                    host="localhost",
                    port=5432,
                    database="testdb",
                    username="testuser",
                    password="testpass",
                    pool_size=10,
                    max_connections=20,
                )
                mock_storage.connect.assert_called_once()
                assert result == mock_storage

    @pytest.mark.asyncio
    async def test_initialize_storage_missing_config(self):
        """Test storage initialization with missing configuration."""
        with patch("template_mcp_server.src.oauth.service._storage_service", None):
            with patch(
                "template_mcp_server.src.oauth.service.settings"
            ) as mock_settings:
                mock_settings.POSTGRES_HOST = None
                mock_settings.POSTGRES_PORT = 5432
                mock_settings.POSTGRES_DB = "testdb"
                mock_settings.POSTGRES_USER = "testuser"

                with pytest.raises(
                    ValueError, match="Missing required PostgreSQL configuration"
                ):
                    await initialize_storage()

    @pytest.mark.asyncio
    async def test_initialize_storage_already_initialized(self):
        """Test storage initialization when already initialized."""
        mock_storage = Mock()
        with patch(
            "template_mcp_server.src.oauth.service._storage_service", mock_storage
        ):
            result = await initialize_storage()
            assert result == mock_storage

    @pytest.mark.asyncio
    async def test_cleanup_storage_with_service(self):
        """Test storage cleanup when service exists."""
        mock_storage = AsyncMock()
        mock_storage.disconnect = AsyncMock()

        with patch(
            "template_mcp_server.src.oauth.service._storage_service", mock_storage
        ):
            await cleanup_storage()
            mock_storage.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_storage_without_service(self):
        """Test storage cleanup when no service exists."""
        with patch("template_mcp_server.src.oauth.service._storage_service", None):
            # Should not raise any exception
            await cleanup_storage()


class TestClientManagement:
    """Test client management functions."""

    @pytest.mark.asyncio
    async def test_validate_client_success(self):
        """Test successful client validation."""
        mock_storage = AsyncMock()
        mock_storage.get_client.return_value = {
            "id": "client123",
            "secret": "secret123",
            "name": "Test Client",
        }

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await validate_client("client123", "secret123")

            mock_storage.get_client.assert_called_once_with("client123")
            assert result["id"] == "client123"

    @pytest.mark.asyncio
    async def test_validate_client_not_found(self):
        """Test client validation when client not found."""
        mock_storage = AsyncMock()
        mock_storage.get_client.return_value = None

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await validate_client("client123", "secret123")
            assert result is None

    @pytest.mark.asyncio
    async def test_validate_client_wrong_secret(self):
        """Test client validation with wrong secret."""
        mock_storage = AsyncMock()
        mock_storage.get_client.return_value = {
            "id": "client123",
            "secret": "correct_secret",
            "name": "Test Client",
        }

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await validate_client("client123", "wrong_secret")
            assert result is None

    @pytest.mark.asyncio
    async def test_validate_client_no_secret_required(self):
        """Test client validation without secret validation."""
        mock_storage = AsyncMock()
        mock_storage.get_client.return_value = {
            "id": "client123",
            "secret": "secret123",
            "name": "Test Client",
        }

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await validate_client("client123")
            assert result["id"] == "client123"

    @pytest.mark.asyncio
    async def test_register_client_new(self):
        """Test registering a new client."""
        mock_storage = AsyncMock()
        mock_storage.get_client_by_name_and_redirect_uris.return_value = None
        mock_storage.store_client.return_value = True

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            with patch(
                "template_mcp_server.src.oauth.service.generate_random_string"
            ) as mock_gen:
                mock_gen.side_effect = ["client123", "secret123"]

                result = await register_client(
                    "Test Client", ["http://localhost:3000/callback"]
                )

                assert result["client_id"] == "client123"
                assert result["client_secret"] == "secret123"
                assert result["client_name"] == "Test Client"
                mock_storage.store_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_client_existing(self):
        """Test registering an existing client."""
        existing_client = {
            "id": "existing123",
            "secret": "existing_secret",
            "name": "Test Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "read write",
            "created_at": 1234567890,
        }

        mock_storage = AsyncMock()
        mock_storage.get_client_by_name_and_redirect_uris.return_value = existing_client

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await register_client(
                "Test Client", ["http://localhost:3000/callback"]
            )

            assert result["client_id"] == "existing123"
            assert result["client_secret"] == "existing_secret"
            # Should not call store_client for existing client
            mock_storage.store_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_client_storage_failure(self):
        """Test client registration when storage fails."""
        mock_storage = AsyncMock()
        mock_storage.get_client_by_name_and_redirect_uris.return_value = None
        mock_storage.store_client.return_value = False

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            with pytest.raises(
                RuntimeError, match="Failed to persist client registration"
            ):
                await register_client("Test Client", ["http://localhost:3000/callback"])


class TestAuthorizationCodeFlow:
    """Test authorization code flow functions."""

    @pytest.mark.asyncio
    async def test_create_authorization_code(self):
        """Test creating authorization code."""
        mock_storage = AsyncMock()
        mock_storage.store_authorization_code.return_value = True

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            with patch(
                "template_mcp_server.src.oauth.service.generate_random_string",
                return_value="code123",
            ):
                result = await create_authorization_code(
                    "client123",
                    "http://localhost:3000/callback",
                    "read",
                    "challenge123",
                    "S256",
                    "state_123",
                )

                assert result == "code123"
                mock_storage.store_authorization_code.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_token_to_code(self):
        """Test adding token to authorization code."""
        mock_storage = AsyncMock()
        mock_storage.update_authorization_code_token.return_value = True

        token_set = {"access_token": "token123", "refresh_token": "refresh123"}

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            await add_token_to_code("code123", token_set)
            mock_storage.update_authorization_code_token.assert_called_once_with(
                "code123", token_set
            )

    @pytest.mark.asyncio
    async def test_validate_authorization_code_valid(self):
        """Test validating valid authorization code."""
        mock_storage = AsyncMock()
        mock_storage.get_authorization_code.return_value = {
            "client_id": "client123",
            "expires_at": time.time() + 600,  # Expires in 10 minutes
        }

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await validate_authorization_code("code123")
            assert result["client_id"] == "client123"

    @pytest.mark.asyncio
    async def test_validate_authorization_code_expired(self):
        """Test validating expired authorization code."""
        mock_storage = AsyncMock()
        mock_storage.get_authorization_code.return_value = {
            "client_id": "client123",
            "expires_at": time.time() - 600,  # Expired 10 minutes ago
        }

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await validate_authorization_code("code123")
            assert result is None

    @pytest.mark.asyncio
    async def test_validate_authorization_code_not_found(self):
        """Test validating non-existent authorization code."""
        mock_storage = AsyncMock()
        mock_storage.get_authorization_code.return_value = None

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await validate_authorization_code("code123")
            assert result is None

    @pytest.mark.asyncio
    async def test_mark_code_as_used_success(self):
        """Test marking authorization code as used successfully."""
        mock_storage = AsyncMock()
        mock_storage.delete_authorization_code.return_value = True

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            await mark_code_as_used("code123")
            mock_storage.delete_authorization_code.assert_called_once_with("code123")

    @pytest.mark.asyncio
    async def test_mark_code_as_used_failure(self):
        """Test marking authorization code as used when deletion fails."""
        mock_storage = AsyncMock()
        mock_storage.delete_authorization_code.return_value = False

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            await mark_code_as_used("code123")
            mock_storage.delete_authorization_code.assert_called_once_with("code123")


class TestTokenManagement:
    """Test token management functions."""

    @pytest.mark.asyncio
    async def test_store_access_token(self):
        """Test storing access token."""
        mock_storage = AsyncMock()
        mock_storage.store_access_token.return_value = True

        token_data = {
            "client_id": "client123",
            "scope": "read",
            "expires_at": time.time() + 3600,
        }

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await store_access_token("token123", token_data)
            assert result is True
            mock_storage.store_access_token.assert_called_once_with(
                "token123", token_data
            )

    @pytest.mark.asyncio
    async def test_retrieve_access_token(self):
        """Test retrieving access token."""
        mock_storage = AsyncMock()
        mock_storage.get_access_token.return_value = {
            "client_id": "client123",
            "scope": "read",
        }

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await retrieve_access_token("token123")
            assert result["client_id"] == "client123"
            mock_storage.get_access_token.assert_called_once_with("token123")

    @pytest.mark.asyncio
    async def test_store_refresh_token(self):
        """Test storing refresh token."""
        mock_storage = AsyncMock()
        mock_storage.store_refresh_token.return_value = True

        token_data = {"client_id": "client123", "expires_at": time.time() + 86400}

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await store_refresh_token("refresh123", token_data)
            assert result is True
            mock_storage.store_refresh_token.assert_called_once_with(
                "refresh123", token_data
            )

    @pytest.mark.asyncio
    async def test_retrieve_refresh_token(self):
        """Test retrieving refresh token."""
        mock_storage = AsyncMock()
        mock_storage.get_refresh_token.return_value = {"client_id": "client123"}

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await retrieve_refresh_token("refresh123")
            assert result["client_id"] == "client123"
            mock_storage.get_refresh_token.assert_called_once_with("refresh123")

    @pytest.mark.asyncio
    async def test_validate_refresh_token_valid(self):
        """Test validating valid refresh token."""
        mock_storage = AsyncMock()
        mock_storage.get_refresh_token.return_value = {
            "client_id": "client123",
            "expires_at": time.time() + 86400,  # Expires in 24 hours
        }

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await validate_refresh_token("refresh123")
            assert result["client_id"] == "client123"

    @pytest.mark.asyncio
    async def test_validate_refresh_token_expired(self):
        """Test validating expired refresh token."""
        mock_storage = AsyncMock()
        mock_storage.get_refresh_token.return_value = {
            "client_id": "client123",
            "expires_at": time.time() - 3600,  # Expired 1 hour ago
        }

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await validate_refresh_token("refresh123")
            assert result is None

    @pytest.mark.asyncio
    async def test_validate_refresh_token_not_found(self):
        """Test validating non-existent refresh token."""
        mock_storage = AsyncMock()
        mock_storage.get_refresh_token.return_value = None

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await validate_refresh_token("refresh123")
            assert result is None

    @pytest.mark.asyncio
    async def test_revoke_access_token(self):
        """Test revoking access token."""
        mock_storage = AsyncMock()
        mock_storage.delete_access_token.return_value = True

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await revoke_access_token("token123")
            assert result is True
            mock_storage.delete_access_token.assert_called_once_with("token123")

    @pytest.mark.asyncio
    async def test_revoke_refresh_token(self):
        """Test revoking refresh token."""
        mock_storage = AsyncMock()
        mock_storage.delete_refresh_token.return_value = True

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await revoke_refresh_token("refresh123")
            assert result is True
            mock_storage.delete_refresh_token.assert_called_once_with("refresh123")

    @pytest.mark.asyncio
    async def test_get_storage_status(self):
        """Test getting storage status."""
        mock_storage = AsyncMock()
        mock_storage.get_status.return_value = {"healthy": True, "type": "postgresql"}

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            result = await get_storage_status()
            assert result["healthy"] is True
            mock_storage.get_status.assert_called_once()


class TestOAuthServiceIntegration:
    """Integration tests for OAuth service."""

    @pytest.mark.asyncio
    async def test_full_oauth_flow(self):
        """Test a complete OAuth flow."""
        mock_storage = AsyncMock()

        # Setup storage responses
        mock_storage.get_client_by_name_and_redirect_uris.return_value = None
        mock_storage.store_client.return_value = True
        mock_storage.get_client.return_value = {
            "id": "client123",
            "secret": "secret123",
            "name": "Test Client",
        }
        mock_storage.store_authorization_code.return_value = True
        mock_storage.get_authorization_code.return_value = {
            "client_id": "client123",
            "expires_at": time.time() + 600,
            "code_challenge": "challenge123",
            "redirect_uri": "http://localhost:3000/callback",
        }
        mock_storage.delete_authorization_code.return_value = True
        mock_storage.store_access_token.return_value = True
        mock_storage.store_refresh_token.return_value = True

        with patch(
            "template_mcp_server.src.oauth.service.get_storage_service",
            return_value=mock_storage,
        ):
            with patch(
                "template_mcp_server.src.oauth.service.generate_random_string"
            ) as mock_gen:
                mock_gen.side_effect = ["client123", "secret123", "code123"]

                # 1. Register client
                client = await register_client(
                    "Test Client", ["http://localhost:3000/callback"]
                )
                assert client["client_id"] == "client123"

                # 2. Validate client
                validated_client = await validate_client("client123", "secret123")
                assert validated_client is not None

                # 3. Create authorization code
                auth_code = await create_authorization_code(
                    "client123",
                    "http://localhost:3000/callback",
                    "read",
                    "challenge123",
                    "S256",
                    "state_123",
                )
                assert auth_code == "code123"

                # 4. Validate authorization code
                code_data = await validate_authorization_code("code123")
                assert code_data["client_id"] == "client123"

                # 5. Mark code as used
                await mark_code_as_used("code123")
                mock_storage.delete_authorization_code.assert_called_with("code123")


class TestOAuthServiceEdgeCases:
    """Test OAuth service edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_validate_authorization_code_expired(self):
        """Test validation of expired authorization code."""
        from template_mcp_server.src.oauth.service import OAuthService
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_authorization_code.return_value = {
            "client_id": "test_client",
            "redirect_uri": "http://localhost:3000/callback",
            "scope": "read",
            "expires_at": time.time() - 3600,  # Expired 1 hour ago
        }

        oauth_service = OAuthService(mock_storage)
        result = await oauth_service.validate_authorization_code("expired_code")

        assert result is None
        mock_storage.get_authorization_code.assert_called_once_with("expired_code")

    @pytest.mark.asyncio
    async def test_validate_authorization_code_not_found(self):
        """Test validation of non-existent authorization code."""
        from template_mcp_server.src.oauth.service import OAuthService
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_authorization_code.return_value = None

        oauth_service = OAuthService(mock_storage)
        result = await oauth_service.validate_authorization_code("nonexistent_code")

        assert result is None
        mock_storage.get_authorization_code.assert_called_once_with("nonexistent_code")

    @pytest.mark.asyncio
    async def test_validate_authorization_code_storage_error(self):
        """Test validation when storage service fails."""
        from template_mcp_server.src.oauth.service import OAuthService
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_authorization_code.side_effect = Exception(
            "Database connection error"
        )

        oauth_service = OAuthService(mock_storage)

        with pytest.raises(Exception, match="Database connection error"):
            await oauth_service.validate_authorization_code("test_code")

    @pytest.mark.asyncio
    async def test_validate_refresh_token_expired(self):
        """Test validation of expired refresh token."""
        from template_mcp_server.src.oauth.service import OAuthService
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_refresh_token.return_value = {
            "client_id": "test_client",
            "scope": "read",
            "expires_at": time.time() - 3600,  # Expired 1 hour ago
        }

        oauth_service = OAuthService(mock_storage)
        result = await oauth_service.validate_refresh_token("expired_refresh_token")

        assert result is None
        mock_storage.get_refresh_token.assert_called_once_with("expired_refresh_token")

    @pytest.mark.asyncio
    async def test_validate_refresh_token_missing_expiry(self):
        """Test validation of refresh token without expiry time (should not expire)."""
        from template_mcp_server.src.oauth.service import OAuthService
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_refresh_token.return_value = {
            "client_id": "test_client",
            "scope": "read",
            # No expires_at field
        }

        oauth_service = OAuthService(mock_storage)
        result = await oauth_service.validate_refresh_token("refresh_token_no_expiry")

        assert result is not None
        assert result["client_id"] == "test_client"
        assert result["scope"] == "read"

    @pytest.mark.asyncio
    async def test_validate_client_with_secret_mismatch(self):
        """Test client validation with mismatched secret."""
        from template_mcp_server.src.oauth.service import OAuthService
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client.return_value = {
            "id": "test_client",
            "secret": "correct_secret",
            "name": "Test Client",
        }

        oauth_service = OAuthService(mock_storage)
        result = await oauth_service.validate_client("test_client", "wrong_secret")

        assert result is None
        mock_storage.get_client.assert_called_once_with("test_client")

    @pytest.mark.asyncio
    async def test_validate_client_no_secret_in_store(self):
        """Test client validation when stored client has no secret."""
        from template_mcp_server.src.oauth.service import OAuthService
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client.return_value = {
            "id": "test_client",
            "name": "Test Client",
            # No secret field
        }

        oauth_service = OAuthService(mock_storage)
        result = await oauth_service.validate_client("test_client", "any_secret")

        assert result is not None
        assert result["id"] == "test_client"
        assert result["name"] == "Test Client"

    @pytest.mark.asyncio
    async def test_create_authorization_code_with_defaults(self):
        """Test creating authorization code with default values."""
        from template_mcp_server.src.oauth.service import OAuthService
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.store_authorization_code.return_value = True

        oauth_service = OAuthService(mock_storage)

        with patch(
            "template_mcp_server.src.oauth.service.generate_random_string"
        ) as mock_gen:
            mock_gen.return_value = "generated_code"

            result = await oauth_service.create_authorization_code(
                client_id="test_client",
                redirect_uri="http://localhost:3000/callback",
                scope=None,  # Should default to "read"
                code_challenge="test_challenge",
                code_challenge_method="S256",
                state="state_123",
            )

            assert result == "generated_code"
            mock_storage.store_authorization_code.assert_called_once()
            stored_data = mock_storage.store_authorization_code.call_args[0][1]
            assert stored_data["scope"] == "read"

    @pytest.mark.asyncio
    async def test_register_client_storage_failure(self):
        """Test client registration when storage fails."""
        from template_mcp_server.src.oauth.service import OAuthService
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client_by_name_and_redirect_uris.return_value = None
        mock_storage.store_client.return_value = False  # Storage failure

        oauth_service = OAuthService(mock_storage)

        with pytest.raises(RuntimeError, match="Failed to persist client registration"):
            await oauth_service.register_client(
                client_name="Test Client",
                redirect_uris=["http://localhost:3000/callback"],
            )

    @pytest.mark.asyncio
    async def test_register_client_returns_existing(self):
        """Test that existing client is returned instead of creating new one."""
        from template_mcp_server.src.oauth.service import OAuthService
        from template_mcp_server.src.storage.storage_service import StorageService

        existing_client = {
            "id": "existing_client_id",
            "secret": "existing_secret",
            "name": "Test Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "read write",
            "created_at": time.time() - 86400,  # Created yesterday
        }

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client_by_name_and_redirect_uris.return_value = existing_client

        oauth_service = OAuthService(mock_storage)

        result = await oauth_service.register_client(
            client_name="Test Client", redirect_uris=["http://localhost:3000/callback"]
        )

        assert result["client_id"] == "existing_client_id"
        assert result["client_secret"] == "existing_secret"
        # Should not call store_client since existing client was found
        mock_storage.store_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_mark_code_as_used_storage_failure(self):
        """Test marking authorization code as used when storage fails."""
        from template_mcp_server.src.oauth.service import OAuthService
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.delete_authorization_code.side_effect = Exception("Storage error")

        oauth_service = OAuthService(mock_storage)

        with pytest.raises(Exception, match="Storage error"):
            await oauth_service.mark_code_as_used("test_code")

    @pytest.mark.asyncio
    async def test_token_operations_with_storage_failures(self):
        """Test various token operations when storage fails."""
        from template_mcp_server.src.oauth.service import OAuthService
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        oauth_service = OAuthService(mock_storage)

        # Test store_access_token failure
        mock_storage.store_access_token.side_effect = Exception("Storage error")
        with pytest.raises(Exception, match="Storage error"):
            await oauth_service.store_access_token("token", {"data": "test"})

        # Reset for next test
        mock_storage.reset_mock()
        mock_storage.store_access_token.side_effect = None

        # Test retrieve_access_token failure
        mock_storage.get_access_token.side_effect = Exception("Storage error")
        with pytest.raises(Exception, match="Storage error"):
            await oauth_service.retrieve_access_token("token")

        # Reset for next test
        mock_storage.reset_mock()
        mock_storage.get_access_token.side_effect = None

        # Test revoke_access_token failure
        mock_storage.delete_access_token.side_effect = Exception("Storage error")
        with pytest.raises(Exception, match="Storage error"):
            await oauth_service.revoke_access_token("token")


class TestOAuthServiceConcurrency:
    """Test OAuth service under concurrent access scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_authorization_code_validation(self):
        """Test concurrent validation of the same authorization code."""
        import asyncio

        from template_mcp_server.src.oauth.service import OAuthService
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_authorization_code.return_value = {
            "client_id": "test_client",
            "redirect_uri": "http://localhost:3000/callback",
            "scope": "read",
            "expires_at": time.time() + 600,  # Valid for 10 minutes
        }

        oauth_service = OAuthService(mock_storage)

        # Simulate concurrent validation attempts
        tasks = [
            oauth_service.validate_authorization_code("same_code") for _ in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed since code is valid
        assert all(result is not None for result in results)
        assert all(result["client_id"] == "test_client" for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_client_registration(self):
        """Test concurrent registration of clients with same name and redirect URIs."""
        import asyncio

        from template_mcp_server.src.oauth.service import OAuthService
        from template_mcp_server.src.storage.storage_service import StorageService

        # First call returns None (no existing client), subsequent calls return existing client
        existing_client = {
            "id": "first_client_id",
            "secret": "first_secret",
            "name": "Test Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "read write",
            "created_at": time.time(),
        }

        mock_storage = AsyncMock(spec=StorageService)

        # Simulate race condition: first call finds no existing client, others find existing
        call_count = 0

        async def mock_get_existing(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # First call: no existing client
            else:
                return existing_client  # Subsequent calls: existing client found

        mock_storage.get_client_by_name_and_redirect_uris.side_effect = (
            mock_get_existing
        )
        mock_storage.store_client.return_value = True

        oauth_service = OAuthService(mock_storage)

        # Simulate concurrent registration attempts
        tasks = [
            oauth_service.register_client(
                client_name="Test Client",
                redirect_uris=["http://localhost:3000/callback"],
            )
            for _ in range(3)
        ]

        with patch(
            "template_mcp_server.src.oauth.service.generate_random_string"
        ) as mock_gen:
            mock_gen.side_effect = ["new_client_id", "new_secret"]

            results = await asyncio.gather(*tasks)

        # At least one should create a new client, others should return existing
        assert len(results) == 3
        assert all("client_id" in result for result in results)


class TestUtilityFunctionsEdgeCases:
    """Test utility functions with edge cases."""

    def test_generate_random_string_zero_length(self):
        """Test generating random string with zero length."""
        result = generate_random_string(0)
        assert result == ""

    def test_generate_random_string_large_length(self):
        """Test generating random string with very large length."""
        result = generate_random_string(1000)
        assert len(result) == 1000
        # Ensure it contains only valid characters
        valid_chars = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
        )
        assert all(c in valid_chars for c in result)

    def test_base64url_encode_empty_bytes(self):
        """Test base64url encoding with empty bytes."""
        result = base64url_encode(b"")
        assert result == ""

    def test_base64url_encode_special_characters(self):
        """Test base64url encoding with special characters."""
        # Test data that would normally contain padding
        test_data = b"hello world!"
        result = base64url_encode(test_data)

        # Should not contain padding characters
        assert "=" not in result
        # Should not contain standard base64 characters that are URL-unsafe
        assert "+" not in result
        assert "/" not in result

    def test_verify_code_challenge_edge_cases(self):
        """Test PKCE code challenge verification with edge cases."""
        # Test with empty strings
        assert not verify_code_challenge("", "")

        # Test with None values (should handle gracefully)
        assert not verify_code_challenge(None, "challenge")
        assert not verify_code_challenge("verifier", None)

        # Test with invalid base64url
        assert not verify_code_challenge("verifier", "invalid_challenge_!@#")

        # Test with extremely long verifier
        long_verifier = "a" * 128  # Maximum allowed length
        expected_challenge = base64url_encode(
            hashlib.sha256(long_verifier.encode()).digest()
        )
        assert verify_code_challenge(long_verifier, expected_challenge)

    def test_verify_code_challenge_different_encodings(self):
        """Test PKCE verification with different string encodings."""
        # Test with Unicode characters
        unicode_verifier = "café_verifier_🔑"
        expected_challenge = base64url_encode(
            hashlib.sha256(unicode_verifier.encode("utf-8")).digest()
        )
        assert verify_code_challenge(unicode_verifier, expected_challenge)

    def test_verify_code_challenge_case_sensitivity(self):
        """Test that PKCE verification is case sensitive."""
        verifier = "TestVerifier123"
        challenge = base64url_encode(hashlib.sha256(verifier.encode()).digest())

        # Should work with exact match
        assert verify_code_challenge(verifier, challenge)

        # Should fail with different case
        assert not verify_code_challenge(verifier.lower(), challenge)
        assert not verify_code_challenge(verifier.upper(), challenge)
