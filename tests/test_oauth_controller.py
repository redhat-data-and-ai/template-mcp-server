from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

from template_mcp_server.src.oauth import controller
from template_mcp_server.src.oauth.service import OAuthService


class TestOAuthControllerHandleCallback:
    """Verifies that iss is present in the redirect AND that the value matches the configured MCP_HOST_ENDPOINT (URL-encoded in the query string)."""

    @patch(
        "template_mcp_server.src.oauth.controller.get_current_issuer",
        return_value="https://mcp.example.com",
    )
    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_handle_callback_success(self, mock_settings, _mock_issuer):
        """Test successful OAuth callback handling with RFC 9207 iss parameter (SEP-2468)."""
        mock_settings.USE_EXTERNAL_BROWSER_AUTH = False

        mock_request = Mock()
        mock_request.query_params.get.side_effect = lambda key: {
            "code": "auth_code_123",
            "state": "state_123",
        }.get(key)

        mock_request.session = {
            "user_details": {
                "auth_code": "stored_code_123",
                "redirect_uri": "http://localhost:3000/callback",
            }
        }

        mock_token = {"access_token": "token123", "refresh_token": "refresh123"}

        with patch(
            "template_mcp_server.src.oauth.controller.OAuth2Handler"
        ) as mock_handler:
            mock_handler.get_access_token_from_authorization_code_flow.return_value = (
                mock_token
            )

            oauth_service = AsyncMock(spec=OAuthService)
            oauth_service.add_token_to_code = AsyncMock()

            result = await controller.handle_callback(mock_request, oauth_service)

            mock_handler.get_access_token_from_authorization_code_flow.assert_called_once_with(
                "auth_code_123", "state_123"
            )

            oauth_service.add_token_to_code.assert_called_once_with(
                "stored_code_123", mock_token
            )

            assert isinstance(result, RedirectResponse)
            assert result.status_code == 302
            assert "code=stored_code_123" in result.headers["location"]
            assert "iss=https%3A%2F%2Fmcp.example.com" in result.headers["location"]

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_handle_callback_missing_session_data(self, mock_settings):
        """Test callback handling with missing session data in production mode."""
        # Set production mode to test original flow
        mock_settings.USE_EXTERNAL_BROWSER_AUTH = False

        mock_request = Mock()
        mock_request.query_params.get.side_effect = lambda key: {
            "code": "auth_code_123",
            "state": "state_123",
        }.get(key)

        # Missing user_details in session
        mock_request.session = {}

        with patch(
            "template_mcp_server.src.oauth.controller.OAuth2Handler"
        ) as mock_handler:
            mock_handler.get_access_token_from_authorization_code_flow.return_value = {
                "access_token": "token"
            }

            # Create mock OAuth service
            oauth_service = AsyncMock(spec=OAuthService)

            # Should raise HTTPException when session data is missing
            with pytest.raises(HTTPException) as exc_info:
                await controller.handle_callback(mock_request, oauth_service)
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail["error"] == "invalid_request"

    @pytest.mark.asyncio
    async def test_handle_callback_missing_code_param(self):
        """Test callback handling when code or state query param is missing."""
        mock_request = Mock()
        mock_request.query_params.get.side_effect = lambda key: {
            "code": None,
            "state": "state_123",
        }.get(key)

        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_callback(mock_request, oauth_service)
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_request"
        assert (
            "Missing code or state parameter"
            in exc_info.value.detail["error_description"]
        )

    @pytest.mark.asyncio
    async def test_handle_callback_missing_state_param(self):
        """Test callback handling when state query param is missing."""
        mock_request = Mock()
        mock_request.query_params.get.side_effect = lambda key: {
            "code": "auth_code_123",
            "state": None,
        }.get(key)

        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_callback(mock_request, oauth_service)
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_request"

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_handle_callback_local_development(self, mock_settings):
        """Test OAuth callback handling in local development mode."""
        # Set local development mode
        mock_settings.USE_EXTERNAL_BROWSER_AUTH = True

        # Mock request
        mock_request = Mock()
        mock_request.query_params.get.side_effect = lambda key: {
            "code": "auth_code_123",
            "state": "state_123",
        }.get(key)

        # Mock OAuth2Handler
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

            # Create mock OAuth service
            oauth_service = AsyncMock(spec=OAuthService)

            result = await controller.handle_callback(mock_request, oauth_service)

            # Verify OAuth2Handler was called correctly
            mock_handler.get_access_token_from_authorization_code_flow.assert_called_once_with(
                "auth_code_123", "state_123"
            )

            # Verify token was stored in local development mode
            assert mock_api_module._local_development_token == "dev_token_123"

            # Verify JSON response returned
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

        # Create mock OAuth service
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
            # Missing code_challenge and code_challenge_method
        }

        # Create mock OAuth service
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
            "response_type": "token",  # Unsupported
            "client_id": "client123",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "challenge123",
            "code_challenge_method": "S256",
        }

        # Create mock OAuth service
        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_authorize(mock_request, oauth_service)

        assert exc_info.value.status_code == 400
        assert "unsupported_response_type" in str(exc_info.value.detail)


class TestOAuthControllerHandleToken:
    """Test handle_token function."""

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_handle_token_authorization_code_grant(self, mock_settings):
        """Test token endpoint with authorization code grant."""
        mock_settings.COMPATIBLE_WITH_CURSOR = False
        mock_settings.ACCESS_TOKEN_EXPIRY = 3600

        # Mock form data
        form_data = {
            "grant_type": "authorization_code",
            "code": "code123",
            "redirect_uri": "http://localhost:3000/callback",
            "client_id": "client123",
            "client_secret": "secret123",
            "code_verifier": "verifier123",
        }

        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(return_value=form_data)
        mock_request.json = AsyncMock()
        mock_request.body = AsyncMock(return_value=b"")

        # Mock code data
        code_data = {
            "client_id": "client123",
            "issuer": "http://localhost:5001",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "challenge123",
            "snowflake_token": {
                "access_token": "snowflake_access",
                "refresh_token": "snowflake_refresh",
            },
        }

        # Create mock OAuth service
        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.issuer = "http://localhost:5001"
        oauth_service.validate_authorization_code = AsyncMock(return_value=code_data)
        oauth_service.validate_client = AsyncMock(return_value={"id": "client123"})
        oauth_service.mark_code_as_used = AsyncMock()

        with patch(
            "template_mcp_server.src.oauth.controller.verify_code_challenge",
            return_value=True,
        ):
            result = await controller.handle_token(mock_request, oauth_service)

            # Verify service calls
            oauth_service.validate_authorization_code.assert_called_once_with("code123")
            oauth_service.validate_client.assert_called_once_with(
                "client123", "secret123"
            )
            oauth_service.mark_code_as_used.assert_called_once_with("code123")

            # Verify response
            assert result["access_token"] == "snowflake_access"
            assert result["refresh_token"] == "snowflake_refresh"
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
        form_data = {
            "grant_type": "authorization_code"
            # Missing code, redirect_uri, client_id, code_verifier
        }

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
            "application_type": "native",
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
            None,
        )

        # Convert Pydantic model to dict for comparison
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
        # Mock a complete client response for Pydantic validation
        complete_client_response = {
            "client_id": "client123",
            "client_secret": "secret123",
            "client_name": "Minimal Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "read write",
            "application_type": "native",
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
            ],  # Default grant types from Pydantic model
            ["code"],  # Default response types from Pydantic model
            "read write",  # Default scope from Pydantic model
            None,  # application_type not provided, will be inferred
        )

        # Convert Pydantic model to dict for comparison
        result_dict = result.model_dump() if hasattr(result, "model_dump") else result
        assert result_dict["client_id"] == "client123"

    @pytest.mark.asyncio
    async def test_handle_register_with_application_type(self):
        """Test client registration with explicit application_type."""
        registration_data = {
            "client_name": "Native App",
            "redirect_uris": ["myapp://callback"],
            "application_type": "native",
        }

        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=registration_data)

        client_response = {
            "client_id": "client456",
            "client_secret": "secret456",
            "client_name": "Native App",
            "redirect_uris": ["myapp://callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "read write",
            "application_type": "native",
            "client_id_issued_at": 1234567890,
        }

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.register_client = AsyncMock(return_value=client_response)

        result = await controller.handle_register(mock_request, oauth_service)

        oauth_service.register_client.assert_called_once_with(
            "Native App",
            ["myapp://callback"],
            ["authorization_code", "refresh_token"],
            ["code"],
            "read write",
            "native",
        )

        result_dict = result.model_dump() if hasattr(result, "model_dump") else result
        assert result_dict["application_type"] == "native"


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
            "expires_at": 9999999999,  # Far future
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
    async def test_invalid_authorization_code(self):
        """Test with invalid authorization code."""
        from template_mcp_server.src.oauth.models import (
            AuthorizationCodeTokenRequest,
        )

        token_request = AuthorizationCodeTokenRequest(
            grant_type="authorization_code",
            code="invalid_code",
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost:3000/callback",
            code_verifier="test_verifier",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_authorization_code.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_authorization_code_grant(
                token_request, oauth_service
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_grant"
        assert (
            "Invalid or expired authorization code"
            in exc_info.value.detail["error_description"]
        )
        oauth_service.validate_authorization_code.assert_called_once_with(
            "invalid_code"
        )

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_invalid_client_credentials(self, mock_settings):
        """Test with invalid client credentials."""
        mock_settings.COMPATIBLE_WITH_CURSOR = False

        from template_mcp_server.src.oauth.models import (
            AuthorizationCodeTokenRequest,
        )

        token_request = AuthorizationCodeTokenRequest(
            grant_type="authorization_code",
            code="valid_code",
            client_id="invalid_client",
            client_secret="invalid_secret",
            redirect_uri="http://localhost:3000/callback",
            code_verifier="test_verifier",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.issuer = "http://localhost:5001"
        oauth_service.validate_authorization_code.return_value = {
            "client_id": "test_client",
            "issuer": "http://localhost:5001",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "test_challenge",
            "scope": "read",
        }
        oauth_service.validate_client.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_authorization_code_grant(
                token_request, oauth_service
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_client"
        assert (
            "Invalid client credentials" in exc_info.value.detail["error_description"]
        )

    @pytest.mark.asyncio
    async def test_redirect_uri_mismatch(self):
        """Test with mismatched redirect URI."""
        from template_mcp_server.src.oauth.models import (
            AuthorizationCodeTokenRequest,
        )

        token_request = AuthorizationCodeTokenRequest(
            grant_type="authorization_code",
            code="valid_code",
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost:3000/different",
            code_verifier="test_verifier",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.issuer = "http://localhost:5001"
        oauth_service.validate_authorization_code.return_value = {
            "client_id": "test_client",
            "issuer": "http://localhost:5001",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "test_challenge",
            "scope": "read",
        }
        oauth_service.validate_client.return_value = {"id": "test_client"}

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_authorization_code_grant(
                token_request, oauth_service
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_grant"
        assert "Redirect URI mismatch" in exc_info.value.detail["error_description"]

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_pkce_verification_failure(self, mock_settings):
        """Test with PKCE verification failure."""
        mock_settings.COMPATIBLE_WITH_CURSOR = False

        from template_mcp_server.src.oauth.models import (
            AuthorizationCodeTokenRequest,
        )

        token_request = AuthorizationCodeTokenRequest(
            grant_type="authorization_code",
            code="valid_code",
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost:3000/callback",
            code_verifier="wrong_verifier",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.issuer = "http://localhost:5001"
        oauth_service.validate_authorization_code.return_value = {
            "client_id": "test_client",
            "issuer": "http://localhost:5001",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "test_challenge",
            "scope": "read",
        }
        oauth_service.validate_client.return_value = {"id": "test_client"}

        with patch(
            "template_mcp_server.src.oauth.controller.verify_code_challenge"
        ) as mock_verify:
            mock_verify.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await controller.handle_authorization_code_grant(
                    token_request, oauth_service
                )

            assert exc_info.value.status_code == 400
            assert exc_info.value.detail["error"] == "invalid_grant"
            assert "Invalid code verifier" in exc_info.value.detail["error_description"]
            mock_verify.assert_called_once_with("wrong_verifier", "test_challenge")

    @pytest.mark.asyncio
    async def test_successful_grant_with_snowflake_tokens(self):
        """Test successful authorization code grant with Snowflake tokens."""
        from template_mcp_server.src.oauth.models import (
            AuthorizationCodeTokenRequest,
        )

        token_request = AuthorizationCodeTokenRequest(
            grant_type="authorization_code",
            code="valid_code",
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost:3000/callback",
            code_verifier="test_verifier",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.issuer = "http://localhost:5001"
        oauth_service.validate_authorization_code.return_value = {
            "client_id": "test_client",
            "issuer": "http://localhost:5001",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "test_challenge",
            "scope": "read write",
            "snowflake_token": {
                "access_token": "snowflake_access_token",
                "refresh_token": "snowflake_refresh_token",
            },
        }
        oauth_service.validate_client.return_value = {"id": "test_client"}
        oauth_service.mark_code_as_used = AsyncMock()

        with patch(
            "template_mcp_server.src.oauth.controller.verify_code_challenge"
        ) as mock_verify:
            mock_verify.return_value = True

            result = await controller.handle_authorization_code_grant(
                token_request, oauth_service
            )

            assert result["access_token"] == "snowflake_access_token"
            assert result["refresh_token"] == "snowflake_refresh_token"
            assert result["token_type"] == "Bearer"
            assert result["expires_in"] == 3600
            assert result["scope"] == "read write"

            oauth_service.mark_code_as_used.assert_called_once_with("valid_code")

    @pytest.mark.asyncio
    async def test_successful_grant_without_snowflake_tokens(self):
        """Test successful authorization code grant without Snowflake tokens."""
        from template_mcp_server.src.oauth.models import (
            AuthorizationCodeTokenRequest,
        )

        token_request = AuthorizationCodeTokenRequest(
            grant_type="authorization_code",
            code="valid_code",
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost:3000/callback",
            code_verifier="test_verifier",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.issuer = "http://localhost:5001"
        oauth_service.validate_authorization_code.return_value = {
            "client_id": "test_client",
            "issuer": "http://localhost:5001",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "test_challenge",
            "scope": "read",
        }
        oauth_service.validate_client.return_value = {"id": "test_client"}
        oauth_service.mark_code_as_used = AsyncMock()

        with patch(
            "template_mcp_server.src.oauth.controller.verify_code_challenge"
        ) as mock_verify:
            mock_verify.return_value = True

            result = await controller.handle_authorization_code_grant(
                token_request, oauth_service
            )

            assert result["access_token"]
            assert "placeholder" not in result["access_token"]
            assert result["token_type"] == "Bearer"
            assert result["expires_in"] == 3600
            assert result["scope"] == "read"
            assert "refresh_token" not in result

            oauth_service.mark_code_as_used.assert_called_once_with("valid_code")
            oauth_service.store_access_token.assert_called_once()
            call_args = oauth_service.store_access_token.call_args
            assert call_args[0][0] == result["access_token"]
            assert call_args[0][1]["client_id"] == "test_client"
            assert call_args[0][1]["scope"] == "read"
            assert "expires_at" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_authorization_code_cross_issuer_rejection(self):
        """Test that auth code from a different issuer is rejected (SEP-2352)."""
        from template_mcp_server.src.oauth.models import AuthorizationCodeTokenRequest

        token_request = AuthorizationCodeTokenRequest(
            grant_type="authorization_code",
            code="valid_code",
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost:3000/callback",
            code_verifier="test_verifier",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.issuer = "http://current-issuer.com"
        oauth_service.validate_authorization_code.return_value = {
            "client_id": "test_client",
            "issuer": "http://different-issuer.com",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "test_challenge",
            "scope": "read",
        }

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_authorization_code_grant(
                token_request, oauth_service
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_grant"
        assert (
            "different authorization server"
            in exc_info.value.detail["error_description"]
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

            assert result["access_token"]
            assert "placeholder" not in result["access_token"]
            assert result["token_type"] == "Bearer"
            assert result["expires_in"] == 3600
            assert result["scope"] == "read"
            oauth_service.store_access_token.assert_called_once()

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

        assert result["access_token"]
        assert "placeholder" not in result["access_token"]
        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 3600
        assert result["scope"] == "write"
        oauth_service.store_access_token.assert_called_once()
        call_args = oauth_service.store_access_token.call_args
        assert call_args[0][0] == result["access_token"]

    @pytest.mark.asyncio
    async def test_refresh_token_cross_issuer_rejection(self):
        """Test that refresh token from a different issuer is rejected (SEP-2352)."""
        from template_mcp_server.src.oauth.models import RefreshTokenRequest

        token_request = RefreshTokenRequest(
            grant_type="refresh_token",
            refresh_token="valid_refresh_token",
            client_id="test_client",
            client_secret="test_secret",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.issuer = "http://current-issuer.com"
        oauth_service.validate_refresh_token.return_value = {
            "client_id": "test_client",
            "issuer": "http://different-issuer.com",
            "scope": "read",
        }

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_refresh_token_grant_pydantic(
                token_request, oauth_service
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_grant"
        assert (
            "different authorization server"
            in exc_info.value.detail["error_description"]
        )

    @pytest.mark.asyncio
    async def test_refresh_token_same_issuer_accepted(self):
        """Test that refresh token from the same issuer is accepted (SEP-2352)."""
        from template_mcp_server.src.oauth.models import RefreshTokenRequest

        token_request = RefreshTokenRequest(
            grant_type="refresh_token",
            refresh_token="valid_refresh_token",
            client_id="test_client",
            client_secret="test_secret",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.issuer = "http://same-issuer.com"
        oauth_service.validate_refresh_token.return_value = {
            "client_id": "test_client",
            "issuer": "http://same-issuer.com",
            "scope": "read",
        }
        oauth_service.validate_client.return_value = {"id": "test_client"}

        result = await controller.handle_refresh_token_grant_pydantic(
            token_request, oauth_service
        )

        assert result["access_token"]
        assert "placeholder" not in result["access_token"]
        assert result["token_type"] == "Bearer"
        oauth_service.store_access_token.assert_called_once()


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

        assert result["access_token"]
        assert "placeholder" not in result["access_token"]
        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 3600
        assert result["scope"] == "admin"
        oauth_service.store_access_token.assert_called_once()

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

        assert result["access_token"]
        assert "placeholder" not in result["access_token"]
        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 3600
        assert result["scope"] == "client"
        oauth_service.store_access_token.assert_called_once()
        call_args = oauth_service.store_access_token.call_args
        assert call_args[0][0] == result["access_token"]
        assert call_args[0][1]["client_id"] == "test_client"


class TestTokenGenerationAndStorage:
    """Test that real tokens are generated and stored instead of placeholders."""

    @pytest.mark.asyncio
    async def test_auth_code_grant_generates_unique_tokens(self):
        """Test that each auth code grant produces a unique token."""
        from template_mcp_server.src.oauth.models import AuthorizationCodeTokenRequest

        token_request = AuthorizationCodeTokenRequest(
            grant_type="authorization_code",
            code="valid_code",
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost:3000/callback",
            code_verifier="test_verifier",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.issuer = "http://localhost:5001"
        oauth_service.validate_authorization_code.return_value = {
            "client_id": "test_client",
            "issuer": "http://localhost:5001",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "test_challenge",
            "scope": "read",
        }
        oauth_service.validate_client.return_value = {"id": "test_client"}
        oauth_service.mark_code_as_used = AsyncMock()

        with patch(
            "template_mcp_server.src.oauth.controller.verify_code_challenge",
            return_value=True,
        ):
            result1 = await controller.handle_authorization_code_grant(
                token_request, oauth_service
            )
            result2 = await controller.handle_authorization_code_grant(
                token_request, oauth_service
            )

            assert result1["access_token"] != result2["access_token"]

    @pytest.mark.asyncio
    async def test_access_token_expiry_uses_settings(self):
        """Test that token expiry comes from settings.ACCESS_TOKEN_EXPIRY."""
        from template_mcp_server.src.oauth.models import ClientCredentialsTokenRequest

        token_request = ClientCredentialsTokenRequest(
            grant_type="client_credentials",
            client_id="test_client",
            client_secret="test_secret",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client.return_value = {"id": "test_client"}

        with patch(
            "template_mcp_server.src.oauth.controller.settings"
        ) as mock_settings:
            mock_settings.COMPATIBLE_WITH_CURSOR = False
            mock_settings.ACCESS_TOKEN_EXPIRY = 7200

            result = await controller.handle_client_credentials_grant_pydantic(
                token_request, oauth_service
            )

            assert result["expires_in"] == 7200


class TestHandleAuthorizeFullCoverage:
    """Cover remaining branches in handle_authorize."""

    @pytest.mark.asyncio
    async def test_handle_authorize_missing_required_params(self):
        """Test authorization with response_type but missing client_id."""
        mock_request = Mock()
        mock_request.query_params = {
            "response_type": "code",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "challenge123",
            "code_challenge_method": "S256",
        }

        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_authorize(mock_request, oauth_service)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_request"
        assert (
            "Missing required parameters" in exc_info.value.detail["error_description"]
        )

    @pytest.mark.asyncio
    async def test_handle_authorize_invalid_redirect_uri(self):
        """Test authorization with redirect_uri not in client's registered list."""
        mock_request = Mock()
        mock_request.query_params = {
            "response_type": "code",
            "client_id": "client123",
            "redirect_uri": "http://evil.com/callback",
            "code_challenge": "challenge123",
            "code_challenge_method": "S256",
            "scope": "read",
            "state": "state_123",
        }

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client.return_value = {
            "id": "client123",
            "redirect_uris": ["http://localhost:3000/callback"],
        }

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_authorize(mock_request, oauth_service)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_request"
        assert "Invalid redirect_uri" in exc_info.value.detail["error_description"]

    @pytest.mark.asyncio
    async def test_handle_authorize_success(self):
        """Test successful authorization flow generates code and redirects."""
        mock_request = Mock()
        mock_request.query_params = {
            "response_type": "code",
            "client_id": "client123",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "challenge123",
            "code_challenge_method": "S256",
            "scope": "read",
            "state": "state_123",
        }
        mock_request.session = {}

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client.return_value = {
            "id": "client123",
            "redirect_uris": ["http://localhost:3000/callback"],
        }
        oauth_service.create_authorization_code.return_value = "auth_code_123"

        with patch(
            "template_mcp_server.src.oauth.controller.OAuth2Handler"
        ) as mock_handler:
            mock_handler.get_authorization_url.return_value = (
                "https://sso.example.com/authorize?state=xyz",
                "xyz",
            )

            result = await controller.handle_authorize(mock_request, oauth_service)

            assert isinstance(result, RedirectResponse)
            assert result.status_code == 302
            oauth_service.create_authorization_code.assert_called_once()
            assert mock_request.session["user_details"]["auth_code"] == "auth_code_123"

    @pytest.mark.asyncio
    async def test_handle_authorize_generic_exception(self):
        """Test that unexpected exceptions in handle_authorize return 500."""
        mock_request = Mock()
        mock_request.query_params = {
            "response_type": "code",
            "client_id": "client123",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "challenge123",
            "code_challenge_method": "S256",
        }

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client.side_effect = RuntimeError("Unexpected DB error")

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_authorize(mock_request, oauth_service)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error"] == "server_error"


class TestHandleTokenFullCoverage:
    """Cover remaining branches in handle_token."""

    @pytest.mark.asyncio
    async def test_handle_token_missing_grant_type(self):
        """Test token endpoint with no grant_type field."""
        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(return_value={"client_id": "test"})

        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_token(mock_request, oauth_service)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_request"
        assert "Missing grant_type" in exc_info.value.detail["error_description"]

    @pytest.mark.asyncio
    async def test_handle_token_refresh_validation_error(self):
        """Test token endpoint with invalid refresh_token request fields."""
        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(return_value={"grant_type": "refresh_token"})

        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_token(mock_request, oauth_service)

        assert exc_info.value.status_code == 400
        assert "invalid_request" in str(exc_info.value.detail)

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_handle_token_refresh_token_happy_path(self, mock_settings):
        """Test token endpoint dispatches refresh_token grant through handle_token."""
        mock_settings.COMPATIBLE_WITH_CURSOR = True
        mock_settings.ACCESS_TOKEN_EXPIRY = 3600

        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(
            return_value={
                "grant_type": "refresh_token",
                "refresh_token": "rt_valid",
                "client_id": "client123",
            }
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.issuer = "http://localhost:5001"
        oauth_service.validate_refresh_token.return_value = {
            "client_id": "client123",
            "issuer": "http://localhost:5001",
            "scope": "read",
        }
        oauth_service.store_access_token.return_value = True

        result = await controller.handle_token(mock_request, oauth_service)

        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 3600
        oauth_service.validate_refresh_token.assert_called_once_with("rt_valid")

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_handle_token_client_credentials_happy_path(self, mock_settings):
        """Test token endpoint dispatches client_credentials grant through handle_token."""
        mock_settings.COMPATIBLE_WITH_CURSOR = True
        mock_settings.ACCESS_TOKEN_EXPIRY = 3600

        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(
            return_value={
                "grant_type": "client_credentials",
                "client_id": "client123",
                "client_secret": "secret123",
            }
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.store_access_token.return_value = True

        result = await controller.handle_token(mock_request, oauth_service)

        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 3600
        assert result["scope"] == "client"

    @pytest.mark.asyncio
    async def test_handle_token_client_credentials_validation_error(self):
        """Test token endpoint with invalid client_credentials request fields."""
        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/json"}
        mock_request.json = AsyncMock(
            return_value={"grant_type": "client_credentials", "client_id": 12345}
        )

        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_token(mock_request, oauth_service)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_handle_token_generic_exception(self):
        """Test that unexpected exceptions in handle_token return 500."""
        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(
            return_value={
                "grant_type": "authorization_code",
                "code": "c",
                "redirect_uri": "http://x",
                "client_id": "cid",
                "code_verifier": "v",
            }
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_authorization_code = AsyncMock(
            side_effect=RuntimeError("unexpected")
        )

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_token(mock_request, oauth_service)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error"] == "server_error"


class TestClientIdRequiredBranches:
    """Cover the client_id-is-None branches when COMPATIBLE_WITH_CURSOR=False."""

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_auth_code_grant_missing_client_id(self, mock_settings):
        """Test auth code grant raises when client_id is None."""
        mock_settings.COMPATIBLE_WITH_CURSOR = False

        from template_mcp_server.src.oauth.models import AuthorizationCodeTokenRequest

        token_request = AuthorizationCodeTokenRequest(
            grant_type="authorization_code",
            code="valid_code",
            redirect_uri="http://localhost:3000/callback",
            code_verifier="test_verifier",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.issuer = "http://localhost:5001"
        oauth_service.validate_authorization_code.return_value = {
            "client_id": "test_client",
            "issuer": "http://localhost:5001",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "test_challenge",
            "scope": "read",
        }

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_authorization_code_grant(
                token_request, oauth_service
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_client"
        assert "Client ID is required" in exc_info.value.detail["error_description"]

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_refresh_grant_missing_client_id(self, mock_settings):
        """Test refresh grant raises when client_id is None."""
        mock_settings.COMPATIBLE_WITH_CURSOR = False

        from template_mcp_server.src.oauth.models import RefreshTokenRequest

        token_request = RefreshTokenRequest(
            grant_type="refresh_token",
            refresh_token="valid_refresh",
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_refresh_token.return_value = {
            "client_id": "test_client",
            "scope": "read",
        }

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_refresh_token_grant_pydantic(
                token_request, oauth_service
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_client"
        assert "Client ID is required" in exc_info.value.detail["error_description"]

    @patch("template_mcp_server.src.oauth.controller.settings")
    @pytest.mark.asyncio
    async def test_client_credentials_missing_client_id(self, mock_settings):
        """Test client_credentials grant raises when client_id is None."""
        mock_settings.COMPATIBLE_WITH_CURSOR = False

        from template_mcp_server.src.oauth.models import ClientCredentialsTokenRequest

        token_request = ClientCredentialsTokenRequest(
            grant_type="client_credentials",
        )

        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_client_credentials_grant_pydantic(
                token_request, oauth_service
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_client"
        assert "Client ID is required" in exc_info.value.detail["error_description"]


class TestHandleRegisterFullCoverage:
    """Cover remaining branches in handle_register."""

    @pytest.mark.asyncio
    async def test_handle_register_validation_error(self):
        """Test registration with invalid request body."""
        mock_request = Mock()
        mock_request.json = AsyncMock(return_value={"invalid_field": "value"})

        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_register(mock_request, oauth_service)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_request"

    @pytest.mark.asyncio
    async def test_handle_register_generic_exception(self):
        """Test registration with unexpected internal error."""
        mock_request = Mock()
        mock_request.json = AsyncMock(
            return_value={
                "client_name": "Test",
                "redirect_uris": ["http://localhost:3000/cb"],
            }
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.register_client.side_effect = RuntimeError("DB error")

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_register(mock_request, oauth_service)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error"] == "server_error"


class TestHandleIntrospectFullCoverage:
    """Cover remaining branches in handle_introspect."""

    @pytest.mark.asyncio
    async def test_handle_introspect_json_content_type(self):
        """Test introspection with application/json content type."""
        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/json"}
        mock_request.json = AsyncMock(
            return_value={
                "token": "token123",
                "client_id": "client123",
                "client_secret": "secret123",
            }
        )

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client.return_value = {"id": "client123"}

        with patch(
            "template_mcp_server.src.oauth.controller.OAuth2Handler.introspect_token"
        ) as mock_introspect:
            mock_introspect.return_value = {"active": True}

            result = await controller.handle_introspect(mock_request, oauth_service)

            assert result["active"] is True
            mock_request.json.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_introspect_missing_token(self):
        """Test introspection when token parameter is missing."""
        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(
            return_value={"client_id": "client123", "client_secret": "secret123"}
        )
        mock_request.query_params = {}

        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_introspect(mock_request, oauth_service)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "invalid_request"
        assert "Missing token" in exc_info.value.detail["error_description"]

    @pytest.mark.asyncio
    async def test_handle_introspect_basic_auth(self):
        """Test introspection with Basic auth header."""
        import base64

        credentials = base64.b64encode(b"client123:secret123").decode()

        mock_request = AsyncMock()
        mock_request.headers = {
            "content-type": "application/x-www-form-urlencoded",
            "authorization": f"Basic {credentials}",
        }
        mock_request.form = AsyncMock(return_value={"token": "token123"})
        mock_request.query_params = {}

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client.return_value = {"id": "client123"}

        with patch(
            "template_mcp_server.src.oauth.controller.OAuth2Handler.introspect_token"
        ) as mock_introspect:
            mock_introspect.return_value = {"active": True}

            result = await controller.handle_introspect(mock_request, oauth_service)

            assert result["active"] is True
            oauth_service.validate_client.assert_called_once_with(
                "client123", "secret123"
            )

    @pytest.mark.asyncio
    async def test_handle_introspect_invalid_basic_auth(self):
        """Test introspection with malformed Basic auth header."""
        mock_request = AsyncMock()
        mock_request.headers = {
            "content-type": "application/x-www-form-urlencoded",
            "authorization": "Basic !!!invalid-base64!!!",
        }
        mock_request.form = AsyncMock(return_value={"token": "token123"})
        mock_request.query_params = {}

        oauth_service = AsyncMock(spec=OAuthService)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_introspect(mock_request, oauth_service)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "invalid_client"

    @pytest.mark.asyncio
    async def test_handle_introspect_query_params_fallback(self):
        """Test introspection falls back to query params when form parsing fails."""
        mock_request = AsyncMock()
        mock_request.headers = {"content-type": ""}
        mock_request.form = AsyncMock(side_effect=Exception("form parse error"))
        mock_request.query_params = {
            "token": "token123",
            "client_id": "client123",
            "client_secret": "secret123",
        }

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client.return_value = {"id": "client123"}

        with patch(
            "template_mcp_server.src.oauth.controller.OAuth2Handler.introspect_token"
        ) as mock_introspect:
            mock_introspect.return_value = {"active": True}

            result = await controller.handle_introspect(mock_request, oauth_service)

            assert result["active"] is True

    @pytest.mark.asyncio
    async def test_handle_introspect_generic_exception(self):
        """Test that unexpected exceptions in handle_introspect return 500."""
        mock_request = AsyncMock()
        mock_request.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_request.form = AsyncMock(
            return_value={
                "token": "token123",
                "client_id": "client123",
                "client_secret": "secret123",
            }
        )
        mock_request.query_params = {}

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.validate_client.return_value = {"id": "client123"}

        with patch(
            "template_mcp_server.src.oauth.controller.OAuth2Handler.introspect_token",
            side_effect=RuntimeError("unexpected"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await controller.handle_introspect(mock_request, oauth_service)

            assert exc_info.value.status_code == 500
            assert exc_info.value.detail["error"] == "server_error"


class TestHandleClientMetadata:
    """Test handle_client_metadata function (SEP-991 CIMD endpoint)."""

    @pytest.mark.asyncio
    async def test_client_metadata_found(self):
        """Test CIMD returns metadata for a known client."""
        from template_mcp_server.src.oauth.models import ClientMetadataResponse

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.get_client_metadata = AsyncMock(
            return_value={
                "client_id": "client123",
                "client_name": "Test Client",
                "redirect_uris": ["http://localhost:3000/callback"],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "scope": "read write",
                "application_type": "native",
            }
        )

        result = await controller.handle_client_metadata("client123", oauth_service)

        assert isinstance(result, ClientMetadataResponse)
        result_dict = result.model_dump()
        assert result_dict["client_id"] == "client123"
        assert result_dict["client_name"] == "Test Client"
        assert result_dict["redirect_uris"] == ["http://localhost:3000/callback"]
        assert result_dict["application_type"] == "native"
        oauth_service.get_client_metadata.assert_called_once_with("client123")

    @pytest.mark.asyncio
    async def test_client_metadata_not_found(self):
        """Test CIMD returns 404 for unknown client."""
        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.get_client_metadata = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await controller.handle_client_metadata("unknown_client", oauth_service)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"] == "invalid_client"
        assert "Client not found" in exc_info.value.detail["error_description"]

    @pytest.mark.asyncio
    async def test_client_metadata_does_not_expose_secret(self):
        """Test that CIMD response does not include client_secret."""
        from template_mcp_server.src.oauth.models import ClientMetadataResponse

        oauth_service = AsyncMock(spec=OAuthService)
        oauth_service.get_client_metadata = AsyncMock(
            return_value={
                "client_id": "client123",
                "client_name": "Test Client",
                "redirect_uris": ["http://localhost:3000/callback"],
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "scope": "read write",
                "application_type": "web",
            }
        )

        result = await controller.handle_client_metadata("client123", oauth_service)

        result_dict = result.model_dump()
        assert "client_secret" not in result_dict
        assert "client_id_issued_at" not in result_dict


class TestExternalBrowserAuthImport:
    """Cover the conditional import on line 36."""

    def test_controller_imports_api_module_when_external_browser_auth(self):
        """Test that USE_EXTERNAL_BROWSER_AUTH=True triggers the api_module import."""
        import importlib
        from template_mcp_server.src.settings import settings as real_settings

        original = real_settings.USE_EXTERNAL_BROWSER_AUTH
        try:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = True
            importlib.reload(controller)
            assert hasattr(controller, "api_module")
        finally:
            real_settings.USE_EXTERNAL_BROWSER_AUTH = original
            importlib.reload(controller)
