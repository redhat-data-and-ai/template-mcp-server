"""This module sets up the FastAPI application for the Template MCP server.

It initializes the FastAPI app, configures CORS middleware, and sets up
the MCP server with appropriate transport protocols.
"""

import json
import webbrowser
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
from typing import AsyncGenerator, Callable, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from template_mcp_server.src.mcp import TemplateMCPServer
from template_mcp_server.src.oauth.handler import OAuth2Handler
from template_mcp_server.src.oauth.routes import register_oauth_routes
from template_mcp_server.src.oauth.service import OAuthService
from template_mcp_server.src.settings import settings
from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger(settings.PYTHON_LOG_LEVEL)

server = TemplateMCPServer()

oauth_service_instance: Optional[OAuthService] = None

_local_development_token: Optional[str] = None

# SEP-2207: scopes_supported MUST NOT include offline_access.
# Refresh token support is advertised via grant_types_supported instead.
SCOPES_SUPPORTED = ["template-mcp-server"]

_OFFLINE_ACCESS_SCOPE = "offline_access"


def _validate_scopes_no_offline_access(scopes: list) -> None:
    """SEP-2207: Validate that offline_access is not in scopes_supported."""
    if _OFFLINE_ACCESS_SCOPE in scopes:
        raise ValueError(
            f"SEP-2207: '{_OFFLINE_ACCESS_SCOPE}' must not appear in SCOPES_SUPPORTED. "
            "Refresh token support is advertised via grant_types_supported."
        )


_validate_scopes_no_offline_access(SCOPES_SUPPORTED)

PUBLIC_PATHS = frozenset(
    {
        "/.well-known/oauth-protected-resource",
        "/.well-known/oauth-authorization-server",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/auth/authorize",
        "/auth/token",
        "/auth/revoke",
        "/auth/introspect",
        "/auth/register",
        "/auth/callback",
        "/auth/callback/oidc",
        "/health",
    }
)

mcp_app = server.mcp.http_app(path="/mcp")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Combined lifespan handler for MCP and storage initialization."""
    global oauth_service_instance

    # Initialize storage service before starting
    logger.info("Initializing storage service...")
    try:
        if settings.ENABLE_AUTH:
            from template_mcp_server.src.oauth.service import initialize_storage

            storage_service = await initialize_storage()
            logger.info("Storage service initialized successfully")

            oauth_service_instance = OAuthService(storage_service, get_host())
            logger.info("OAuth service initialized with dependency injection")
    except Exception as e:
        logger.critical(f"Failed to initialize storage service: {e}")
        raise

    # Run MCP lifespan
    async with mcp_app.lifespan(app):
        logger.info("Server is ready to accept connections")
        yield

    # Cleanup storage service
    logger.info("Shutting down storage service...")
    try:
        from template_mcp_server.src.oauth.service import cleanup_storage

        await cleanup_storage()
        oauth_service_instance = None
        logger.info("Storage service shutdown complete")
    except Exception as e:
        logger.error(f"Error during storage cleanup: {e}")


app = FastAPI(lifespan=lifespan)


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle OAuth authorization for protected endpoints."""

    async def dispatch(self, request: Request, call_next: Callable):
        """Process incoming requests and apply OAuth authorization checks."""
        if not settings.ENABLE_AUTH:
            return await call_next(request)

        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("authorization")
        if not auth_header:
            logger.warning(
                "Missing Authorization header for protected route: %s", request.url.path
            )
            return Response(
                content="Unauthorized",
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_info = OAuth2Handler.verify_authorization_header(auth_header)
        if not token_info:
            logger.warning("Invalid token for protected route: %s", request.url.path)
            return Response(
                content="Unauthorized",
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        response = await call_next(request)
        return response


class LocalDevelopmentAuthorizationMiddleware(BaseHTTPMiddleware):
    """Local development authorization middleware that auto-opens browser for OAuth."""

    async def dispatch(self, request: Request, call_next: Callable):
        """Process requests and handle local development OAuth flow."""
        if not settings.USE_EXTERNAL_BROWSER_AUTH:
            return await call_next(request)

        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        if request.method == "POST" and request.url.path in {"/mcp", "/mcp/"}:
            try:
                body_bytes = await request.body()
                body = json.loads(body_bytes)
                # Only enforce auth on tools/call — allow tools/list so agents can discover tools without a token.
                if body.get("method") == "tools/call":

                    async def receive():
                        return {"type": "http.request", "body": body_bytes}

                    request = Request(request.scope, receive)
                else:
                    return await call_next(request)
            except Exception:
                return await call_next(request)
        else:
            return await call_next(request)
        global _local_development_token

        if _local_development_token:
            request.headers.__dict__["_list"].append(
                (b"authorization", f"Bearer {_local_development_token}".encode())
            )
            return await call_next(request)

        try:
            authorization_url, state = OAuth2Handler.get_authorization_url()

            logger.info(
                f"Opening browser for local OAuth authorization: {authorization_url}"
            )

            webbrowser.open(authorization_url)

            return JSONResponse(
                status_code=401,
                content={
                    "message": "Authorization required for local development",
                    "action": "Browser opened for OAuth authorization",
                    "authorization_url": authorization_url,
                    "instructions": "Please complete the authorization in your browser, then retry this request",
                },
            )

        except Exception as e:
            logger.error(f"Failed to initiate local OAuth flow: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Failed to initiate local authorization",
                    "details": str(e),
                },
            )


if settings.USE_EXTERNAL_BROWSER_AUTH and settings.ENABLE_AUTH:
    app.add_middleware(LocalDevelopmentAuthorizationMiddleware)
else:
    app.add_middleware(AuthorizationMiddleware)


def _get_session_secret() -> str:
    """Get session secret with security validation."""
    if settings.SESSION_SECRET:
        return settings.SESSION_SECRET

    if getattr(settings, "ENVIRONMENT", "").lower() == "production":
        raise ValueError(
            "SESSION_SECRET must be explicitly set in production environment. "
            "Generate a secure random key and set the SESSION_SECRET environment variable."
        )

    import secrets

    ephemeral_key = secrets.token_urlsafe(32)
    # Only log in debug mode to reduce noise during local development
    if settings.PYTHON_LOG_LEVEL == "DEBUG":
        logger.warning(
            "Using auto-generated ephemeral session secret for development. "
            "Set SESSION_SECRET environment variable for production use."
        )
    return ephemeral_key


def _get_session_https_only() -> bool:
    """Determine whether session cookies require HTTPS."""
    if settings.SESSION_COOKIE_HTTPS_ONLY is not None:
        return settings.SESSION_COOKIE_HTTPS_ONLY
    return getattr(settings, "ENVIRONMENT", "development").lower() != "development"


app.add_middleware(
    SessionMiddleware,
    secret_key=_get_session_secret(),
    session_cookie="mcp_session",
    max_age=settings.SESSION_COOKIE_MAX_AGE,
    same_site=settings.SESSION_COOKIE_SAME_SITE,
    https_only=_get_session_https_only(),
)


def _get_version() -> str:
    """Get the package version from installed metadata."""
    try:
        return version("template-mcp-server")
    except PackageNotFoundError:
        return "0.0.0-dev"


@app.get("/health")
async def health_check():
    """Health check endpoint for the MCP server."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "template-mcp-server",
            "transport_protocol": settings.MCP_TRANSPORT_PROTOCOL,
            "version": _get_version(),
        },
    )


_ISSUER_SAFE_DEFAULT = "http://localhost:5001"

TOKEN_ENDPOINT_AUTH_METHODS = [
    "client_secret_basic",
    "client_secret_post",
    "none",
]


def get_host() -> str:
    """Determine the canonical issuer/host for OAuth discovery endpoints.

    Checks OAUTH_ISSUER first (explicit override), then derives from
    MCP_HOST_ENDPOINT origin.
    """
    explicit = getattr(settings, "OAUTH_ISSUER", None)
    if explicit:
        return explicit

    endpoint = getattr(settings, "MCP_HOST_ENDPOINT", None) or _ISSUER_SAFE_DEFAULT
    try:
        callback_uri = urlparse(endpoint)
        if (
            callback_uri.scheme in ("http", "https")
            and callback_uri.netloc
            and " " not in callback_uri.netloc
            and not callback_uri.scheme.isspace()
        ):
            return f"{callback_uri.scheme}://{callback_uri.netloc}"
        else:
            logger.warning(
                f"Invalid MCP_HOST_ENDPOINT '{endpoint}' for OAuth discovery; falling back to {_ISSUER_SAFE_DEFAULT}"
            )
            return _ISSUER_SAFE_DEFAULT
    except Exception as e:
        logger.warning(
            f"Exception parsing MCP_HOST_ENDPOINT '{endpoint}': {e}; falling back to {_ISSUER_SAFE_DEFAULT}"
        )
        return _ISSUER_SAFE_DEFAULT


@app.get("/.well-known/oauth-protected-resource", tags=["OAuth2"])
async def well_known_oauth_protected_resource():
    """Return protected resource metadata endpoint.

    Returns metadata about this resource server as per RFC 8414.
    """
    host = get_host()
    return {
        "resource": host,
        "authorization_servers": [host],
        "scopes_supported": SCOPES_SUPPORTED,
        "registration_endpoint": f"{host}/auth/register",
        "bearer_methods_supported": ["header"],
        "revocation_endpoint": f"{host}/auth/revoke",
        "introspection_endpoint": f"{host}/auth/introspect",
        "introspection_endpoint_auth_methods_supported": TOKEN_ENDPOINT_AUTH_METHODS,
    }


@app.get("/.well-known/oauth-authorization-server", tags=["OAuth2"])
async def well_known_oauth_authorization_server():
    """Return authorization server metadata endpoint.

    Returns metadata about the authorization server as per RFC 8414.
    """
    host = get_host()
    return {
        "issuer": host,
        "authorization_response_iss_parameter_supported": True,
        "authorization_endpoint": f"{host}/auth/authorize",
        "token_endpoint": f"{host}/auth/token",
        "registration_endpoint": f"{host}/auth/register",
        "scopes_supported": SCOPES_SUPPORTED,
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": [
            "authorization_code",
            "refresh_token",
            "client_credentials",
        ],
        "token_endpoint_auth_methods_supported": TOKEN_ENDPOINT_AUTH_METHODS,
        "revocation_endpoint": f"{host}/auth/revoke",
        "revocation_endpoint_auth_methods_supported": TOKEN_ENDPOINT_AUTH_METHODS,
        "introspection_endpoint": f"{host}/auth/introspect",
        "introspection_endpoint_auth_methods_supported": TOKEN_ENDPOINT_AUTH_METHODS,
        "code_challenge_methods_supported": ["S256"],
    }


# Register OAuth routes with dependency injection
def get_oauth_service_provider() -> OAuthService:
    """Get the OAuth service instance."""
    if oauth_service_instance is None:
        raise RuntimeError("OAuth service not initialized")
    return oauth_service_instance


register_oauth_routes(app, get_oauth_service_provider)

app.mount("/", mcp_app)

if settings.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )
