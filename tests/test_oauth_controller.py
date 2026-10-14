from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

from template_mcp_server.src.oauth import controller
from template_mcp_server.src.oauth.service import OAuthService


class TestOAuthControllerHandleCallback:
    """Test handle_callback function."""

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_handle_callback_success(self, mock_settings):
        """Test successful OAuth callback handling in production mode."""
        mock_settings.USE_EXTERNAL_BROWSER_AUTH = False

        mock_request = Mock()
        mock_request.query_params.get.side_effect = lambda key: {
            "code": "sso_code_123",
            "state": "sso_state_123",
        }.get(key)

        mock_request.session = {
            "user_details": {
                "redirect_uri": "https://www.cursor.com/agents/mcp/oauth/callback",
                "state": "cursor_state_123",
            }
        }

        oauth_service = AsyncMock(spec=OAuthService)

        result = await controller.handle_callback(mock_request, oauth_service)

        assert isinstance(result, RedirectResponse)
        assert result.status_code == 302
        assert "code=sso_code_123%3A%3Asso_state_123" in result.headers["location"]
        assert "state=cursor_state_123" in result.headers["location"]

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_handle_callback_local_development(self, mock_settings):
        """Test OAuth callback handling in local development mode."""
        mock_settings.USE_EXTERNAL_BROWSER_AUTH = True

        mock_request = Mock()
        mock_request.query_params.get.side_effect = lambda key: {
            "code": "auth_code_123",
            "state": "state_123",
        }.get(key)

        mock_token = {"access_token": "dev_token_123", "refresh_token": "refresh123"}

        with (
            patch(
                "template_mcp_server.src.oauth.controller.OAuth2Handler"
            ) as mock_handler,
            patch(
                "template_mcp_server.src.oauth.controller.api_module", create=True
            ) as mock_api_module,
        ):
            mock_handler.get_access_token_from_authorization_code_flow.return_value = (
                mock_token
            )

            oauth_service = AsyncMock(spec=OAuthService)

            result = await controller.handle_callback(mock_request, oauth_service)

            mock_handler.get_access_token_from_authorization_code_flow.assert_called_once_with(
                "auth_code_123", "state_123"
            )

            assert mock_api_module._local_development_token == "dev_token_123"

            assert isinstance(result, JSONResponse)
            assert result.status_code == 200


class TestOAuthControllerHandleAuthorize:
    """Test handle_authorize function."""

    @pytest.mark.asyncio
    async def test_handle_authorize_invalid_client(self):
        """Test authorization with invalid client."""
        mock_request = Mock()
        mock_request.query_params = {
            "response_type": "code",
            "client_id": "invalid_client",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "challenge123",
            "code_challenge_method": "S256",
            "state": "state_123",
        }

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_authorize(mock_request, oauth_service)

        assert exc_info.value.status_code == 400
        assert "invalid_client" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_handle_authorize_missing_pkce(self):
        """Test authorization without PKCE parameters."""
        mock_request = Mock()
        mock_request.query_params = {
            "response_type": "code",
            "client_id": "client123",
            "redirect_uri": "http://localhost:3000/callback",
        }

        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_authorize(mock_request, oauth_service)

        assert exc_info.value.status_code == 400
        assert "invalid_request" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_handle_authorize_unsupported_response_type(self):
        """Test authorization with unsupported response type."""
        mock_request = Mock()
        mock_request.query_params = {
            "response_type": "token",
            "client_id": "client123",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "challenge123",
            "code_challenge_method": "S256",
        }

        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_authorize(mock_request, oauth_service)

        assert exc_info.value.status_code == 400
        assert "unsupported_response_type" in str(exc_info.value.detail)


class TestOAuthControllerHandleToken:
    """Test handle_token function."""

    @pytest.mark.asyncio
    async def test_handle_token_authorization_code_grant(self):
        """Test token endpoint with authorization code grant."""
        form_data = {
            "grant_type": "authorization_code",
            "code": "sso_code_123::sso_state_123",
            "redirect_uri": "https://www.cursor.com/agents/mcp/oauth/callback",
            "code_verifier": "verifier123",
        }

        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(return_value=form_data)
        mock_request.json = AsyncMock()
        mock_request.body = AsyncMock(return_value=b"")

        mock_token = {
            "access_token": "sso_access_token",
            "refresh_token": "sso_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid email profile",
        }

        oauth_service = AsyncMock(spec=OAuthService)

        with patch(
            "template_mcp_server.src.oauth.controller.OAuth2Handler"
        ) as mock_handler:
            mock_handler.get_access_token_from_authorization_code_flow.return_value = (
                mock_token
            )

            result = await controller.handle_token(mock_request, oauth_service)

            mock_handler.get_access_token_from_authorization_code_flow.assert_called_once_with(
                "sso_code_123", "sso_state_123"
            )

            assert result["access_token"] == "sso_access_token"
            assert result["refresh_token"] == "sso_refresh_token"
            assert result["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_handle_token_invalid_grant_type(self):
        """Test token endpoint with invalid grant type."""
        form_data = {"grant_type": "invalid_grant"}

        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(return_value=form_data)
        mock_request.json = AsyncMock()
        mock_request.body = AsyncMock(return_value=b"")

        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_token(mock_request, oauth_service)

        assert exc_info.value.status_code == 400
        assert "unsupported_grant_type" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_handle_token_missing_parameters(self):
        """Test token endpoint with missing required parameters."""
        form_data = {"grant_type": "authorization_code"}

        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(return_value=form_data)
        mock_request.json = AsyncMock()
        mock_request.body = AsyncMock(return_value=b"")

        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_token(mock_request, oauth_service)

        assert exc_info.value.status_code == 400
        assert "invalid_request" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_handle_token_refresh_token_grant(self):
        """Test token endpoint with refresh_token grant type via handle_token."""
        form_data = {
            "grant_type": "refresh_token",
            "refresh_token": "valid_refresh_token",
            "client_id": "test_client",
            "client_secret": "test_secret",
        }

        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(return_value=form_data)
        mock_request.json = AsyncMock()
        mock_request.body = AsyncMock(return_value=b"")

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_refresh_token = AsyncMock(
            return_value={
                "client_id": "test_client",
                "scope": "read",
            }
        )
        oauth_service.validate_client = AsyncMock(return_value={"id": "test_client"})

        result = await controller.handle_token(mock_request, oauth_service)

        assert result["access_token"] == "refreshed_access_token_placeholder"
        assert result["token_type"] == "Bearer"

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_handle_token_client_credentials_grant(self, mock_settings):
        """Test token endpoint with client_credentials grant type via handle_token."""
        mock_settings.COMPATIBLE_WITH_CURSOR = False

        form_data = {
            "grant_type": "client_credentials",
            "client_id": "test_client",
            "client_secret": "test_secret",
        }

        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(return_value=form_data)
        mock_request.json = AsyncMock()
        mock_request.body = AsyncMock(return_value=b"")

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client = AsyncMock(return_value={"id": "test_client"})

        result = await controller.handle_token(mock_request, oauth_service)

        assert result["access_token"] == "client_credentials_access_token_placeholder"
        assert result["token_type"] == "Bearer"


class TestOAuthControllerHandleRegister:
    """Test handle_register function."""

    @pytest.mark.asyncio
    async def test_handle_register_success(self):
        """Test successful client registration."""
        registration_data = {
            "client_name": "Test Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "read write",
        }

        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=registration_data)

        client_response = {
            "client_id": "client123",
            "client_secret": "secret123",
            "client_name": "Test Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "read write",
            "client_id_issued_at": 1234567890,
        }

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.register_client = AsyncMock(return_value=client_response)

        result = await controller.handle_register(mock_request, oauth_service)

        oauth_service.register_client.assert_called_once_with(
            "Test Client",
            ["http://localhost:3000/callback"],
            ["authorization_code"],
            ["code"],
            "read write",
        )

        result_dict = result.model_dump() if hasattr(result, "model_dump") else result
        assert result_dict == client_response

    @pytest.mark.asyncio
    async def test_handle_register_minimal_data(self):
        """Test client registration with minimal required data."""
        registration_data = {
            "client_name": "Minimal Client",
            "redirect_uris": ["http://localhost:3000/callback"],
        }

        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=registration_data)

        oauth_service = AsyncMock(spec=OAuthService)
        complete_client_response = {
            "client_id": "client123",
            "client_secret": "secret123",
            "client_name": "Minimal Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "read write",
            "client_id_issued_at": 1234567890,
        }
        oauth_service.register_client = AsyncMock(return_value=complete_client_response)

        result = await controller.handle_register(mock_request, oauth_service)

        oauth_service.register_client.assert_called_once_with(
            "Minimal Client",
            ["http://localhost:3000/callback"],
            [
                "authorization_code",
                "refresh_token",
            ],
            ["code"],
            "read write",
        )

        result_dict = result.model_dump() if hasattr(result, "model_dump") else result
        assert result_dict["client_id"] == "client123"


class TestOAuthControllerHandleIntrospect:
    """Test handle_introspect function."""

    @pytest.mark.asyncio
    async def test_handle_introspect_active_token(self):
        """Test token introspection with active token."""
        form_data = {
            "token": "token123",
            "client_id": "client123",
            "client_secret": "secret123",
        }

        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(return_value=form_data)
        mock_request.json = AsyncMock()
        mock_request.query_params = {}

        token_data = {
            "client_id": "client123",
            "scope": "read write",
            "expires_at": 9999999999,
        }

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client = AsyncMock(return_value={"id": "client123"})
        oauth_service.retrieve_access_token = AsyncMock(return_value=token_data)

        with patch(
            "template_mcp_server.src.oauth.controller.OAuth2Handler.introspect_token"
        ) as mock_introspect:
            mock_introspect.return_value = {
                "active": True,
                "client_id": "client123",
                "scope": "read write",
            }

            result = await controller.handle_introspect(mock_request, oauth_service)

            oauth_service.validate_client.assert_called_once_with(
                "client123", "secret123"
            )
            mock_introspect.assert_called_once_with("token123")

            assert result["active"] is True
            assert result["client_id"] == "client123"
            assert result["scope"] == "read write"

    @pytest.mark.asyncio
    async def test_handle_introspect_inactive_token(self):
        """Test token introspection with inactive token."""
        form_data = {
            "token": "invalid_token",
            "client_id": "client123",
            "client_secret": "secret123",
        }

        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(return_value=form_data)
        mock_request.json = AsyncMock()
        mock_request.query_params = {}

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client = AsyncMock(return_value={"id": "client123"})
        oauth_service.retrieve_access_token = AsyncMock(return_value=None)

        with patch(
            "template_mcp_server.src.oauth.controller.OAuth2Handler.introspect_token"
        ) as mock_introspect:
            mock_introspect.return_value = {"active": False}

            result = await controller.handle_introspect(mock_request, oauth_service)

            assert result["active"] is False

    @pytest.mark.asyncio
    async def test_handle_introspect_unauthorized_client(self):
        """Test token introspection with unauthorized client."""
        form_data = {
            "token": "token123",
            "client_id": "invalid_client",
            "client_secret": "wrong_secret",
        }

        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(return_value=form_data)
        mock_request.json = AsyncMock()
        mock_request.query_params = {}

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_introspect(mock_request, oauth_service)

        assert exc_info.value.status_code == 401
        assert "invalid_client" in str(exc_info.value.detail)


class TestOAuthControllerIntegration:
    """Integration tests for OAuth controller."""

    @pytest.mark.asyncio
    async def test_complete_oauth_flow(self):
        """Test a complete OAuth authorization code flow."""
        oauth_service = AsyncMock(spec=OAuthService)
        assert oauth_service is not None


class TestParseTokenRequest:
    """Test parse_token_request function edge cases."""

    @pytest.mark.asyncio
    async def test_parse_json_request(self):
        """Test parsing valid JSON request."""
        mock_request = Mock()
        mock_request.headers.get.return_value = "application/json"
        mock_request.json = AsyncMock(
            return_value={
                "grant_type": "authorization_code",
                "code": "test_code",
                "client_id": "test_client",
            }
        )

        result = await controller.parse_token_request(mock_request)

        assert result["grant_type"] == "authorization_code"
        assert result["code"] == "test_code"
        assert result["client_id"] == "test_client"
        mock_request.json.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_form_request(self):
        """Test parsing valid form data request."""
        mock_request = Mock()
        mock_request.headers.get.return_value = "application/x-www-form-urlencoded"
        mock_form_data = {
            "grant_type": "authorization_code",
            "code": "test_code",
            "client_id": "test_client",
        }
        mock_request.form = AsyncMock(return_value=mock_form_data)

        result = await controller.parse_token_request(mock_request)

        assert result["grant_type"] == "authorization_code"
        assert result["code"] == "test_code"
        assert result["client_id"] == "test_client"
        mock_request.form.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_request_no_content_type(self):
        """Test parsing request with no content-type header."""
        mock_request = Mock()
        mock_request.headers.get.return_value = None
        mock_form_data = {"grant_type": "authorization_code"}
        mock_request.form = AsyncMock(return_value=mock_form_data)

        result = await controller.parse_token_request(mock_request)

        assert result["grant_type"] == "authorization_code"
        mock_request.form.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_request_malformed_json(self):
        """Test parsing request with malformed JSON."""
        mock_request = Mock()
        mock_request.headers.get.return_value = "application/json"
        mock_request.json = AsyncMock(side_effect=ValueError("Invalid JSON"))

        with pytest.raises(HTTPException) as exc_info:
            await controller.parse_token_request(mock_request)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_request"
        assert "Invalid request format" in exc_info.value.detail["error_description"]

    @pytest.mark.asyncio
    async def test_parse_request_form_data_error(self):
        """Test parsing request with form data error."""
        mock_request = Mock()
        mock_request.headers.get.return_value = "application/x-www-form-urlencoded"
        mock_request.form = AsyncMock(side_effect=RuntimeError("Form parsing error"))

        with pytest.raises(HTTPException) as exc_info:
            await controller.parse_token_request(mock_request)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_request"
        assert "Invalid request format" in exc_info.value.detail["error_description"]

    @pytest.mark.asyncio
    async def test_parse_request_empty_json(self):
        """Test parsing request with empty JSON."""
        mock_request = Mock()
        mock_request.headers.get.return_value = "application/json"
        mock_request.json = AsyncMock(return_value={})

        result = await controller.parse_token_request(mock_request)

        assert result == {}

    @pytest.mark.asyncio
    async def test_parse_request_empty_form(self):
        """Test parsing request with empty form data."""
        mock_request = Mock()
        mock_request.headers.get.return_value = "application/x-www-form-urlencoded"
        mock_request.form = AsyncMock(return_value={})

        result = await controller.parse_token_request(mock_request)

        assert result == {}


class TestAuthorizationCodeGrantEdgeCases:
    """Test handle_authorization_code_grant edge cases."""

    @pytest.mark.asyncio
    async def test_successful_grant_with_sso_exchange(self):
        """Test successful authorization code grant via SSO exchange."""
        from template_mcp_server.src.oauth.models import (
            AuthorizationCodeTokenRequest,
        )

        token_request = AuthorizationCodeTokenRequest(
            grant_type="authorization_code",
            code="sso_code_123::sso_state_123",
            redirect_uri="https://www.cursor.com/agents/mcp/oauth/callback",
            code_verifier="test_verifier",
        )

        mock_token = {
            "access_token": "sso_access_token",
            "refresh_token": "sso_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid email profile",
        }

        oauth_service = AsyncMock(spec=OAuthService)

        with patch(
            "template_mcp_server.src.oauth.controller.OAuth2Handler"
        ) as mock_handler:
            mock_handler.get_access_token_from_authorization_code_flow.return_value = (
                mock_token
            )

            result = await controller.handle_authorization_code_grant(
                token_request, oauth_service
            )

            mock_handler.get_access_token_from_authorization_code_flow.assert_called_once_with(
                "sso_code_123", "sso_state_123"
            )

            assert result["access_token"] == "sso_access_token"
            assert result["refresh_token"] == "sso_refresh_token"
            assert result["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_sso_exchange_failure(self):
        """Test authorization code grant when SSO exchange fails."""
        from template_mcp_server.src.oauth.models import (
            AuthorizationCodeTokenRequest,
        )

        token_request = AuthorizationCodeTokenRequest(
            grant_type="authorization_code",
            code="invalid_code::invalid_state",
            redirect_uri="https://www.cursor.com/agents/mcp/oauth/callback",
            code_verifier="test_verifier",
        )

        oauth_service = AsyncMock(spec=OAuthService)

        with patch(
            "template_mcp_server.src.oauth.controller.OAuth2Handler"
        ) as mock_handler:
            mock_handler.get_access_token_from_authorization_code_flow.side_effect = (
                Exception("SSO exchange failed")
            )

            with pytest.raises(Exception, match="SSO exchange failed"):
                await controller.handle_authorization_code_grant(
                    token_request, oauth_service
                )


class TestRefreshTokenGrantEdgeCases:
    """Test handle_refresh_token_grant_pydantic edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_refresh_token(self):
        """Test with invalid refresh token."""
        from template_mcp_server.src.oauth.models import RefreshTokenRequest

        token_request = RefreshTokenRequest(
            grant_type="refresh_token",
            refresh_token="invalid_refresh_token",
            client_id="test_client",
            client_secret="test_secret",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_refresh_token.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_refresh_token_grant_pydantic(
                token_request, oauth_service
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_grant"
        assert (
            "Invalid or expired refresh token"
            in exc_info.value.detail["error_description"]
        )
        oauth_service.validate_refresh_token.assert_called_once_with(
            "invalid_refresh_token"
        )

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_invalid_client_credentials_refresh(self, mock_settings):
        """Test refresh token grant with invalid client credentials."""
        mock_settings.COMPATIBLE_WITH_CURSOR = False

        from template_mcp_server.src.oauth.models import RefreshTokenRequest

        token_request = RefreshTokenRequest(
            grant_type="refresh_token",
            refresh_token="valid_refresh_token",
            client_id="invalid_client",
            client_secret="invalid_secret",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_refresh_token.return_value = {
            "client_id": "test_client",
            "scope": "read",
        }
        oauth_service.validate_client.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_refresh_token_grant_pydantic(
                token_request, oauth_service
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_client"
        assert (
            "Invalid client credentials" in exc_info.value.detail["error_description"]
        )

    @pytest.mark.asyncio
    async def test_successful_refresh_with_snowflake_token(self):
        """Test successful refresh token grant with Snowflake token."""
        from template_mcp_server.src.oauth.models import RefreshTokenRequest

        token_request = RefreshTokenRequest(
            grant_type="refresh_token",
            refresh_token="valid_refresh_token",
            client_id="test_client",
            client_secret="test_secret",
            scope="read write",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_refresh_token.return_value = {
            "client_id": "test_client",
            "scope": "read",
            "snowflake_refresh_token": "snowflake_refresh_token",
        }
        oauth_service.validate_client.return_value = {"id": "test_client"}

        with patch(
            "template_mcp_server.src.oauth.controller.OAuth2Handler"
        ) as mock_handler:
            mock_handler.get_access_token_from_refresh_token.return_value = {
                "access_token": "new_snowflake_access_token",
                "refresh_token": "new_snowflake_refresh_token",
                "expires_in": 7200,
            }

            result = await controller.handle_refresh_token_grant_pydantic(
                token_request, oauth_service
            )

            assert result["access_token"] == "new_snowflake_access_token"
            assert result["refresh_token"] == "new_snowflake_refresh_token"
            assert result["token_type"] == "Bearer"
            assert result["expires_in"] == 7200
            assert result["scope"] == "read write"

            mock_handler.get_access_token_from_refresh_token.assert_called_once_with(
                "snowflake_refresh_token"
            )

    @pytest.mark.asyncio
    async def test_snowflake_refresh_failure_fallback(self):
        """Test fallback when Snowflake token refresh fails."""
        from template_mcp_server.src.oauth.models import RefreshTokenRequest

        token_request = RefreshTokenRequest(
            grant_type="refresh_token",
            refresh_token="valid_refresh_token",
            client_id="test_client",
            client_secret="test_secret",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_refresh_token.return_value = {
            "client_id": "test_client",
            "scope": "read",
            "snowflake_refresh_token": "invalid_snowflake_refresh_token",
        }
        oauth_service.validate_client.return_value = {"id": "test_client"}

        with patch(
            "template_mcp_server.src.oauth.controller.OAuth2Handler"
        ) as mock_handler:
            mock_handler.get_access_token_from_refresh_token.side_effect = Exception(
                "Snowflake error"
            )

            result = await controller.handle_refresh_token_grant_pydantic(
                token_request, oauth_service
            )

            assert result["access_token"] == "refreshed_access_token_placeholder"
            assert result["token_type"] == "Bearer"
            assert result["expires_in"] == 3600
            assert result["scope"] == "read"

    @pytest.mark.asyncio
    async def test_successful_refresh_without_snowflake_token(self):
        """Test successful refresh token grant without Snowflake token."""
        from template_mcp_server.src.oauth.models import RefreshTokenRequest

        token_request = RefreshTokenRequest(
            grant_type="refresh_token",
            refresh_token="valid_refresh_token",
            client_id="test_client",
            client_secret="test_secret",
            scope="write",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_refresh_token.return_value = {
            "client_id": "test_client",
            "scope": "read",
        }
        oauth_service.validate_client.return_value = {"id": "test_client"}

        result = await controller.handle_refresh_token_grant_pydantic(
            token_request, oauth_service
        )

        assert result["access_token"] == "refreshed_access_token_placeholder"
        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 3600
        assert result["scope"] == "write"


class TestClientCredentialsGrantEdgeCases:
    """Test handle_client_credentials_grant_pydantic edge cases."""

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_invalid_client_credentials(self, mock_settings):
        """Test client credentials grant with invalid credentials."""
        mock_settings.COMPATIBLE_WITH_CURSOR = False

        from template_mcp_server.src.oauth.models import (
            ClientCredentialsTokenRequest,
        )

        token_request = ClientCredentialsTokenRequest(
            grant_type="client_credentials",
            client_id="invalid_client",
            client_secret="invalid_secret",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_client_credentials_grant_pydantic(
                token_request, oauth_service
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_client"
        assert (
            "Invalid client credentials" in exc_info.value.detail["error_description"]
        )
        oauth_service.validate_client.assert_called_once_with(
            "invalid_client", "invalid_secret"
        )

    @pytest.mark.asyncio
    async def test_successful_client_credentials_grant(self):
        """Test successful client credentials grant."""
        from template_mcp_server.src.oauth.models import (
            ClientCredentialsTokenRequest,
        )

        token_request = ClientCredentialsTokenRequest(
            grant_type="client_credentials",
            client_id="test_client",
            client_secret="test_secret",
            scope="admin",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client.return_value = {"id": "test_client"}

        result = await controller.handle_client_credentials_grant_pydantic(
            token_request, oauth_service
        )

        assert result["access_token"] == "client_credentials_access_token_placeholder"
        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 3600
        assert result["scope"] == "admin"

    @pytest.mark.asyncio
    async def test_successful_client_credentials_grant_default_scope(self):
        """Test successful client credentials grant with default scope."""
        from template_mcp_server.src.oauth.models import (
            ClientCredentialsTokenRequest,
        )

        token_request = ClientCredentialsTokenRequest(
            grant_type="client_credentials",
            client_id="test_client",
            client_secret="test_secret",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client.return_value = {"id": "test_client"}

        result = await controller.handle_client_credentials_grant_pydantic(
            token_request, oauth_service
        )

        assert result["access_token"] == "client_credentials_access_token_placeholder"
        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 3600
        assert result["scope"] == "client"
