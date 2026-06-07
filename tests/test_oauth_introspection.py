import time
from unittest.mock import Mock, patch

import httpx

from template_mcp_server.src.oauth.introspection import (
    Rfc7662Introspector,
    TokenInfoIntrospector,
    create_token_introspector,
)


class TestRfc7662Introspector:
    @patch("template_mcp_server.src.oauth.introspection.httpx.post")
    def test_introspect_success(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"active": True, "sub": "user123"}
        mock_post.return_value = mock_response

        introspector = Rfc7662Introspector(
            url="https://sso.example.com/introspect",
            client_id="client123",
            client_secret="secret123",
        )
        result = introspector.introspect("token123")

        mock_post.assert_called_once_with(
            "https://sso.example.com/introspect",
            data={
                "token": "token123",
                "client_id": "client123",
                "client_secret": "secret123",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        assert result == {"active": True, "sub": "user123"}

    @patch("template_mcp_server.src.oauth.introspection.httpx.post")
    def test_introspect_http_error(self, mock_post):
        mock_post.side_effect = httpx.HTTPError("Connection failed")

        introspector = Rfc7662Introspector(
            url="https://sso.example.com/introspect",
            client_id="client123",
            client_secret="secret123",
        )
        result = introspector.introspect("token123")

        assert result["active"] is False
        assert "Introspection failed" in result["error"]


class TestTokenInfoIntrospector:
    @patch("template_mcp_server.src.oauth.introspection.httpx.get")
    def test_introspect_success(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "sub": "123",
            "email": "user@example.com",
            "aud": "my-client-id",
            "exp": str(int(time.time()) + 3600),
        }
        mock_get.return_value = mock_response

        introspector = TokenInfoIntrospector(
            url="https://oauth2.googleapis.com/tokeninfo",
            client_id="my-client-id",
        )
        result = introspector.introspect("ya29.test")

        mock_get.assert_called_once_with(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"access_token": "ya29.test"},
            timeout=10.0,
        )
        assert result["active"] is True
        assert result["sub"] == "123"
        assert isinstance(result["exp"], int)

    @patch("template_mcp_server.src.oauth.introspection.httpx.get")
    def test_introspect_audience_mismatch(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "sub": "123",
            "email": "user@example.com",
            "aud": "other-client-id",
            "exp": str(int(time.time()) + 3600),
        }
        mock_get.return_value = mock_response

        introspector = TokenInfoIntrospector(
            url="https://oauth2.googleapis.com/tokeninfo",
            client_id="expected-client-id",
        )
        result = introspector.introspect("ya29.test")

        assert result["active"] is False
        assert result["error"] == "audience_mismatch"

    @patch("template_mcp_server.src.oauth.introspection.httpx.get")
    def test_introspect_http_error(self, mock_get):
        mock_get.side_effect = httpx.HTTPError("400 Bad Request")

        introspector = TokenInfoIntrospector(
            url="https://oauth2.googleapis.com/tokeninfo",
        )
        result = introspector.introspect("bad-token")

        assert result["active"] is False
        assert "Introspection failed" in result["error"]


class TestCreateTokenIntrospector:
    def test_create_rfc7662_introspector(self):
        introspector = create_token_introspector(
            "rfc7662",
            "https://sso.example.com/introspect",
            "client-id",
            "client-secret",
        )
        assert isinstance(introspector, Rfc7662Introspector)

    def test_create_tokeninfo_introspector(self):
        introspector = create_token_introspector(
            "tokeninfo",
            "https://oauth2.googleapis.com/tokeninfo",
            "client-id",
            "client-secret",
        )
        assert isinstance(introspector, TokenInfoIntrospector)
