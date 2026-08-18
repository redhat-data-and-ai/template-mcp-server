"""Pluggable token introspection strategies for OAuth SSO providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict

import httpx

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()

INTROSPECTION_MODE_RFC7662 = "rfc7662"
INTROSPECTION_MODE_TOKENINFO = "tokeninfo"
SUPPORTED_INTROSPECTION_MODES = frozenset(
    {INTROSPECTION_MODE_RFC7662, INTROSPECTION_MODE_TOKENINFO}
)


class TokenIntrospector(ABC):
    """Validate access tokens against a configured SSO introspection endpoint."""

    @abstractmethod
    def introspect(self, token: str) -> Dict[str, Any]:
        """Return RFC 7662-like introspection payload with an ``active`` flag."""


class Rfc7662Introspector(TokenIntrospector):
    """RFC 7662 POST introspection (Keycloak, Auth0, Okta, Red Hat SSO, etc.)."""

    def __init__(
        self,
        url: str,
        client_id: str,
        client_secret: str,
        timeout: float = 10.0,
    ) -> None:
        """Initialize RFC 7662 introspection client settings."""
        self.url = url
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout

    def introspect(self, token: str) -> Dict[str, Any]:
        """POST the token to the introspection endpoint and return the JSON payload."""
        try:
            response = httpx.post(
                self.url,
                data={
                    "token": token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Token introspection response: {data}")
            return data
        except httpx.HTTPError as e:
            logger.error(f"Token introspection failed: {e}")
            return {"active": False, "error": f"Introspection failed: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error during token introspection: {e}")
            return {"active": False, "error": f"Unexpected error: {e}"}


class TokenInfoIntrospector(TokenIntrospector):
    """GET-based tokeninfo validation for providers without RFC 7662 introspection."""

    def __init__(
        self,
        url: str,
        client_id: str = "",
        timeout: float = 10.0,
    ) -> None:
        """Initialize tokeninfo introspection client settings."""
        self.url = url
        self.client_id = client_id
        self.timeout = timeout

    @staticmethod
    def normalize_response(data: Dict[str, Any], client_id: str = "") -> Dict[str, Any]:
        """Map tokeninfo-style payloads to RFC 7662-like shape."""
        if "active" in data:
            return data

        if data.get("error"):
            return {"active": False, **data}

        if "sub" in data or "email" in data:
            normalized = dict(data)
            normalized["active"] = True
            normalized.setdefault("token_type", "Bearer")
            if "exp" in normalized:
                normalized["exp"] = int(normalized["exp"])

            aud = normalized.get("aud") or normalized.get("azp")
            if aud and client_id and aud != client_id:
                return {
                    "active": False,
                    "error": "audience_mismatch",
                    "aud": aud,
                }

            return normalized

        return {"active": False, **data}

    def introspect(self, token: str) -> Dict[str, Any]:
        """Validate the token via tokeninfo and return a normalized payload."""
        try:
            response = httpx.get(
                self.url,
                params={"access_token": token},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = self.normalize_response(response.json(), self.client_id)
            logger.debug(f"Token introspection response: {data}")
            return data
        except httpx.HTTPError as e:
            logger.error(f"Token introspection failed: {e}")
            return {"active": False, "error": f"Introspection failed: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error during token introspection: {e}")
            return {"active": False, "error": f"Unexpected error: {e}"}


def create_token_introspector(
    mode: str,
    url: str,
    client_id: str,
    client_secret: str,
) -> TokenIntrospector:
    """Build the introspection strategy configured for the current SSO provider."""
    if mode == INTROSPECTION_MODE_TOKENINFO:
        return TokenInfoIntrospector(url=url, client_id=client_id)
    return Rfc7662Introspector(
        url=url,
        client_id=client_id,
        client_secret=client_secret,
    )
