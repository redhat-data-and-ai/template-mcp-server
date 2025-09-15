"""This module sets up the FastAPI application for the Template MCP server.

It initializes the FastAPI app, configures CORS middleware, and sets up
the MCP server with appropriate transport protocols.
"""

import webbrowser
from contextlib import asynccontextmanager
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

# Choose the appropriate transport protocol based on settings
if settings.MCP_TRANSPORT_PROTOCOL == "sse":
    from fastmcp.server.http import create_sse_app

    mcp_app = create_sse_app(server.mcp, message_path="/sse/message", sse_path="/sse")
else:  # Default to standard HTTP (works for both "http" and "streamable-http")
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

            oauth_service_instance = OAuthService(storage_service)
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

        public_paths = {
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
            "/auth/callback/snowflake",
            "/auth/callback/oidc",
            "/health",
        }

        if request.url.path in public_paths:
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

        public_paths = {
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
            "/auth/callback/snowflake",
            "/auth/callback/oidc",
            "/health",
        }

        if request.url.path in public_paths:
            return await call_next(request)
        if request.method == "POST" and request.url.path in {"/mcp", "/mcp/"}:
            try:
                body_bytes = await request.body()
                import json

                body = json.loads(body_bytes)
                #! I think this is needed only for tool calls so goose or other agents can list tools with requiring auth.
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
            from template_mcp_server.src.oauth.handler import OAuth2Handler

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
    logger.warning(
        "Using auto-generated ephemeral session secret for development. "
        "Set SESSION_SECRET environment variable for production use."
    )
    return ephemeral_key


app.add_middleware(
    SessionMiddleware,
    secret_key=_get_session_secret(),
    session_cookie="mcp_session",
    max_age=60 * 60 * 24,  # 1 day
    same_site="lax",
    https_only=False,
)


@app.get("/health")
async def health_check():
    """Health check endpoint for the MCP server."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "template-mcp-server",
            "transport_protocol": settings.MCP_TRANSPORT_PROTOCOL,
            "version": "0.1.0",
        },
    )


def get_host() -> str:
    """Determine the HOST for OAuth discovery endpoints."""
    safe_default = "http://localhost:8080"
    endpoint = getattr(settings, "MCP_HOST_ENDPOINT", None) or safe_default
    try:
        callback_uri = urlparse(endpoint)
        # Validate that scheme and netloc are present and scheme is http or https
        if (
            callback_uri.scheme in ("http", "https")
            and callback_uri.netloc
            and " " not in callback_uri.netloc
            and not callback_uri.scheme.isspace()
        ):
            return f"{callback_uri.scheme}://{callback_uri.netloc}"
        else:
            # Malformed URL: fallback to safe default
            logger.warning(
                f"Invalid MCP_HOST_ENDPOINT '{endpoint}' for OAuth discovery; falling back to {safe_default}"
            )
            return safe_default
    except Exception as e:
        logger.warning(
            f"Exception parsing MCP_HOST_ENDPOINT '{endpoint}': {e}; falling back to {safe_default}"
        )
        return safe_default


@app.get("/.well-known/oauth-protected-resource", tags=["OAuth2"])
async def well_known_oauth_protected_resource():
    """Return protected resource metadata endpoint.

    Returns metadata about this resource server as per RFC 8414.
    """
    host = get_host()
    return {
        "resource": host,
        "authorization_servers": [host],
        "scopes_supported": ["snowflake-mcp-server"],
        "registration_endpoint": f"{host}/auth/register",
        "bearer_methods_supported": ["header"],
        "revocation_endpoint": f"{host}/auth/revoke",
        "introspection_endpoint": f"{host}/auth/introspect",
        "introspection_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
            "none",
        ],
    }


@app.get("/.well-known/oauth-authorization-server", tags=["OAuth2"])
async def well_known_oauth_authorization_server():
    """Return authorization server metadata endpoint.

    Returns metadata about the authorization server as per RFC 8414.
    """
    host = get_host()
    return {
        "issuer": host,
        "authorization_endpoint": f"{host}/auth/authorize",
        "token_endpoint": f"{host}/auth/token",
        "registration_endpoint": f"{host}/auth/register",
        "scopes_supported": ["dataverse-console"],
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": [
            "authorization_code",
            "refresh_token",
            "client_credentials",
        ],
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
            "none",
        ],
        "revocation_endpoint": f"{host}/auth/revoke",
        "revocation_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
            "none",
        ],
        "introspection_endpoint": f"{host}/auth/introspect",
        "introspection_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
            "none",
        ],
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
