"""Pydantic models for OAuth request and response validation."""

from typing import Any, Optional

from pydantic import BaseModel, Field

from template_mcp_server.src.settings import settings

# Pydantic uses ... (Ellipsis) as a sentinel for "required field".
# When COMPATIBLE_WITH_CURSOR is True, client_id becomes optional (default=None).
_CLIENT_ID_DEFAULT: Any = (
    None if getattr(settings, "COMPATIBLE_WITH_CURSOR", False) else ...
)


class TokenRequestBase(BaseModel):
    """Base class for all token requests."""

    grant_type: str = Field(..., description="OAuth 2.0 grant type")

    client_id: Optional[str] = Field(
        _CLIENT_ID_DEFAULT,
        description="OAuth client identifier",
    )
    client_secret: Optional[str] = Field(None, description="OAuth client secret")


class AuthorizationCodeTokenRequest(TokenRequestBase):
    """Request model for authorization_code grant type."""

    grant_type: str = Field(
        "authorization_code", description="Must be 'authorization_code'"
    )
    code: str = Field(
        ..., description="Authorization code received from authorization server"
    )
    redirect_uri: str = Field(
        ..., description="Redirect URI used in authorization request"
    )
    code_verifier: str = Field(..., description="PKCE code verifier")


class RefreshTokenRequest(TokenRequestBase):
    """Request model for refresh_token grant type."""

    grant_type: str = Field("refresh_token", description="Must be 'refresh_token'")
    refresh_token: str = Field(..., description="The refresh token")
    scope: Optional[str] = Field(None, description="Optional scope for token refresh")


class ClientCredentialsTokenRequest(TokenRequestBase):
    """Request model for client_credentials grant type."""

    grant_type: str = Field(
        "client_credentials", description="Must be 'client_credentials'"
    )
    scope: Optional[str] = Field(
        None, description="Optional scope for client credentials flow"
    )


class ClientRegistrationRequest(BaseModel):
    """Request model for OAuth client registration."""

    client_name: str = Field(..., description="Human-readable name of the client")
    redirect_uris: list[str] = Field(..., description="Array of redirect URIs")
    grant_types: Optional[list[str]] = Field(
        default=["authorization_code", "refresh_token"],
        description="Array of OAuth 2.0 grant types",
    )
    response_types: Optional[list[str]] = Field(
        default=["code"], description="Array of OAuth 2.0 response types"
    )
    scope: Optional[str] = Field(
        default="read write", description="Space-separated list of scope values"
    )


class TokenResponse(BaseModel):
    """Response model for successful token requests."""

    access_token: str = Field(..., description="The access token")
    token_type: str = Field("Bearer", description="Type of token (usually Bearer)")
    expires_in: Optional[int] = Field(
        None, description="Token expiration time in seconds"
    )
    refresh_token: Optional[str] = Field(None, description="The refresh token")
    scope: Optional[str] = Field(None, description="Scope of the access token")


class ClientRegistrationResponse(BaseModel):
    """Response model for successful client registration."""

    client_id: str = Field(..., description="The assigned client identifier")
    client_secret: str = Field(..., description="The assigned client secret")
    client_name: str = Field(..., description="Human-readable name of the client")
    redirect_uris: list[str] = Field(..., description="Array of redirect URIs")
    grant_types: list[str] = Field(..., description="Array of OAuth 2.0 grant types")
    response_types: list[str] = Field(
        ..., description="Array of OAuth 2.0 response types"
    )
    scope: str = Field(..., description="Space-separated list of scope values")
    client_id_issued_at: int = Field(..., description="Time when client ID was issued")
