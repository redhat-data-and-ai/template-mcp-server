import hashlib
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from template_mcp_server.src.oauth.service import (
    OAuthService,
    base64url_encode,
    cleanup_storage,
    generate_random_string,
    initialize_storage,
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


class TestStorageLifecycle:
    """Test storage initialization and cleanup."""

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
            await cleanup_storage()


class TestInferApplicationType:
    """Test _infer_application_type for SEP-837 edge cases."""

    def test_loopback_localhost(self):
        """Test localhost redirect URIs infer native."""
        from template_mcp_server.src.oauth.service import _infer_application_type

        assert _infer_application_type(["http://localhost:3000/callback"]) == "native"

    def test_loopback_127_0_0_1(self):
        """Test 127.0.0.1 redirect URIs infer native."""
        from template_mcp_server.src.oauth.service import _infer_application_type

        assert _infer_application_type(["http://127.0.0.1:8080/callback"]) == "native"

    def test_loopback_ipv6(self):
        """Test IPv6 loopback redirect URIs infer native."""
        from template_mcp_server.src.oauth.service import _infer_application_type

        assert _infer_application_type(["http://[::1]:8080/callback"]) == "native"

    def test_custom_scheme(self):
        """Test custom scheme redirect URIs infer native."""
        from template_mcp_server.src.oauth.service import _infer_application_type

        assert _infer_application_type(["myapp://callback"]) == "native"

    def test_non_loopback_https(self):
        """Test non-loopback HTTPS redirect URIs infer web."""
        from template_mcp_server.src.oauth.service import _infer_application_type

        assert _infer_application_type(["https://example.com/callback"]) == "web"

    def test_mixed_loopback_and_non_loopback(self):
        """Test mixed URIs: any non-loopback HTTP/HTTPS makes it web."""
        from template_mcp_server.src.oauth.service import _infer_application_type

        result = _infer_application_type(
            [
                "http://localhost:3000/callback",
                "https://example.com/callback",
            ]
        )
        assert result == "web"

    def test_empty_redirect_uris(self):
        """Test empty redirect URIs list infers native."""
        from template_mcp_server.src.oauth.service import _infer_application_type

        assert _infer_application_type([]) == "native"


class TestGetCurrentIssuer:
    """Test get_current_issuer for SEP-2352 issuer derivation."""

    def test_valid_endpoint(self):
        """Test issuer derivation from valid MCP_HOST_ENDPOINT."""
        from template_mcp_server.src.oauth.service import get_current_issuer

        with patch("template_mcp_server.src.oauth.service.settings") as mock_settings:
            mock_settings.OAUTH_ISSUER = None
            mock_settings.MCP_HOST_ENDPOINT = "https://mcp.example.com:8443/path"
            result = get_current_issuer()
            assert result == "https://mcp.example.com:8443"

    def test_fallback_on_none(self):
        """Test fallback when MCP_HOST_ENDPOINT is None."""
        from template_mcp_server.src.oauth.service import get_current_issuer

        with patch("template_mcp_server.src.oauth.service.settings") as mock_settings:
            mock_settings.OAUTH_ISSUER = None
            mock_settings.MCP_HOST_ENDPOINT = None
            result = get_current_issuer()
            assert result == "http://localhost:5001"

    def test_fallback_on_empty(self):
        """Test fallback when MCP_HOST_ENDPOINT is empty string."""
        from template_mcp_server.src.oauth.service import get_current_issuer

        with patch("template_mcp_server.src.oauth.service.settings") as mock_settings:
            mock_settings.OAUTH_ISSUER = None
            mock_settings.MCP_HOST_ENDPOINT = ""
            result = get_current_issuer()
            assert result == "http://localhost:5001"

    def test_fallback_on_invalid_scheme(self):
        """Test fallback when MCP_HOST_ENDPOINT has invalid scheme."""
        from template_mcp_server.src.oauth.service import get_current_issuer

        with patch("template_mcp_server.src.oauth.service.settings") as mock_settings:
            mock_settings.OAUTH_ISSUER = None
            mock_settings.MCP_HOST_ENDPOINT = "ftp://example.com"
            result = get_current_issuer()
            assert result == "http://localhost:5001"

    def test_strips_path(self):
        """Test that path is stripped from the issuer."""
        from template_mcp_server.src.oauth.service import get_current_issuer

        with patch("template_mcp_server.src.oauth.service.settings") as mock_settings:
            mock_settings.MCP_HOST_ENDPOINT = "http://localhost:5001/some/path"
            mock_settings.OAUTH_ISSUER = None
            result = get_current_issuer()
            assert result == "http://localhost:5001"

    def test_explicit_oauth_issuer_takes_precedence(self):
        """Test that OAUTH_ISSUER setting overrides MCP_HOST_ENDPOINT derivation."""
        from template_mcp_server.src.oauth.service import get_current_issuer

        with patch("template_mcp_server.src.oauth.service.settings") as mock_settings:
            mock_settings.OAUTH_ISSUER = "https://auth.example.com"
            mock_settings.MCP_HOST_ENDPOINT = "https://mcp.other.com:8443/path"
            result = get_current_issuer()
            assert result == "https://auth.example.com"

    def test_urlparse_exception_returns_safe_default(self):
        """Test that urlparse exception falls back to safe default."""
        from template_mcp_server.src.oauth.service import get_current_issuer

        with patch("template_mcp_server.src.oauth.service.settings") as mock_settings:
            mock_settings.OAUTH_ISSUER = None
            mock_settings.MCP_HOST_ENDPOINT = "https://valid.example.com"
            with patch(
                "template_mcp_server.src.oauth.service.urlparse",
                side_effect=ValueError("parse error"),
            ):
                result = get_current_issuer()
                assert result == "http://localhost:5001"

    def test_fallback_on_space_in_netloc(self):
        """Test fallback when netloc contains spaces."""
        from template_mcp_server.src.oauth.service import get_current_issuer

        with patch("template_mcp_server.src.oauth.service.settings") as mock_settings:
            mock_settings.OAUTH_ISSUER = None
            mock_settings.MCP_HOST_ENDPOINT = "https://invalid host.com"
            result = get_current_issuer()
            assert result == "http://localhost:5001"

    def test_fallback_on_whitespace_scheme(self):
        """Test fallback when scheme is whitespace."""
        from template_mcp_server.src.oauth.service import get_current_issuer

        with patch("template_mcp_server.src.oauth.service.settings") as mock_settings:
            mock_settings.OAUTH_ISSUER = None
            mock_settings.MCP_HOST_ENDPOINT = "http://example.com"
            with patch(
                "template_mcp_server.src.oauth.service.urlparse"
            ) as mock_urlparse:
                mock_result = Mock()
                mock_result.scheme = "http "
                mock_result.netloc = "example.com"
                mock_urlparse.return_value = mock_result
                result = get_current_issuer()
                assert result == "http://localhost:5001"


class TestOAuthServiceMethods:
    """Test OAuthService class methods directly."""

    @pytest.mark.asyncio
    async def test_validate_client_success(self):
        """Test successful client validation with matching secret."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client.return_value = {
            "id": "client123",
            "secret": "secret123",
            "name": "Test Client",
        }

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.validate_client("client123", "secret123")

        assert result["id"] == "client123"
        mock_storage.get_client.assert_called_once_with(
            "client123", "http://localhost:5001"
        )

    @pytest.mark.asyncio
    async def test_validate_client_not_found(self):
        """Test client validation when client not found."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client.return_value = None

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.validate_client("client123", "secret123")
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_client_with_secret_mismatch(self):
        """Test client validation with mismatched secret."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client.return_value = {
            "id": "test_client",
            "secret": "correct_secret",
            "name": "Test Client",
        }

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.validate_client("test_client", "wrong_secret")

        assert result is None
        mock_storage.get_client.assert_called_once_with(
            "test_client", "http://localhost:5001"
        )

    @pytest.mark.asyncio
    async def test_validate_client_no_secret_in_store(self):
        """Test client validation when stored client has no secret."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client.return_value = {
            "id": "test_client",
            "name": "Test Client",
        }

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.validate_client("test_client", "any_secret")

        assert result is not None
        assert result["id"] == "test_client"

    @pytest.mark.asyncio
    async def test_add_token_to_code(self):
        """Test adding token to authorization code."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        token_set = {"access_token": "token123", "refresh_token": "refresh123"}
        await oauth_service.add_token_to_code("code123", token_set)

        mock_storage.update_authorization_code_token.assert_called_once_with(
            "code123", token_set
        )

    @pytest.mark.asyncio
    async def test_mark_code_as_used_success(self):
        """Test marking authorization code as used successfully."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.delete_authorization_code.return_value = True

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        await oauth_service.mark_code_as_used("code123")

        mock_storage.delete_authorization_code.assert_called_once_with("code123")

    @pytest.mark.asyncio
    async def test_mark_code_as_used_failure(self):
        """Test marking authorization code when deletion returns False."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.delete_authorization_code.return_value = False

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        await oauth_service.mark_code_as_used("code123")

        mock_storage.delete_authorization_code.assert_called_once_with("code123")

    @pytest.mark.asyncio
    async def test_retrieve_access_token(self):
        """Test retrieving access token."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_access_token.return_value = {
            "client_id": "client123",
            "scope": "read",
        }

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.retrieve_access_token("token123")

        assert result["client_id"] == "client123"
        mock_storage.get_access_token.assert_called_once_with("token123")

    @pytest.mark.asyncio
    async def test_retrieve_refresh_token(self):
        """Test retrieving refresh token."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_refresh_token.return_value = {"client_id": "client123"}

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.retrieve_refresh_token("refresh123")

        assert result["client_id"] == "client123"
        mock_storage.get_refresh_token.assert_called_once_with("refresh123")

    @pytest.mark.asyncio
    async def test_revoke_access_token(self):
        """Test revoking access token."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.delete_access_token.return_value = True

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.revoke_access_token("token123")

        assert result is True
        mock_storage.delete_access_token.assert_called_once_with("token123")

    @pytest.mark.asyncio
    async def test_revoke_refresh_token(self):
        """Test revoking refresh token."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.delete_refresh_token.return_value = True

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.revoke_refresh_token("refresh123")

        assert result is True
        mock_storage.delete_refresh_token.assert_called_once_with("refresh123")

    @pytest.mark.asyncio
    async def test_get_storage_status(self):
        """Test getting storage status."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_status.return_value = {"healthy": True, "type": "postgresql"}

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.get_storage_status()

        assert result["healthy"] is True
        mock_storage.get_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_refresh_token_not_found(self):
        """Test validating non-existent refresh token."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_refresh_token.return_value = None

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.validate_refresh_token("refresh123")
        assert result is None


class TestOAuthServiceEdgeCases:
    """Test OAuth service edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_validate_authorization_code_expired(self):
        """Test validation of expired authorization code."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_authorization_code.return_value = {
            "client_id": "test_client",
            "redirect_uri": "http://localhost:3000/callback",
            "scope": "read",
            "expires_at": time.time() - 3600,
        }

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.validate_authorization_code("expired_code")

        assert result is None
        mock_storage.get_authorization_code.assert_called_once_with("expired_code")

    @pytest.mark.asyncio
    async def test_validate_authorization_code_not_found(self):
        """Test validation of non-existent authorization code."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_authorization_code.return_value = None

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.validate_authorization_code("nonexistent_code")

        assert result is None
        mock_storage.get_authorization_code.assert_called_once_with("nonexistent_code")

    @pytest.mark.asyncio
    async def test_validate_authorization_code_storage_error(self):
        """Test validation when storage service fails."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_authorization_code.side_effect = Exception(
            "Database connection error"
        )

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")

        with pytest.raises(Exception, match="Database connection error"):
            await oauth_service.validate_authorization_code("test_code")

    @pytest.mark.asyncio
    async def test_validate_refresh_token_expired(self):
        """Test validation of expired refresh token."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_refresh_token.return_value = {
            "client_id": "test_client",
            "scope": "read",
            "expires_at": time.time() - 3600,
        }

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.validate_refresh_token("expired_refresh_token")

        assert result is None
        mock_storage.get_refresh_token.assert_called_once_with("expired_refresh_token")

    @pytest.mark.asyncio
    async def test_validate_refresh_token_missing_expiry(self):
        """Test validation of refresh token without expiry time (should not expire)."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_refresh_token.return_value = {
            "client_id": "test_client",
            "scope": "read",
        }

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.validate_refresh_token("refresh_token_no_expiry")

        assert result is not None
        assert result["client_id"] == "test_client"
        assert result["scope"] == "read"

    @pytest.mark.asyncio
    async def test_create_authorization_code_with_defaults(self):
        """Test creating authorization code with default values."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.store_authorization_code.return_value = True

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")

        with patch(
            "template_mcp_server.src.oauth.service.generate_random_string"
        ) as mock_gen:
            mock_gen.return_value = "generated_code"

            result = await oauth_service.create_authorization_code(
                client_id="test_client",
                redirect_uri="http://localhost:3000/callback",
                scope=None,
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
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client_by_name_and_redirect_uris.return_value = None
        mock_storage.store_client.return_value = False

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")

        with pytest.raises(RuntimeError, match="Failed to persist client registration"):
            await oauth_service.register_client(
                client_name="Test Client",
                redirect_uris=["http://localhost:3000/callback"],
            )

    @pytest.mark.asyncio
    async def test_register_client_returns_existing(self):
        """Test that existing client is returned instead of creating new one."""
        from template_mcp_server.src.storage.storage_service import StorageService

        existing_client = {
            "id": "existing_client_id",
            "secret": "existing_secret",
            "name": "Test Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "read write",
            "application_type": "native",
            "created_at": time.time() - 86400,
        }

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client_by_name_and_redirect_uris.return_value = existing_client

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")

        result = await oauth_service.register_client(
            client_name="Test Client", redirect_uris=["http://localhost:3000/callback"]
        )

        assert result["client_id"] == "existing_client_id"
        assert result["client_secret"] == "existing_secret"
        mock_storage.store_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_mark_code_as_used_storage_failure(self):
        """Test marking authorization code as used when storage fails."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.delete_authorization_code.side_effect = Exception("Storage error")

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")

        with pytest.raises(Exception, match="Storage error"):
            await oauth_service.mark_code_as_used("test_code")

    @pytest.mark.asyncio
    async def test_token_operations_with_storage_failures(self):
        """Test various token operations when storage fails."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        oauth_service = OAuthService(mock_storage, "http://localhost:5001")

        mock_storage.store_access_token.side_effect = Exception("Storage error")
        with pytest.raises(Exception, match="Storage error"):
            await oauth_service.store_access_token("token", {"data": "test"})

        mock_storage.reset_mock()
        mock_storage.store_access_token.side_effect = None

        mock_storage.get_access_token.side_effect = Exception("Storage error")
        with pytest.raises(Exception, match="Storage error"):
            await oauth_service.retrieve_access_token("token")

        mock_storage.reset_mock()
        mock_storage.get_access_token.side_effect = None

        mock_storage.delete_access_token.side_effect = Exception("Storage error")
        with pytest.raises(Exception, match="Storage error"):
            await oauth_service.revoke_access_token("token")


class TestOAuthServiceConcurrency:
    """Test OAuth service under concurrent access scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_authorization_code_validation(self):
        """Test concurrent validation of the same authorization code."""
        import asyncio

        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_authorization_code.return_value = {
            "client_id": "test_client",
            "redirect_uri": "http://localhost:3000/callback",
            "scope": "read",
            "expires_at": time.time() + 600,
        }

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")

        tasks = [
            oauth_service.validate_authorization_code("same_code") for _ in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert all(result is not None for result in results)
        assert all(result["client_id"] == "test_client" for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_client_registration(self):
        """Test concurrent registration of clients with same name and redirect URIs."""
        import asyncio

        from template_mcp_server.src.storage.storage_service import StorageService

        existing_client = {
            "id": "first_client_id",
            "secret": "first_secret",
            "name": "Test Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "read write",
            "application_type": "native",
            "created_at": time.time(),
        }

        mock_storage = AsyncMock(spec=StorageService)

        call_count = 0

        async def mock_get_existing(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None
            else:
                return existing_client

        mock_storage.get_client_by_name_and_redirect_uris.side_effect = (
            mock_get_existing
        )
        mock_storage.store_client.return_value = True

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")

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
        test_data = b"hello world!"
        result = base64url_encode(test_data)

        assert "=" not in result
        assert "+" not in result
        assert "/" not in result

    def test_verify_code_challenge_edge_cases(self):
        """Test PKCE code challenge verification with edge cases."""
        assert not verify_code_challenge("", "")

        assert not verify_code_challenge(None, "challenge")
        assert not verify_code_challenge("verifier", None)

        assert not verify_code_challenge("verifier", "invalid_challenge_!@#")

        long_verifier = "a" * 128
        expected_challenge = base64url_encode(
            hashlib.sha256(long_verifier.encode()).digest()
        )
        assert verify_code_challenge(long_verifier, expected_challenge)

    def test_verify_code_challenge_different_encodings(self):
        """Test PKCE verification with different string encodings."""
        unicode_verifier = "cafe_verifier_\U0001f511"
        expected_challenge = base64url_encode(
            hashlib.sha256(unicode_verifier.encode("utf-8")).digest()
        )
        assert verify_code_challenge(unicode_verifier, expected_challenge)

    def test_verify_code_challenge_case_sensitivity(self):
        """Test that PKCE verification is case sensitive."""
        verifier = "TestVerifier123"
        challenge = base64url_encode(hashlib.sha256(verifier.encode()).digest())

        assert verify_code_challenge(verifier, challenge)

        assert not verify_code_challenge(verifier.lower(), challenge)
        assert not verify_code_challenge(verifier.upper(), challenge)


class TestIssuerBinding:
    """Test that client credentials are bound to the authorization server issuer (SEP-2352)."""

    @pytest.mark.asyncio
    async def test_validate_client_wrong_issuer(self):
        """Test that validate_client returns None when no client exists for the given issuer."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client.return_value = None

        oauth_service = OAuthService(mock_storage, "http://issuer-a.com")
        result = await oauth_service.validate_client("client123")

        assert result is None
        mock_storage.get_client.assert_called_once_with(
            "client123", "http://issuer-a.com"
        )

    @pytest.mark.asyncio
    async def test_register_client_stores_issuer(self):
        """Test that register_client stores the issuer in the client data."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client_by_name_and_redirect_uris.return_value = None
        mock_storage.store_client.return_value = True

        oauth_service = OAuthService(mock_storage, "http://issuer-a.com")

        with patch(
            "template_mcp_server.src.oauth.service.generate_random_string"
        ) as mock_gen:
            mock_gen.side_effect = ["generated_client_id", "generated_secret"]

            await oauth_service.register_client(
                client_name="Test Client",
                redirect_uris=["http://localhost:3000/callback"],
            )

        mock_storage.store_client.assert_called_once()
        stored_client_data = mock_storage.store_client.call_args[0][0]
        assert stored_client_data["issuer"] == "http://issuer-a.com"

    @pytest.mark.asyncio
    async def test_store_access_token_enforces_issuer(self):
        """Test that store_access_token always sets issuer from service, not caller (SEP-2352)."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.store_access_token.return_value = True

        oauth_service = OAuthService(mock_storage, "http://correct-issuer.com")

        token_data = {
            "client_id": "test_client",
            "issuer": "http://attacker-issuer.com",
            "expires_at": time.time() + 3600,
        }

        await oauth_service.store_access_token("token123", token_data)

        mock_storage.store_access_token.assert_called_once()
        stored_data = mock_storage.store_access_token.call_args[0][1]
        assert stored_data["issuer"] == "http://correct-issuer.com"

    @pytest.mark.asyncio
    async def test_store_refresh_token_enforces_issuer(self):
        """Test that store_refresh_token always sets issuer from service, not caller (SEP-2352)."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.store_refresh_token.return_value = True

        oauth_service = OAuthService(mock_storage, "http://correct-issuer.com")

        token_data = {
            "client_id": "test_client",
            "issuer": "http://attacker-issuer.com",
            "expires_at": time.time() + 86400,
        }

        await oauth_service.store_refresh_token("refresh123", token_data)

        mock_storage.store_refresh_token.assert_called_once()
        stored_data = mock_storage.store_refresh_token.call_args[0][1]
        assert stored_data["issuer"] == "http://correct-issuer.com"

    @pytest.mark.asyncio
    async def test_create_authorization_code_stores_issuer(self):
        """Test that authorization codes are bound to the service's issuer (SEP-2352)."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.store_authorization_code.return_value = True

        oauth_service = OAuthService(mock_storage, "http://issuer-a.com")

        with patch(
            "template_mcp_server.src.oauth.service.generate_random_string"
        ) as mock_gen:
            mock_gen.return_value = "generated_code"

            await oauth_service.create_authorization_code(
                client_id="test_client",
                redirect_uri="http://localhost:3000/callback",
                scope="read",
                code_challenge="test_challenge",
                code_challenge_method="S256",
                state="state_123",
            )

        mock_storage.store_authorization_code.assert_called_once()
        stored_data = mock_storage.store_authorization_code.call_args[0][1]
        assert stored_data["issuer"] == "http://issuer-a.com"


class TestGetClientMetadata:
    """Test OAuthService.get_client_metadata (SEP-991 CIMD)."""

    @pytest.mark.asyncio
    async def test_returns_metadata_without_secret(self):
        """Test that get_client_metadata returns public metadata without secret."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client.return_value = {
            "id": "client123",
            "secret": "should_not_appear",
            "name": "Test Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "read write",
            "issuer": "http://localhost:5001",
            "application_type": "native",
            "created_at": 1234567890.0,
        }

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.get_client_metadata("client123")

        assert result is not None
        assert result["client_id"] == "client123"
        assert result["client_name"] == "Test Client"
        assert result["application_type"] == "native"
        assert "secret" not in result
        assert "client_secret" not in result
        assert "created_at" not in result
        mock_storage.get_client.assert_called_once_with(
            "client123", "http://localhost:5001"
        )

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_client(self):
        """Test that get_client_metadata returns None for unknown client."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client.return_value = None

        oauth_service = OAuthService(mock_storage, "http://localhost:5001")
        result = await oauth_service.get_client_metadata("unknown")

        assert result is None
        mock_storage.get_client.assert_called_once_with(
            "unknown", "http://localhost:5001"
        )

    @pytest.mark.asyncio
    async def test_uses_service_issuer_for_lookup(self):
        """Test that get_client_metadata uses the service's issuer, not the client's."""
        from template_mcp_server.src.storage.storage_service import StorageService

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.get_client.return_value = None

        oauth_service = OAuthService(mock_storage, "http://issuer-a.com")
        await oauth_service.get_client_metadata("client123")

        mock_storage.get_client.assert_called_once_with(
            "client123", "http://issuer-a.com"
        )
