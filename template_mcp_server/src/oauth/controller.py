"""OAuth controller module containing FastAPI route handlers.

This module provides HTTP endpoints for OAuth 2.0 operations including:
- Authorization endpoint
- Token endpoint
- Client registration
- Token introspection
"""

import base64
import secrets
import time
from typing import Any, Dict
from urllib.parse import urlencode, urlparse

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import ValidationError

from template_mcp_server.src.settings import settings
from template_mcp_server.utils.pylogger import get_python_logger

from .handler import OAuth2Handler
from .models import (
    AuthorizationCodeTokenRequest,
    ClientCredentialsTokenRequest,
    ClientMetadataResponse,
    ClientRegistrationRequest,
    ClientRegistrationResponse,
    RefreshTokenRequest,
    TokenRequestBase,
)
from .service import OAuthService, get_current_issuer, verify_code_challenge

logger = get_python_logger(settings.PYTHON_LOG_LEVEL)

if settings.USE_EXTERNAL_BROWSER_AUTH:
    import template_mcp_server.src.api as api_module


async def _validate_client_credentials(
    token_request: TokenRequestBase, oauth_service: OAuthService
) -> None:
    """Validate client credentials when COMPATIBLE_WITH_CURSOR is disabled."""
    if settings.COMPATIBLE_WITH_CURSOR:
        return
    if token_request.client_id is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_client",
                "error_description": "Client ID is required",
            },
        )
    client = await oauth_service.validate_client(
        token_request.client_id, token_request.client_secret
    )
    if not client:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_client",
                "error_description": "Invalid client credentials",
            },
        )


async def handle_callback(request: Request, oauth_service: OAuthService) -> Response:
    """Handle OAuth callback endpoint."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code or not state:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_request",
                "error_description": "Missing code or state parameter",
            },
        )

    token_set_from_code = OAuth2Handler.get_access_token_from_authorization_code_flow(
        code, state
    )

    logger.debug("Access token obtained successfully")

    if settings.USE_EXTERNAL_BROWSER_AUTH:
        access_token = token_set_from_code.get("access_token")
        if access_token:
            api_module._local_development_token = access_token
            logger.info("Local development token stored successfully")

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Authorization successful!",
                    "status": "Token stored for local development",
                    "instructions": "You can now close this browser tab and retry your API request",
                },
            )

    user_details = request.session.get("user_details")
    if not user_details:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_request",
                "error_description": "Missing session data",
            },
        )
    code_from_session = user_details.get("auth_code")
    state_from_session = user_details.get("state")
    redirect_uri_from_session = user_details.get("redirect_uri")

    await oauth_service.add_token_to_code(code_from_session, token_set_from_code)

    redirect_url = urlparse(redirect_uri_from_session)
    query_dict = {
        "code": code_from_session,
        "state": state_from_session,
        "iss": get_current_issuer(),
    }
    redirect_url_str = f"{redirect_url.scheme}://{redirect_url.netloc}{redirect_url.path}?{urlencode(query_dict)}"
    return RedirectResponse(url=redirect_url_str, status_code=302)


async def handle_authorize(request: Request, oauth_service: OAuthService) -> Response:
    """Handle OAuth authorization endpoint."""
    try:
        query_params = dict(request.query_params)
        response_type = query_params.get("response_type")
        client_id = query_params.get("client_id")
        redirect_uri = query_params.get("redirect_uri")
        scope = query_params.get("scope")
        code_challenge = query_params.get("code_challenge")
        state = query_params.get("state")
        code_challenge_method = query_params.get("code_challenge_method")

        if not code_challenge or code_challenge_method != "S256":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_request",
                    "error_description": "PKCE is required with S256 method",
                },
            )

        if not response_type or not client_id or not redirect_uri:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_request",
                    "error_description": "Missing required parameters",
                },
            )

        if response_type != "code":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "unsupported_response_type",
                    "error_description": "Only authorization code flow is supported",
                },
            )

        client = await oauth_service.validate_client(client_id)
        if not client:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_client",
                    "error_description": "Invalid client_id",
                },
            )

        if redirect_uri not in client["redirect_uris"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_request",
                    "error_description": "Invalid redirect_uri",
                },
            )

        # Generate authorization code
        auth_code = await oauth_service.create_authorization_code(
            client_id,
            redirect_uri,
            scope,
            code_challenge,
            code_challenge_method,
            state or "",
        )

        request.session["user_details"] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "auth_code": auth_code,
            "state": state,
        }

        authorization_url, state = OAuth2Handler.get_authorization_url()

        return RedirectResponse(url=authorization_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth authorize error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "server_error",
                "error_description": "Internal server error",
            },
        )


async def parse_token_request(request: Request) -> Dict[str, Any]:
    """Parse token request data from form or JSON."""
    content_type = request.headers.get("content-type", "")

    try:
        if content_type and content_type.startswith("application/json"):
            return await request.json()
        else:
            # Handle form data
            form_data = await request.form()
            return dict(form_data)
    except Exception as e:
        logger.error(f"Request parsing error: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_request",
                "error_description": "Invalid request format",
            },
        )


async def handle_token(request: Request, oauth_service: OAuthService) -> Dict[str, Any]:
    """Handle OAuth token endpoint with Pydantic validation."""
    try:
        # Parse request data
        request_data = await parse_token_request(request)
        grant_type = request_data.get("grant_type")

        if not grant_type:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_request",
                    "error_description": "Missing grant_type",
                },
            )

        # Route to appropriate handler based on grant type
        if grant_type == "authorization_code":
            try:
                auth_code_request = AuthorizationCodeTokenRequest(**request_data)
                logger.info(f"Token request: {auth_code_request}")
                return await handle_authorization_code_grant(
                    auth_code_request, oauth_service
                )
            except ValidationError as e:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_request",
                        "error_description": f"Invalid authorization_code request: {str(e)}",
                    },
                )
        elif grant_type == "refresh_token":
            try:
                refresh_request = RefreshTokenRequest(**request_data)
                return await handle_refresh_token_grant_pydantic(
                    refresh_request, oauth_service
                )
            except ValidationError as e:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_request",
                        "error_description": f"Invalid refresh_token request: {str(e)}",
                    },
                )
        elif grant_type == "client_credentials":
            try:
                credentials_request = ClientCredentialsTokenRequest(**request_data)
                return await handle_client_credentials_grant_pydantic(
                    credentials_request, oauth_service
                )
            except ValidationError as e:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_request",
                        "error_description": f"Invalid client_credentials request: {str(e)}",
                    },
                )
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "unsupported_grant_type",
                    "error_description": f"Grant type '{grant_type}' not supported",
                },
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Token handling error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "server_error",
                "error_description": "Internal server error",
            },
        )


async def handle_authorization_code_grant(
    token_request: AuthorizationCodeTokenRequest, oauth_service: OAuthService
) -> Dict[str, Any]:
    """Handle authorization code grant with Pydantic validation."""
    # Validate the authorization code
    code_data = await oauth_service.validate_authorization_code(token_request.code)

    if not code_data:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_grant",
                "error_description": "Invalid or expired authorization code",
            },
        )

    # SEP-2352: Verify the auth code was issued by this AS
    if code_data.get("issuer") != oauth_service.issuer:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_grant",
                "error_description": "Authorization code was issued by a different authorization server",
            },
        )

    await _validate_client_credentials(token_request, oauth_service)

    # Verify redirect URI matches
    if token_request.redirect_uri != code_data["redirect_uri"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_grant",
                "error_description": "Redirect URI mismatch",
            },
        )

    if not settings.COMPATIBLE_WITH_CURSOR:
        # Verify PKCE
        if not verify_code_challenge(
            token_request.code_verifier, code_data["code_challenge"]
        ):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_grant",
                    "error_description": "Invalid code verifier",
                },
            )

    # Mark the code as used
    await oauth_service.mark_code_as_used(token_request.code)

    scope = code_data.get("scope", "read")
    expires_in = settings.ACCESS_TOKEN_EXPIRY

    # Use upstream SSO tokens if available, otherwise generate a local token
    snowflake_tokens = code_data.get("snowflake_token", {})
    if snowflake_tokens and snowflake_tokens.get("access_token"):
        access_token = snowflake_tokens["access_token"]
    else:
        access_token = secrets.token_urlsafe(32)

    await oauth_service.store_access_token(
        access_token,
        {
            "client_id": code_data["client_id"],
            "scope": scope,
            "expires_at": time.time() + expires_in,
        },
    )

    oauth_response = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": scope,
    }

    if snowflake_tokens and "refresh_token" in snowflake_tokens:
        oauth_response["refresh_token"] = snowflake_tokens["refresh_token"]

    return oauth_response


async def handle_refresh_token_grant_pydantic(
    token_request: RefreshTokenRequest, oauth_service: OAuthService
) -> Dict[str, Any]:
    """Handle refresh token grant with Pydantic validation."""
    # Validate refresh token
    refresh_data = await oauth_service.validate_refresh_token(
        token_request.refresh_token
    )
    if not refresh_data:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_grant",
                "error_description": "Invalid or expired refresh token",
            },
        )

    # SEP-2352: Verify the refresh token was issued by this AS
    if refresh_data.get("issuer") and refresh_data["issuer"] != oauth_service.issuer:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_grant",
                "error_description": "Refresh token was issued by a different authorization server",
            },
        )

    await _validate_client_credentials(token_request, oauth_service)

    scope = token_request.scope or refresh_data.get("scope", "read")
    expires_in = settings.ACCESS_TOKEN_EXPIRY

    # Use upstream SSO refresh token if available
    snowflake_refresh_token = refresh_data.get("snowflake_refresh_token")
    if snowflake_refresh_token:
        try:
            snowflake_token_response = (
                OAuth2Handler.get_access_token_from_refresh_token(
                    snowflake_refresh_token
                )
            )
            oauth_response = {
                "access_token": snowflake_token_response.get("access_token"),
                "token_type": "Bearer",
                "expires_in": snowflake_token_response.get("expires_in", expires_in),
                "scope": scope,
            }
            if "refresh_token" in snowflake_token_response:
                oauth_response["refresh_token"] = snowflake_token_response.get(
                    "refresh_token"
                )
            return oauth_response
        except Exception as e:
            logger.error(f"Failed to refresh upstream token: {e}")

    # Generate a local token when no upstream SSO is available
    access_token = secrets.token_urlsafe(32)
    await oauth_service.store_access_token(
        access_token,
        {
            "client_id": refresh_data.get("client_id", ""),
            "scope": scope,
            "expires_at": time.time() + expires_in,
        },
    )

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": scope,
    }


async def handle_client_credentials_grant_pydantic(
    token_request: ClientCredentialsTokenRequest, oauth_service: OAuthService
) -> Dict[str, Any]:
    """Handle client credentials grant with Pydantic validation."""
    await _validate_client_credentials(token_request, oauth_service)

    # Generate access token for client credentials flow
    scope = token_request.scope or "client"
    expires_in = settings.ACCESS_TOKEN_EXPIRY
    access_token = secrets.token_urlsafe(32)

    await oauth_service.store_access_token(
        access_token,
        {
            "client_id": token_request.client_id or "",
            "scope": scope,
            "expires_at": time.time() + expires_in,
        },
    )

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": scope,
    }


async def handle_register(
    request: Request, oauth_service: OAuthService
) -> ClientRegistrationResponse:
    """Handle OAuth client registration with Pydantic validation."""
    try:
        # Parse and validate request
        body = await request.json()
        registration_request = ClientRegistrationRequest(**body)

        # Register client using OAuth service
        client_response = await oauth_service.register_client(
            registration_request.client_name,
            registration_request.redirect_uris,
            registration_request.grant_types,
            registration_request.response_types,
            registration_request.scope,
            registration_request.application_type,
        )

        return ClientRegistrationResponse(**client_response)

    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_request",
                "error_description": f"Invalid registration request: {str(e)}",
            },
        )
    except Exception as e:
        logger.error(f"Client registration error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "server_error",
                "error_description": "Internal server error",
            },
        )


async def handle_client_metadata(
    client_id: str, oauth_service: OAuthService
) -> ClientMetadataResponse:
    """Handle CIMD (Client ID Metadata Document) endpoint per SEP-991."""
    metadata = await oauth_service.get_client_metadata(client_id)
    if not metadata:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "invalid_client",
                "error_description": "Client not found",
            },
        )
    return ClientMetadataResponse(**metadata)


async def handle_introspect(
    request: Request, oauth_service: OAuthService
) -> Dict[str, Any]:
    """Handle OAuth token introspection."""
    try:
        # Handle different content types
        content_type = request.headers.get("content-type", "")

        if content_type and content_type.startswith("application/json"):
            form_dict = await request.json()
        else:
            try:
                form_data = await request.form()
                form_dict = dict(form_data)
            except Exception:
                # Fallback to query params
                form_dict = dict(request.query_params)

        token = form_dict.get("token")

        if not token:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_request",
                    "error_description": "Missing token parameter",
                },
            )

        # Validate client authentication
        auth_header = request.headers.get("authorization")
        client_id = None
        client_secret = None

        if auth_header and auth_header.startswith("Basic "):
            try:
                credentials = base64.b64decode(auth_header[6:]).decode("utf-8")
                client_id, client_secret = credentials.split(":", 1)
            except (ValueError, UnicodeDecodeError):
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "invalid_client",
                        "error_description": "Invalid client credentials",
                    },
                )
        else:
            client_id = form_dict.get("client_id")
            client_secret = form_dict.get("client_secret")

        client = await oauth_service.validate_client(client_id, client_secret)
        if not client:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_client",
                    "error_description": "Invalid client credentials",
                },
            )

        introspection_result = OAuth2Handler.introspect_token(token)
        return introspection_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth introspect error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "server_error",
                "error_description": "Internal server error",
            },
        )
