"""Pydantic models for OAuth request and response validation."""

from typing import Optional, Union

from pydantic import BaseModel, Field

from template_mcp_server.src.settings import settings


class TokenRequestBase(BaseModel):
    """Base class for all token requests."""

    grant_type: str = Field(..., description="OAuth 2.0 grant type")

    client_id: Optional[str] = Field(
        None if getattr(settings, "COMPATIBLE_WITH_CURSOR", False) else ...,
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


class TokenIntrospectionRequest(BaseModel):
    """Request model for token introspection."""

    token: str = Field(..., description="The token to introspect")
    token_type_hint: Optional[str] = Field(
        None, description="Hint about the type of token"
    )
    client_id: str = Field(..., description="OAuth client identifier")
    client_secret: str = Field(..., description="OAuth client secret")


class TokenResponse(BaseModel):
    """Response model for successful token requests."""

    access_token: str = Field(..., description="The access token")
    token_type: str = Field("Bearer", description="Type of token (usually Bearer)")
    expires_in: Optional[int] = Field(
        None, description="Token expiration time in seconds"
    )
    refresh_token: Optional[str] = Field(None, description="The refresh token")
    scope: Optional[str] = Field(None, description="Scope of the access token")


class TokenIntrospectionResponse(BaseModel):
    """Response model for token introspection."""

    active: bool = Field(..., description="Whether the token is active")
    scope: Optional[str] = Field(None, description="Scope of the token")
    client_id: Optional[str] = Field(None, description="Client identifier")
    username: Optional[str] = Field(None, description="Username associated with token")
    token_type: Optional[str] = Field(None, description="Type of token")
    exp: Optional[int] = Field(None, description="Expiration timestamp")
    iat: Optional[int] = Field(None, description="Issued at timestamp")
    nbf: Optional[int] = Field(None, description="Not valid before timestamp")
    sub: Optional[str] = Field(None, description="Subject of the token")
    aud: Optional[Union[str, list[str]]] = Field(
        None, description="Audience of the token"
    )
    iss: Optional[str] = Field(None, description="Issuer of the token")
    jti: Optional[str] = Field(None, description="JWT identifier")


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


class ErrorResponse(BaseModel):
    """Standard OAuth error response."""

    error: str = Field(..., description="Error code")
    error_description: Optional[str] = Field(
        None, description="Human-readable error description"
    )
    error_uri: Optional[str] = Field(
        None, description="URI for more information about the error"
    )


# Union type for all possible token requests
TokenRequest = Union[
    AuthorizationCodeTokenRequest, RefreshTokenRequest, ClientCredentialsTokenRequest
]
