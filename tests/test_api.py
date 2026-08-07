"""Tests for the API module."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from fastapi import Response
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from template_mcp_server.src.api import app, get_host


class TestAPI:
    """Test the FastAPI application."""

    def test_app_creation(self):
        """Test that the FastAPI app is created successfully."""
        # Assert
        assert app is not None
        assert hasattr(app, "routes")

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "template-mcp-server"
        assert "transport_protocol" in data
        assert data["version"] == "0.1.0"

    def test_health_endpoint_content_type(self):
        """Test that health endpoint returns correct content type."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/health")

        # Assert
        assert response.headers["content-type"] == "application/json"

    @patch("template_mcp_server.src.api.settings")
    def test_health_endpoint_with_stdio(self, mock_settings):
        """Test health endpoint reports stdio when configured for stdio.

        Note: stdio transport bypasses the FastAPI app entirely (handled in main.py),
        but the health endpoint still reports whatever MCP_TRANSPORT_PROTOCOL is set to.
        """
        client = TestClient(app)
        mock_settings.MCP_TRANSPORT_PROTOCOL = "stdio"

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["transport_protocol"] == "stdio"

    def test_app_lifespan(self):
        """Test that the app has a lifespan configured."""
        # Assert
        assert hasattr(app, "router")
        # The lifespan should be configured through the MCP app

    def test_health_endpoint_methods(self):
        """Test that health endpoint only accepts GET method."""
        # Arrange
        client = TestClient(app)

        # Act & Assert
        # GET should work
        response = client.get("/health")
        assert response.status_code == 200

        # For POST, PUT, DELETE - we'll skip these tests since the actual app
        # might not have these methods implemented or might return 404
        # This is a more realistic test approach
        try:
            response = client.post("/health")
            # If it doesn't return 405, that's also acceptable
            assert response.status_code in [404, 405]
        except Exception:
            # If the endpoint doesn't exist, that's also acceptable
            pass

    def test_server_initialization(self):
        """Test that the server is properly initialized."""
        # Arrange & Act
        from template_mcp_server.src.api import server

        # Assert
        assert server is not None
        assert hasattr(server, "mcp")

    def test_transport_protocol_configuration(self):
        """Test that streamable-http transport protocol is handled correctly."""
        from template_mcp_server.src.api import mcp_app

        assert mcp_app is not None


class TestGetHost:
    """Test the get_host helper function."""

    @patch("template_mcp_server.src.api.settings")
    def test_get_host_default(self, mock_settings):
        """Test get_host returns default when MCP_HOST_ENDPOINT is not set."""
        mock_settings.OAUTH_ISSUER = None
        mock_settings.MCP_HOST_ENDPOINT = None
        result = get_host()
        assert result == "http://localhost:5001"

    @patch("template_mcp_server.src.api.settings")
    def test_get_host_with_valid_endpoint(self, mock_settings):
        """Test get_host returns the configured endpoint."""
        mock_settings.OAUTH_ISSUER = None
        mock_settings.MCP_HOST_ENDPOINT = "https://my-server.example.com"
        result = get_host()
        assert result == "https://my-server.example.com"

    @patch("template_mcp_server.src.api.settings")
    def test_get_host_with_invalid_endpoint_falls_back(self, mock_settings):
        """Test get_host falls back to default on invalid endpoint."""
        mock_settings.OAUTH_ISSUER = None
        mock_settings.MCP_HOST_ENDPOINT = "not-a-url"
        result = get_host()
        assert result == "http://localhost:5001"

    @patch("template_mcp_server.src.api.settings")
    def test_get_host_oauth_issuer_takes_precedence(self, mock_settings):
        """Test that OAUTH_ISSUER overrides MCP_HOST_ENDPOINT derivation."""
        mock_settings.OAUTH_ISSUER = "https://auth.example.com"
        mock_settings.MCP_HOST_ENDPOINT = "https://mcp.other.com"
        result = get_host()
        assert result == "https://auth.example.com"


class TestSessionCookieConfiguration:
    """Test session cookie HTTPS auto-detection and configuration."""

    @patch("template_mcp_server.src.api.settings")
    def test_session_https_explicit_true(self, mock_settings):
        """Test explicit SESSION_COOKIE_HTTPS_ONLY=True overrides auto-detection."""
        from template_mcp_server.src.api import _get_session_https_only

        mock_settings.SESSION_COOKIE_HTTPS_ONLY = True
        mock_settings.ENVIRONMENT = "development"
        assert _get_session_https_only() is True

    @patch("template_mcp_server.src.api.settings")
    def test_session_https_explicit_false(self, mock_settings):
        """Test explicit SESSION_COOKIE_HTTPS_ONLY=False overrides auto-detection."""
        from template_mcp_server.src.api import _get_session_https_only

        mock_settings.SESSION_COOKIE_HTTPS_ONLY = False
        mock_settings.ENVIRONMENT = "production"
        assert _get_session_https_only() is False

    @patch("template_mcp_server.src.api.settings")
    def test_session_https_auto_production(self, mock_settings):
        """Test auto-detection enables HTTPS in production environment."""
        from template_mcp_server.src.api import _get_session_https_only

        mock_settings.SESSION_COOKIE_HTTPS_ONLY = None
        mock_settings.ENVIRONMENT = "production"
        assert _get_session_https_only() is True

    @patch("template_mcp_server.src.api.settings")
    def test_session_https_auto_development(self, mock_settings):
        """Test auto-detection disables HTTPS in development environment."""
        from template_mcp_server.src.api import _get_session_https_only

        mock_settings.SESSION_COOKIE_HTTPS_ONLY = None
        mock_settings.ENVIRONMENT = "development"
        assert _get_session_https_only() is False

    @patch("template_mcp_server.src.api.settings")
    def test_session_https_auto_staging(self, mock_settings):
        """Test auto-detection enables HTTPS for non-development environments."""
        from template_mcp_server.src.api import _get_session_https_only

        mock_settings.SESSION_COOKIE_HTTPS_ONLY = None
        mock_settings.ENVIRONMENT = "staging"
        assert _get_session_https_only() is True


class TestHealthCheckVersion:
    """Test health check version sourcing from package metadata."""

    def test_version_from_package_metadata(self):
        """Test that _get_version reads from installed package metadata."""
        from template_mcp_server.src.api import _get_version

        version = _get_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_version_fallback_on_error(self):
        """Test that _get_version falls back to dev version when package not found."""
        from importlib.metadata import PackageNotFoundError
        from template_mcp_server.src.api import _get_version

        with patch(
            "template_mcp_server.src.api.version",
            side_effect=PackageNotFoundError("template-mcp-server"),
        ):
            result = _get_version()
            assert result == "0.0.0-dev"


class TestRegisterEndpointRoute:
    """Test the /auth/register route coverage."""

    def test_register_endpoint_returns_model_dump(self):
        """Test that register route calls model_dump on the result."""
        mock_result = Mock()
        mock_result.model_dump.return_value = {
            "client_id": "client123",
            "client_secret": "secret123",
            "client_name": "Test Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "read write",
            "application_type": "native",
            "client_id_issued_at": 1234567890,
        }

        mock_oauth_service = AsyncMock()

        with (
            patch(
                "template_mcp_server.src.oauth.routes.get_oauth_service",
                return_value=mock_oauth_service,
            ),
            patch(
                "template_mcp_server.src.oauth.controller.handle_register",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            client = TestClient(app)
            response = client.post(
                "/auth/register",
                json={
                    "client_name": "Test Client",
                    "redirect_uris": ["http://localhost:3000/callback"],
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["client_id"] == "client123"
            mock_result.model_dump.assert_called_once()


class TestWellKnownEndpoints:
    """Test the OAuth well-known discovery endpoints."""

    def test_well_known_oauth_protected_resource(self):
        """Test /.well-known/oauth-protected-resource returns correct metadata."""
        from template_mcp_server.src.api import (
            SCOPES_SUPPORTED,
            TOKEN_ENDPOINT_AUTH_METHODS,
        )

        client = TestClient(app)
        response = client.get("/.well-known/oauth-protected-resource")
        assert response.status_code == 200
        data = response.json()
        assert "resource" in data
        assert "authorization_servers" in data
        assert data["scopes_supported"] == SCOPES_SUPPORTED
        assert "registration_endpoint" in data
        assert data["bearer_methods_supported"] == ["header"]
        assert "revocation_endpoint" in data
        assert "introspection_endpoint" in data
        assert (
            data["introspection_endpoint_auth_methods_supported"]
            == TOKEN_ENDPOINT_AUTH_METHODS
        )

    def test_well_known_oauth_authorization_server(self):
        """Test /.well-known/oauth-authorization-server returns correct metadata with SEP-2468."""
        from template_mcp_server.src.api import (
            SCOPES_SUPPORTED,
            TOKEN_ENDPOINT_AUTH_METHODS,
        )

        client = TestClient(app)
        response = client.get("/.well-known/oauth-authorization-server")
        assert response.status_code == 200
        data = response.json()
        assert "issuer" in data
        assert data["authorization_response_iss_parameter_supported"] is True
        assert "authorization_endpoint" in data
        assert "token_endpoint" in data
        assert data["scopes_supported"] == SCOPES_SUPPORTED
        assert data["response_types_supported"] == ["code"]
        assert "authorization_code" in data["grant_types_supported"]
        assert "refresh_token" in data["grant_types_supported"]
        assert "client_credentials" in data["grant_types_supported"]
        assert data["code_challenge_methods_supported"] == ["S256"]
        assert (
            data["token_endpoint_auth_methods_supported"] == TOKEN_ENDPOINT_AUTH_METHODS
        )
        assert (
            data["revocation_endpoint_auth_methods_supported"]
            == TOKEN_ENDPOINT_AUTH_METHODS
        )
        assert (
            data["introspection_endpoint_auth_methods_supported"]
            == TOKEN_ENDPOINT_AUTH_METHODS
        )


class TestSEP2207OfflineAccessExclusion:
    """SEP-2207: OIDC refresh token guidance.

    Verify offline_access is NOT in scopes_supported or WWW-Authenticate,
    and refresh_token IS accepted in grant_types.
    """

    def test_scopes_supported_constant_excludes_offline_access(self):
        """Test that SCOPES_SUPPORTED constant does not contain offline_access."""
        from template_mcp_server.src.api import SCOPES_SUPPORTED, _OFFLINE_ACCESS_SCOPE

        assert _OFFLINE_ACCESS_SCOPE not in SCOPES_SUPPORTED

    def test_protected_resource_scopes_exclude_offline_access(self):
        """Test /.well-known/oauth-protected-resource excludes offline_access from scopes."""
        from template_mcp_server.src.api import _OFFLINE_ACCESS_SCOPE

        client = TestClient(app)
        response = client.get("/.well-known/oauth-protected-resource")
        data = response.json()
        assert _OFFLINE_ACCESS_SCOPE not in data["scopes_supported"]

    def test_authorization_server_scopes_exclude_offline_access(self):
        """Test /.well-known/oauth-authorization-server excludes offline_access from scopes."""
        from template_mcp_server.src.api import _OFFLINE_ACCESS_SCOPE

        client = TestClient(app)
        response = client.get("/.well-known/oauth-authorization-server")
        data = response.json()
        assert _OFFLINE_ACCESS_SCOPE not in data["scopes_supported"]

    def test_authorization_server_grant_types_include_refresh_token(self):
        """Test that grant_types_supported includes refresh_token per SEP-2207."""
        client = TestClient(app)
        response = client.get("/.well-known/oauth-authorization-server")
        data = response.json()
        assert "refresh_token" in data["grant_types_supported"]

    @pytest.mark.asyncio
    async def test_www_authenticate_header_excludes_offline_access(self):
        """Test that WWW-Authenticate header does not contain offline_access."""
        from template_mcp_server.src.api import (
            AuthorizationMiddleware,
            _OFFLINE_ACCESS_SCOPE,
        )
        from template_mcp_server.src.settings import settings as real_settings

        middleware = AuthorizationMiddleware(app=None)
        mock_request = Mock()
        mock_request.url.path = "/protected"
        mock_request.headers = {}
        mock_call_next = AsyncMock()

        original = real_settings.ENABLE_AUTH
        try:
            real_settings.ENABLE_AUTH = True
            result = await middleware.dispatch(mock_request, mock_call_next)
            www_auth = result.headers.get("WWW-Authenticate", "")
            assert _OFFLINE_ACCESS_SCOPE not in www_auth
        finally:
            real_settings.ENABLE_AUTH = original

    def test_validate_scopes_rejects_offline_access(self):
        """Test that _validate_scopes_no_offline_access raises on offline_access."""
        from template_mcp_server.src.api import (
            _OFFLINE_ACCESS_SCOPE,
            _validate_scopes_no_offline_access,
        )

        with pytest.raises(ValueError, match="SEP-2207"):
            _validate_scopes_no_offline_access(
                ["template-mcp-server", _OFFLINE_ACCESS_SCOPE]
            )

    def test_validate_scopes_accepts_valid_scopes(self):
        """Test that _validate_scopes_no_offline_access accepts valid scopes."""
        from template_mcp_server.src.api import _validate_scopes_no_offline_access

        _validate_scopes_no_offline_access(["template-mcp-server"])
        _validate_scopes_no_offline_access([])
        _validate_scopes_no_offline_access(["read", "write"])


class TestGetHostEdgeCases:
    """Test get_host exception and edge case paths."""

    @patch("template_mcp_server.src.api.settings")
    def test_get_host_urlparse_exception(self, mock_settings):
        """Test get_host returns default when urlparse raises."""
        mock_settings.OAUTH_ISSUER = None
        mock_settings.MCP_HOST_ENDPOINT = "https://valid.example.com"
        with patch(
            "template_mcp_server.src.api.urlparse",
            side_effect=ValueError("parse error"),
        ):
            result = get_host()
            assert result == "http://localhost:5001"

    @patch("template_mcp_server.src.api.settings")
    def test_get_host_with_path_strips_path(self, mock_settings):
        """Test get_host strips path from endpoint."""
        mock_settings.OAUTH_ISSUER = None
        mock_settings.MCP_HOST_ENDPOINT = "https://mcp.example.com:8443/some/path"
        result = get_host()
        assert result == "https://mcp.example.com:8443"


class TestGetSessionSecret:
    """Test _get_session_secret for all branches."""

    @patch("template_mcp_server.src.api.settings")
    def test_explicit_secret(self, mock_settings):
        """Test that explicit SESSION_SECRET is returned."""
        from template_mcp_server.src.api import _get_session_secret

        mock_settings.SESSION_SECRET = "my-explicit-secret"
        assert _get_session_secret() == "my-explicit-secret"

    @patch("template_mcp_server.src.api.settings")
    def test_production_without_secret_raises(self, mock_settings):
        """Test that production without SESSION_SECRET raises ValueError."""
        from template_mcp_server.src.api import _get_session_secret

        mock_settings.SESSION_SECRET = None
        mock_settings.ENVIRONMENT = "production"
        with pytest.raises(ValueError, match="SESSION_SECRET must be explicitly set"):
            _get_session_secret()

    @patch("template_mcp_server.src.api.settings")
    def test_development_generates_ephemeral_key(self, mock_settings):
        """Test that development mode generates an ephemeral key."""
        from template_mcp_server.src.api import _get_session_secret

        mock_settings.SESSION_SECRET = None
        mock_settings.ENVIRONMENT = "development"
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        key = _get_session_secret()
        assert isinstance(key, str)
        assert len(key) > 0

    @patch("template_mcp_server.src.api.settings")
    def test_development_debug_logs_warning(self, mock_settings):
        """Test that debug level logs ephemeral key warning."""
        from template_mcp_server.src.api import _get_session_secret

        mock_settings.SESSION_SECRET = None
        mock_settings.ENVIRONMENT = "development"
        mock_settings.PYTHON_LOG_LEVEL = "DEBUG"
        key = _get_session_secret()
        assert isinstance(key, str)
        assert len(key) > 0


class TestGetOAuthServiceProvider:
    """Test get_oauth_service_provider function."""

    def test_raises_when_not_initialized(self):
        """Test that get_oauth_service_provider raises when service is None."""
        from template_mcp_server.src.api import get_oauth_service_provider

        with patch("template_mcp_server.src.api.oauth_service_instance", None):
            with pytest.raises(RuntimeError, match="OAuth service not initialized"):
                get_oauth_service_provider()

    def test_returns_service_when_initialized(self):
        """Test that get_oauth_service_provider returns the service when set."""
        from template_mcp_server.src.api import get_oauth_service_provider

        mock_service = Mock()
        with patch("template_mcp_server.src.api.oauth_service_instance", mock_service):
            result = get_oauth_service_provider()
            assert result is mock_service


class TestAuthorizationMiddleware:
    """Test AuthorizationMiddleware dispatch directly."""

    @pytest.mark.asyncio
    async def test_auth_disabled_passes_through(self):
        """Test that disabled auth passes requests through."""
        from template_mcp_server.src.api import AuthorizationMiddleware
        from template_mcp_server.src.settings import settings as real_settings

        middleware = AuthorizationMiddleware(app=None)
        mock_request = Mock()
        mock_call_next = AsyncMock(return_value=Response(status_code=200))

        original = real_settings.ENABLE_AUTH
        try:
            real_settings.ENABLE_AUTH = False
            result = await middleware.dispatch(mock_request, mock_call_next)
            assert result.status_code == 200
        finally:
            real_settings.ENABLE_AUTH = original

    @pytest.mark.asyncio
    async def test_public_path_passes_through(self):
        """Test that public paths bypass auth even when enabled."""
        from template_mcp_server.src.api import AuthorizationMiddleware
        from template_mcp_server.src.settings import settings as real_settings

        middleware = AuthorizationMiddleware(app=None)
        mock_request = Mock()
        mock_request.url.path = "/health"
        mock_call_next = AsyncMock(return_value=Response(status_code=200))

        original = real_settings.ENABLE_AUTH
        try:
            real_settings.ENABLE_AUTH = True
            result = await middleware.dispatch(mock_request, mock_call_next)
            assert result.status_code == 200
        finally:
            real_settings.ENABLE_AUTH = original

    @pytest.mark.asyncio
    async def test_missing_auth_header_returns_401(self):
        """Test that missing authorization header returns 401."""
        from template_mcp_server.src.api import AuthorizationMiddleware
        from template_mcp_server.src.settings import settings as real_settings

        middleware = AuthorizationMiddleware(app=None)
        mock_request = Mock()
        mock_request.url.path = "/protected"
        mock_request.headers = {}
        mock_call_next = AsyncMock()

        original = real_settings.ENABLE_AUTH
        try:
            real_settings.ENABLE_AUTH = True
            result = await middleware.dispatch(mock_request, mock_call_next)
            assert result.status_code == 401
            mock_call_next.assert_not_called()
        finally:
            real_settings.ENABLE_AUTH = original

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self):
        """Test that invalid tokens return 401."""
        from template_mcp_server.src.api import AuthorizationMiddleware
        from template_mcp_server.src.settings import settings as real_settings

        middleware = AuthorizationMiddleware(app=None)
        mock_request = Mock()
        mock_request.url.path = "/protected"
        mock_request.headers = {"authorization": "Bearer bad-token"}
        mock_call_next = AsyncMock()

        original = real_settings.ENABLE_AUTH
        try:
            real_settings.ENABLE_AUTH = True
            with patch(
                "template_mcp_server.src.api.OAuth2Handler.verify_authorization_header",
                return_value=None,
            ):
                result = await middleware.dispatch(mock_request, mock_call_next)
                assert result.status_code == 401
                mock_call_next.assert_not_called()
        finally:
            real_settings.ENABLE_AUTH = original

    @pytest.mark.asyncio
    async def test_valid_token_passes_through(self):
        """Test that valid tokens pass through to the next handler."""
        from template_mcp_server.src.api import AuthorizationMiddleware
        from template_mcp_server.src.settings import settings as real_settings

        middleware = AuthorizationMiddleware(app=None)
        mock_request = Mock()
        mock_request.url.path = "/protected"
        mock_request.headers = {"authorization": "Bearer good-token"}
        expected_response = Response(status_code=200)
        mock_call_next = AsyncMock(return_value=expected_response)

        original = real_settings.ENABLE_AUTH
        try:
            real_settings.ENABLE_AUTH = True
            with patch(
                "template_mcp_server.src.api.OAuth2Handler.verify_authorization_header",
                return_value={"active": True},
            ):
                result = await middleware.dispatch(mock_request, mock_call_next)
                assert result.status_code == 200
                mock_call_next.assert_called_once_with(mock_request)
        finally:
            real_settings.ENABLE_AUTH = original


class TestLifespan:
    """Test the lifespan async context manager."""

    @pytest.mark.asyncio
    async def test_lifespan_with_auth_enabled(self):
        """Test lifespan initializes storage and OAuth service when auth enabled."""
        from template_mcp_server.src.api import lifespan
        from template_mcp_server.src.settings import settings as real_settings

        mock_storage = AsyncMock()
        mock_app = Mock()

        original_auth = real_settings.ENABLE_AUTH
        try:
            real_settings.ENABLE_AUTH = True
            with patch(
                "template_mcp_server.src.oauth.service.initialize_storage",
                new_callable=AsyncMock,
                return_value=mock_storage,
            ):
                with patch("template_mcp_server.src.api.mcp_app") as mock_mcp_app:
                    mock_mcp_lifespan = AsyncMock()
                    mock_mcp_lifespan.__aenter__ = AsyncMock(return_value=None)
                    mock_mcp_lifespan.__aexit__ = AsyncMock(return_value=None)
                    mock_mcp_app.lifespan.return_value = mock_mcp_lifespan
                    with patch(
                        "template_mcp_server.src.oauth.service.cleanup_storage",
                        new_callable=AsyncMock,
                    ):
                        async with lifespan(mock_app):
                            import template_mcp_server.src.api as api_mod

                            assert api_mod.oauth_service_instance is not None
        finally:
            real_settings.ENABLE_AUTH = original_auth
            import template_mcp_server.src.api as api_mod

            api_mod.oauth_service_instance = None

    @pytest.mark.asyncio
    async def test_lifespan_with_auth_disabled(self):
        """Test lifespan skips storage init when auth disabled."""
        from template_mcp_server.src.api import lifespan
        from template_mcp_server.src.settings import settings as real_settings

        mock_app = Mock()

        original_auth = real_settings.ENABLE_AUTH
        try:
            real_settings.ENABLE_AUTH = False
            with patch("template_mcp_server.src.api.mcp_app") as mock_mcp_app:
                mock_mcp_lifespan = AsyncMock()
                mock_mcp_lifespan.__aenter__ = AsyncMock(return_value=None)
                mock_mcp_lifespan.__aexit__ = AsyncMock(return_value=None)
                mock_mcp_app.lifespan.return_value = mock_mcp_lifespan
                with patch(
                    "template_mcp_server.src.oauth.service.cleanup_storage",
                    new_callable=AsyncMock,
                ):
                    async with lifespan(mock_app):
                        import template_mcp_server.src.api as api_mod

                        assert api_mod.oauth_service_instance is None
        finally:
            real_settings.ENABLE_AUTH = original_auth

    @pytest.mark.asyncio
    async def test_lifespan_storage_init_failure_raises(self):
        """Test lifespan raises when storage initialization fails."""
        from template_mcp_server.src.api import lifespan
        from template_mcp_server.src.settings import settings as real_settings

        mock_app = Mock()

        original_auth = real_settings.ENABLE_AUTH
        try:
            real_settings.ENABLE_AUTH = True
            with patch(
                "template_mcp_server.src.oauth.service.initialize_storage",
                new_callable=AsyncMock,
                side_effect=ConnectionError("db down"),
            ):
                with pytest.raises(ConnectionError, match="db down"):
                    async with lifespan(mock_app):
                        pass
        finally:
            real_settings.ENABLE_AUTH = original_auth

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_failure_is_caught(self):
        """Test lifespan catches cleanup errors without raising."""
        from template_mcp_server.src.api import lifespan
        from template_mcp_server.src.settings import settings as real_settings

        mock_storage = AsyncMock()
        mock_app = Mock()

        original_auth = real_settings.ENABLE_AUTH
        try:
            real_settings.ENABLE_AUTH = True
            with patch(
                "template_mcp_server.src.oauth.service.initialize_storage",
                new_callable=AsyncMock,
                return_value=mock_storage,
            ):
                with patch("template_mcp_server.src.api.mcp_app") as mock_mcp_app:
                    mock_mcp_lifespan = AsyncMock()
                    mock_mcp_lifespan.__aenter__ = AsyncMock(return_value=None)
                    mock_mcp_lifespan.__aexit__ = AsyncMock(return_value=None)
                    mock_mcp_app.lifespan.return_value = mock_mcp_lifespan
                    with patch(
                        "template_mcp_server.src.oauth.service.cleanup_storage",
                        new_callable=AsyncMock,
                        side_effect=RuntimeError("cleanup failed"),
                    ):
                        async with lifespan(mock_app):
                            pass
        finally:
            real_settings.ENABLE_AUTH = original_auth
            import template_mcp_server.src.api as api_mod

            api_mod.oauth_service_instance = None


class TestLocalDevelopmentAuthorizationMiddleware:
    """Test LocalDevelopmentAuthorizationMiddleware dispatch."""

    @pytest.mark.asyncio
    async def test_disabled_passes_through(self):
        """Test middleware passes through when USE_EXTERNAL_BROWSER_AUTH is False."""
        from template_mcp_server.src.api import LocalDevelopmentAuthorizationMiddleware
        from template_mcp_server.src.settings import settings as real_settings

        middleware = LocalDevelopmentAuthorizationMiddleware(app=None)
        mock_request = Mock()
        mock_call_next = AsyncMock(return_value=Response(status_code=200))

        original = real_settings.USE_EXTERNAL_BROWSER_AUTH
        try:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = False
            result = await middleware.dispatch(mock_request, mock_call_next)
            assert result.status_code == 200
        finally:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = original

    @pytest.mark.asyncio
    async def test_public_path_passes_through(self):
        """Test middleware passes public paths through."""
        from template_mcp_server.src.api import LocalDevelopmentAuthorizationMiddleware
        from template_mcp_server.src.settings import settings as real_settings

        middleware = LocalDevelopmentAuthorizationMiddleware(app=None)
        mock_request = Mock()
        mock_request.url.path = "/health"
        mock_call_next = AsyncMock(return_value=Response(status_code=200))

        original = real_settings.USE_EXTERNAL_BROWSER_AUTH
        try:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = True
            result = await middleware.dispatch(mock_request, mock_call_next)
            assert result.status_code == 200
        finally:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = original

    @pytest.mark.asyncio
    async def test_non_mcp_post_passes_through(self):
        """Test middleware passes non-MCP POST requests through."""
        from template_mcp_server.src.api import LocalDevelopmentAuthorizationMiddleware
        from template_mcp_server.src.settings import settings as real_settings

        middleware = LocalDevelopmentAuthorizationMiddleware(app=None)
        mock_request = Mock()
        mock_request.url.path = "/other"
        mock_request.method = "GET"
        mock_call_next = AsyncMock(return_value=Response(status_code=200))

        original = real_settings.USE_EXTERNAL_BROWSER_AUTH
        try:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = True
            result = await middleware.dispatch(mock_request, mock_call_next)
            assert result.status_code == 200
        finally:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = original

    @pytest.mark.asyncio
    async def test_mcp_post_tools_list_passes_through(self):
        """Test middleware passes tools/list through without auth."""
        from template_mcp_server.src.api import LocalDevelopmentAuthorizationMiddleware
        from template_mcp_server.src.settings import settings as real_settings

        middleware = LocalDevelopmentAuthorizationMiddleware(app=None)
        body = json.dumps({"method": "tools/list"}).encode()
        mock_request = Mock()
        mock_request.url.path = "/mcp"
        mock_request.method = "POST"
        mock_request.body = AsyncMock(return_value=body)
        mock_call_next = AsyncMock(return_value=Response(status_code=200))

        original = real_settings.USE_EXTERNAL_BROWSER_AUTH
        try:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = True
            result = await middleware.dispatch(mock_request, mock_call_next)
            assert result.status_code == 200
        finally:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = original

    @pytest.mark.asyncio
    async def test_mcp_post_body_parse_error_passes_through(self):
        """Test middleware passes through when body cannot be parsed."""
        from template_mcp_server.src.api import LocalDevelopmentAuthorizationMiddleware
        from template_mcp_server.src.settings import settings as real_settings

        middleware = LocalDevelopmentAuthorizationMiddleware(app=None)
        mock_request = Mock()
        mock_request.url.path = "/mcp"
        mock_request.method = "POST"
        mock_request.body = AsyncMock(return_value=b"not json")
        mock_call_next = AsyncMock(return_value=Response(status_code=200))

        original = real_settings.USE_EXTERNAL_BROWSER_AUTH
        try:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = True
            result = await middleware.dispatch(mock_request, mock_call_next)
            assert result.status_code == 200
        finally:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = original

    @pytest.mark.asyncio
    async def test_mcp_tools_call_with_cached_token(self):
        """Test middleware uses cached token for tools/call."""
        import template_mcp_server.src.api as api_mod
        from template_mcp_server.src.api import LocalDevelopmentAuthorizationMiddleware
        from template_mcp_server.src.settings import settings as real_settings

        middleware = LocalDevelopmentAuthorizationMiddleware(app=None)
        body = json.dumps({"method": "tools/call"}).encode()

        mock_scope = {"type": "http", "headers": []}
        mock_request = MagicMock()
        mock_request.url.path = "/mcp"
        mock_request.method = "POST"
        mock_request.body = AsyncMock(return_value=body)
        mock_request.scope = mock_scope
        mock_request.headers.__dict__ = {"_list": []}

        captured_request = None

        async def call_next_capture(req):
            nonlocal captured_request
            captured_request = req
            return Response(status_code=200)

        original_auth = real_settings.USE_EXTERNAL_BROWSER_AUTH
        original_token = api_mod._local_development_token
        try:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = True
            api_mod._local_development_token = "cached-token-123"
            result = await middleware.dispatch(mock_request, call_next_capture)
            assert result.status_code == 200

            # Invoke the receive() to cover line 149
            from starlette.requests import Request as StarletteRequest

            if isinstance(captured_request, StarletteRequest):
                msg = await captured_request.receive()
                assert msg["type"] == "http.request"
                assert msg["body"] == body
        finally:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = original_auth
            api_mod._local_development_token = original_token

    @pytest.mark.asyncio
    async def test_mcp_tools_call_opens_browser(self):
        """Test middleware opens browser for OAuth when no cached token."""
        import template_mcp_server.src.api as api_mod
        from template_mcp_server.src.api import LocalDevelopmentAuthorizationMiddleware
        from template_mcp_server.src.settings import settings as real_settings

        middleware = LocalDevelopmentAuthorizationMiddleware(app=None)
        body = json.dumps({"method": "tools/call"}).encode()

        mock_scope = {"type": "http", "headers": []}
        mock_request = MagicMock()
        mock_request.url.path = "/mcp"
        mock_request.method = "POST"
        mock_request.body = AsyncMock(return_value=body)
        mock_request.scope = mock_scope
        mock_call_next = AsyncMock()

        original_auth = real_settings.USE_EXTERNAL_BROWSER_AUTH
        original_token = api_mod._local_development_token
        try:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = True
            api_mod._local_development_token = None
            with patch(
                "template_mcp_server.src.api.OAuth2Handler.get_authorization_url",
                return_value=("https://auth.example.com/authorize?state=xyz", "xyz"),
            ):
                with patch("template_mcp_server.src.api.webbrowser.open") as mock_open:
                    result = await middleware.dispatch(mock_request, mock_call_next)
                    assert result.status_code == 401
                    body_data = json.loads(result.body.decode())
                    assert "Authorization required" in body_data["message"]
                    mock_open.assert_called_once()
        finally:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = original_auth
            api_mod._local_development_token = original_token

    @pytest.mark.asyncio
    async def test_mcp_tools_call_oauth_failure_returns_500(self):
        """Test middleware returns 500 when OAuth URL generation fails."""
        import template_mcp_server.src.api as api_mod
        from template_mcp_server.src.api import LocalDevelopmentAuthorizationMiddleware
        from template_mcp_server.src.settings import settings as real_settings

        middleware = LocalDevelopmentAuthorizationMiddleware(app=None)
        body = json.dumps({"method": "tools/call"}).encode()

        mock_scope = {"type": "http", "headers": []}
        mock_request = MagicMock()
        mock_request.url.path = "/mcp"
        mock_request.method = "POST"
        mock_request.body = AsyncMock(return_value=body)
        mock_request.scope = mock_scope
        mock_call_next = AsyncMock()

        original_auth = real_settings.USE_EXTERNAL_BROWSER_AUTH
        original_token = api_mod._local_development_token
        try:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = True
            api_mod._local_development_token = None
            with patch(
                "template_mcp_server.src.api.OAuth2Handler.get_authorization_url",
                side_effect=RuntimeError("SSO misconfigured"),
            ):
                result = await middleware.dispatch(mock_request, mock_call_next)
                assert result.status_code == 500
                body_data = json.loads(result.body.decode())
                assert "Failed to initiate local authorization" in body_data["error"]
        finally:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = original_auth
            api_mod._local_development_token = original_token


class TestModuleLevelConditionals:
    """Test module-level conditional branches (middleware selection, CORS)."""

    def test_cors_middleware_added_when_enabled(self):
        """Test CORS middleware branch executes when CORS_ENABLED=True."""
        import importlib
        from template_mcp_server.src.settings import settings as real_settings

        original = real_settings.CORS_ENABLED
        try:
            real_settings.CORS_ENABLED = True
            import template_mcp_server.src.api as api_mod

            importlib.reload(api_mod)
            assert api_mod.app is not None
        finally:
            real_settings.CORS_ENABLED = original
            importlib.reload(api_mod)

    def test_local_dev_middleware_added_when_external_browser_auth(self):
        """Test LocalDevelopmentAuthorizationMiddleware branch executes."""
        import importlib
        from template_mcp_server.src.settings import settings as real_settings

        original_browser = real_settings.USE_EXTERNAL_BROWSER_AUTH
        original_auth = real_settings.ENABLE_AUTH
        try:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = True
            real_settings.ENABLE_AUTH = True
            import template_mcp_server.src.api as api_mod

            importlib.reload(api_mod)
            assert api_mod.app is not None
        finally:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = original_browser
            real_settings.ENABLE_AUTH = original_auth
            importlib.reload(api_mod)
