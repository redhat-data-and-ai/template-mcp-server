"""OAuth 2.0 handler module.

This module provides OAuth 2.0 authentication functionality including:
- OAuth session management
- Authorization URL generation
- Token exchange and refresh
- Token introspection and validation
"""

import time
from typing import Any, Dict, Optional

import httpx
from requests_oauthlib import OAuth2Session

from template_mcp_server.src.settings import settings
from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()

SCOPE = ["email", "openid", "profile", "session:role-any"]


class OAuth2Handler:
    """OAuth2 handler class for managing OAuth authentication flows."""

    @staticmethod
    def create_oauth_session(state=None):
        """Create an OAuth2 session with the specified state."""
        return OAuth2Session(
            settings.SSO_CLIENT_ID,
            scope=SCOPE,
            redirect_uri=settings.SSO_CALLBACK_URL,
            state=state,
        )

    @staticmethod
    def get_authorization_url():
        """Get the authorization URL for OAuth flow."""
        oauth = OAuth2Handler.create_oauth_session()
        authorization_url, state = oauth.authorization_url(
            settings.SSO_AUTHORIZATION_URL
        )
        return authorization_url, state

    @staticmethod
    def get_access_token_from_authorization_code_flow(code: str, state: str):
        """Get access token from authorization code flow."""
        oauth = OAuth2Handler.create_oauth_session(state=state)
        token = oauth.fetch_token(
            settings.SSO_TOKEN_URL,
            code=code,
            client_secret=settings.SSO_CLIENT_SECRET,
            include_client_id=True,
        )
        return token

    @staticmethod
    def get_access_token_from_refresh_token(refresh_token: str):
        """Get access token using refresh token."""
        oauth = OAuth2Handler.create_oauth_session()
        token = oauth.refresh_token(
            settings.SSO_TOKEN_URL,
            refresh_token=refresh_token,
            client_id=settings.SSO_CLIENT_ID,
            client_secret=settings.SSO_CLIENT_SECRET,
        )
        return token

    @staticmethod
    def introspect_token(token: str) -> Dict[str, Any]:
        """Introspect a token using the configured SSO introspection endpoint."""
        introspection_url = settings.SSO_INTROSPECTION_URL

        try:
            response = httpx.post(
                introspection_url,
                data={
                    "token": token,
                    "client_id": settings.SSO_CLIENT_ID,
                    "client_secret": settings.SSO_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
            response.raise_for_status()

            introspection_data = response.json()
            logger.debug(f"Token introspection response: {introspection_data}")

            return introspection_data

        except httpx.HTTPError as e:
            logger.error(f"Token introspection failed: {e}")
            return {"active": False, "error": f"Introspection failed: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error during token introspection: {e}")
            return {"active": False, "error": f"Unexpected error: {e}"}

    @staticmethod
    def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify an access token using RedHat's introspection endpoint."""
        introspection_result = OAuth2Handler.introspect_token(token)

        if not introspection_result.get("active", False):
            logger.warning("Token is not active")
            return None

        # Check if token is expired
        exp = introspection_result.get("exp")
        if exp and exp < time.time():
            logger.warning("Token has expired")
            return None

        # Verify it's an access token (not refresh token)
        token_type = introspection_result.get("token_type", "").lower()
        if token_type and token_type != "bearer" and token_type != "access_token":
            logger.warning(f"Invalid token type: {token_type}")
            return None

        return introspection_result

    @staticmethod
    def verify_authorization_header(auth_header: str) -> Optional[Dict[str, Any]]:
        """Verify Authorization header with Bearer token using RedHat's introspection."""
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("Invalid authorization header format")
            return None

        token = auth_header[7:]  # Remove "Bearer " prefix
        return OAuth2Handler.verify_access_token(token)
