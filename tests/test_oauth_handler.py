import time
from unittest.mock import Mock, patch

import httpx

from template_mcp_server.src.oauth.handler import SCOPE, OAuth2Handler


class TestOAuth2Handler:
    """Test class for OAuth2Handler."""

    @patch("template_mcp_server.src.oauth.handler.settings")
    def test_create_oauth_session_without_state(self, mock_settings):
        """Test creating OAuth session without state."""
        mock_settings.SSO_CLIENT_ID = "test_client_id"
        mock_settings.SSO_CALLBACK_URL = "http://localhost:3000/callback"

        with patch("template_mcp_server.src.oauth.handler.OAuth2Session") as mock_oauth:
            mock_session = Mock()
            mock_oauth.return_value = mock_session

            result = OAuth2Handler.create_oauth_session()

            mock_oauth.assert_called_once_with(
                "test_client_id",
                scope=SCOPE,
                redirect_uri="http://localhost:3000/callback",
                state=None,
            )
            assert result == mock_session

    @patch("template_mcp_server.src.oauth.handler.settings")
    def test_create_oauth_session_with_state(self, mock_settings):
        """Test creating OAuth session with state."""
        mock_settings.SSO_CLIENT_ID = "test_client_id"
        mock_settings.SSO_CALLBACK_URL = "http://localhost:3000/callback"

        with patch("template_mcp_server.src.oauth.handler.OAuth2Session") as mock_oauth:
            mock_session = Mock()
            mock_oauth.return_value = mock_session

            result = OAuth2Handler.create_oauth_session("test_state")

            mock_oauth.assert_called_once_with(
                "test_client_id",
                scope=SCOPE,
                redirect_uri="http://localhost:3000/callback",
                state="test_state",
            )
            assert result == mock_session

    @patch("template_mcp_server.src.oauth.handler.OAuth2Handler.create_oauth_session")
    def test_get_authorization_url(self, mock_create_session):
        """Test getting authorization URL."""
        mock_session = Mock()
        mock_session.authorization_url.return_value = ("http://auth.url", "state123")
        mock_create_session.return_value = mock_session

        auth_url, state = OAuth2Handler.get_authorization_url()

        mock_create_session.assert_called_once_with()
        assert auth_url == "http://auth.url"
        assert state == "state123"

    @patch("template_mcp_server.src.oauth.handler.settings")
    @patch("template_mcp_server.src.oauth.handler.OAuth2Handler.create_oauth_session")
    def test_get_access_token_from_authorization_code_flow(
        self, mock_create_session, mock_settings
    ):
        """Test getting access token from authorization code flow."""
        mock_settings.SSO_CLIENT_SECRET = "test_secret"

        mock_session = Mock()
        mock_token = {"access_token": "token123", "token_type": "Bearer"}
        mock_session.fetch_token.return_value = mock_token
        mock_create_session.return_value = mock_session

        result = OAuth2Handler.get_access_token_from_authorization_code_flow(
            "code123", "state123"
        )

        mock_create_session.assert_called_once_with(state="state123")
        mock_session.fetch_token.assert_called_once_with(
            mock_settings.SSO_TOKEN_URL,
            code="code123",
            client_secret="test_secret",
            include_client_id=True,
        )
        assert result == mock_token

    @patch("template_mcp_server.src.oauth.handler.settings")
    @patch("template_mcp_server.src.oauth.handler.OAuth2Handler.create_oauth_session")
    def test_get_access_token_from_refresh_token(
        self, mock_create_session, mock_settings
    ):
        """Test getting access token from refresh token."""
        mock_settings.SSO_CLIENT_ID = "client123"
        mock_settings.SSO_CLIENT_SECRET = "secret123"

        mock_session = Mock()
        mock_token = {"access_token": "new_token123", "token_type": "Bearer"}
        mock_session.refresh_token.return_value = mock_token
        mock_create_session.return_value = mock_session

        result = OAuth2Handler.get_access_token_from_refresh_token("refresh123")

        mock_create_session.assert_called_once_with()
        mock_session.refresh_token.assert_called_once_with(
            mock_settings.SSO_TOKEN_URL,
            refresh_token="refresh123",
            client_id="client123",
            client_secret="secret123",
        )
        assert result == mock_token

    @patch("template_mcp_server.src.oauth.handler.settings")
    @patch("template_mcp_server.src.oauth.handler.httpx.post")
    def test_introspect_token_success(self, mock_post, mock_settings):
        """Test successful token introspection."""
        mock_settings.SSO_CLIENT_ID = "client123"
        mock_settings.SSO_CLIENT_SECRET = "secret123"

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"active": True, "sub": "user123"}
        mock_post.return_value = mock_response

        result = OAuth2Handler.introspect_token("token123")

        mock_post.assert_called_once_with(
            mock_settings.SSO_INTROSPECTION_URL,
            data={
                "token": "token123",
                "client_id": "client123",
                "client_secret": "secret123",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        assert result == {"active": True, "sub": "user123"}

    @patch("template_mcp_server.src.oauth.handler.settings")
    @patch("template_mcp_server.src.oauth.handler.httpx.post")
    def test_introspect_token_http_error(self, mock_post, mock_settings):
        """Test token introspection with HTTP error."""
        mock_settings.SSO_CLIENT_ID = "client123"
        mock_settings.SSO_CLIENT_SECRET = "secret123"

        mock_post.side_effect = httpx.HTTPError("Connection failed")

        result = OAuth2Handler.introspect_token("token123")

        assert result["active"] is False
        assert "Introspection failed" in result["error"]

    @patch("template_mcp_server.src.oauth.handler.settings")
    @patch("template_mcp_server.src.oauth.handler.httpx.post")
    def test_introspect_token_unexpected_error(self, mock_post, mock_settings):
        """Test token introspection with unexpected error."""
        mock_settings.SSO_CLIENT_ID = "client123"
        mock_settings.SSO_CLIENT_SECRET = "secret123"

        mock_post.side_effect = Exception("Unexpected error")

        result = OAuth2Handler.introspect_token("token123")

        assert result["active"] is False
        assert "Unexpected error" in result["error"]

    @patch("template_mcp_server.src.oauth.handler.OAuth2Handler.introspect_token")
    def test_verify_access_token_active(self, mock_introspect):
        """Test verifying an active access token."""
        mock_introspect.return_value = {
            "active": True,
            "exp": time.time() + 3600,  # Expires in 1 hour
            "token_type": "Bearer",
            "sub": "user123",
        }

        result = OAuth2Handler.verify_access_token("token123")

        mock_introspect.assert_called_once_with("token123")
        assert result["active"] is True
        assert result["sub"] == "user123"

    @patch("template_mcp_server.src.oauth.handler.OAuth2Handler.introspect_token")
    def test_verify_access_token_inactive(self, mock_introspect):
        """Test verifying an inactive token."""
        mock_introspect.return_value = {"active": False}

        result = OAuth2Handler.verify_access_token("token123")

        mock_introspect.assert_called_once_with("token123")
        assert result is None

    @patch("template_mcp_server.src.oauth.handler.OAuth2Handler.introspect_token")
    def test_verify_access_token_expired(self, mock_introspect):
        """Test verifying an expired token."""
        mock_introspect.return_value = {
            "active": True,
            "exp": time.time() - 3600,  # Expired 1 hour ago
            "token_type": "Bearer",
        }

        result = OAuth2Handler.verify_access_token("token123")

        assert result is None

    @patch("template_mcp_server.src.oauth.handler.OAuth2Handler.introspect_token")
    def test_verify_access_token_invalid_type(self, mock_introspect):
        """Test verifying token with invalid type."""
        mock_introspect.return_value = {
            "active": True,
            "exp": time.time() + 3600,
            "token_type": "refresh_token",
        }

        result = OAuth2Handler.verify_access_token("token123")

        assert result is None

    @patch("template_mcp_server.src.oauth.handler.OAuth2Handler.introspect_token")
    def test_verify_access_token_no_expiry(self, mock_introspect):
        """Test verifying token without expiry."""
        mock_introspect.return_value = {
            "active": True,
            "token_type": "access_token",
            "sub": "user123",
        }

        result = OAuth2Handler.verify_access_token("token123")

        assert result["active"] is True
        assert result["sub"] == "user123"

    @patch("template_mcp_server.src.oauth.handler.OAuth2Handler.verify_access_token")
    def test_verify_authorization_header_valid(self, mock_verify):
        """Test verifying valid authorization header."""
        mock_verify.return_value = {"active": True, "sub": "user123"}

        result = OAuth2Handler.verify_authorization_header("Bearer token123")

        mock_verify.assert_called_once_with("token123")
        assert result["active"] is True

    def test_verify_authorization_header_invalid_format(self):
        """Test verifying invalid authorization header format."""
        # Test missing header
        result = OAuth2Handler.verify_authorization_header("")
        assert result is None

        # Test None header
        result = OAuth2Handler.verify_authorization_header(None)
        assert result is None

        # Test wrong format
        result = OAuth2Handler.verify_authorization_header("Basic token123")
        assert result is None

    def test_scope_constant(self):
        """Test SCOPE constant is correctly defined."""
        expected_scope = ["email", "openid", "profile", "session:role-any"]
        assert SCOPE == expected_scope


class TestOAuth2HandlerIntegration:
    """Integration tests for OAuth2Handler."""

    @patch("template_mcp_server.src.oauth.handler.settings")
    @patch("template_mcp_server.src.oauth.handler.OAuth2Session")
    @patch("template_mcp_server.src.oauth.handler.httpx.post")
    def test_full_oauth_flow_simulation(
        self, mock_post, mock_oauth_session, mock_settings
    ):
        """Test a full OAuth flow simulation."""
        # Setup
        mock_settings.SSO_CLIENT_ID = "client123"
        mock_settings.SSO_CLIENT_SECRET = "secret123"
        mock_settings.SSO_CALLBACK_URL = "http://localhost:3000/callback"

        # Mock OAuth session
        mock_session = Mock()
        mock_session.authorization_url.return_value = ("http://auth.url", "state123")
        mock_session.fetch_token.return_value = {
            "access_token": "token123",
            "refresh_token": "refresh123",
        }
        mock_oauth_session.return_value = mock_session

        # Mock introspection
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "active": True,
            "exp": time.time() + 3600,
            "token_type": "Bearer",
        }
        mock_post.return_value = mock_response

        # Test authorization URL generation
        auth_url, state = OAuth2Handler.get_authorization_url()
        assert auth_url == "http://auth.url"
        assert state == "state123"

        # Test token exchange
        token = OAuth2Handler.get_access_token_from_authorization_code_flow(
            "code123", state
        )
        assert token["access_token"] == "token123"

        # Test token verification
        verification = OAuth2Handler.verify_access_token("token123")
        assert verification["active"] is True
