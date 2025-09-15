"""OAuth routes module for FastAPI endpoints.

This module registers OAuth 2.0 endpoints with the FastAPI application including:
- /oauth/authorize - Authorization endpoint
- /oauth/token - Token endpoint
- /oauth/register - Client registration endpoint
- /oauth/introspect - Token introspection endpoint
"""

from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Request

from . import controller
from .service import OAuthService

oauth_router = APIRouter(prefix="/auth", tags=["OAuth2"])

# OAuth service provider function - will be injected during registration
get_oauth_service: Optional[Callable[[], OAuthService]] = None


@oauth_router.get("/callback/oidc")
async def callback_endpoint(request: Request):
    """Handle OAuth 2.0 callback endpoint.

    Handles OAuth callback requests from Snowflake.
    Exchanges authorization code for access token.
    """
    if get_oauth_service is None:
        raise RuntimeError("OAuth service not initialized")
    oauth_service = get_oauth_service()
    return await controller.handle_callback(request, oauth_service)


@oauth_router.get("/authorize")
async def authorize_endpoint(request: Request):
    """Handle authorization endpoint requests.

    Handles authorization requests with PKCE support.
    Redirects to the client's redirect_uri with authorization code.
    """
    if get_oauth_service is None:
        raise RuntimeError("OAuth service not initialized")
    oauth_service = get_oauth_service()
    return await controller.handle_authorize(request, oauth_service)


@oauth_router.post("/token")
async def token_endpoint(request: Request) -> Dict[str, Any]:
    """Handle token endpoint requests.

    Exchanges authorization codes for access tokens.
    Supports authorization_code, refresh_token, and client_credentials grant types.
    """
    if get_oauth_service is None:
        raise RuntimeError("OAuth service not initialized")
    oauth_service = get_oauth_service()
    result = await controller.handle_token(request, oauth_service)
    return result.model_dump() if hasattr(result, "model_dump") else result


@oauth_router.post("/register")
async def register_endpoint(request: Request) -> Dict[str, Any]:
    """Handle client registration endpoint requests.

    Allows clients to register and obtain client credentials.
    """
    if get_oauth_service is None:
        raise RuntimeError("OAuth service not initialized")
    oauth_service = get_oauth_service()
    result = await controller.handle_register(request, oauth_service)
    return result.model_dump() if hasattr(result, "model_dump") else result


@oauth_router.post("/introspect")
async def introspect_endpoint(request: Request) -> Dict[str, Any]:
    """Handle token introspection endpoint requests.

    Allows clients to check the status and metadata of tokens.
    """
    if get_oauth_service is None:
        raise RuntimeError("OAuth service not initialized")
    oauth_service = get_oauth_service()
    result = await controller.handle_introspect(request, oauth_service)
    return result.model_dump() if hasattr(result, "model_dump") else result


def register_oauth_routes(app, oauth_service_provider: Callable[[], OAuthService]):
    """Register OAuth routes with the FastAPI app."""
    global get_oauth_service
    get_oauth_service = oauth_service_provider
    app.include_router(oauth_router)
