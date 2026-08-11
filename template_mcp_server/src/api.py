"""This module sets up the FastAPI application for the Template MCP server.

It initializes the FastAPI app, configures CORS middleware, and sets up
the MCP server with appropriate transport protocols.
"""

import json
import webbrowser
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
from typing import AsyncGenerator, Callable, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from template_mcp_server.src.apps import AppEntry, app_registry
from template_mcp_server.src.deprecation import deprecation_registry
from template_mcp_server.src.errors import (
    HEADER_MISMATCH,
    METHOD_NOT_SUPPORTED,
    RESOURCE_NOT_FOUND,
)
from template_mcp_server.src.extensions import (
    EXTENSION_APPS,
    EXTENSION_TASKS,
    extension_registry,
)
from template_mcp_server.src.mcp import TemplateMCPServer
from template_mcp_server.src.mrtr import (
    complete_result,
    get_response_value,
    input_required_result,
    make_input_request,
)
from template_mcp_server.src.oauth.handler import OAuth2Handler
from template_mcp_server.src.oauth.routes import register_oauth_routes
from template_mcp_server.src.oauth.service import OAuthService, get_current_issuer
from template_mcp_server.src.settings import settings
from template_mcp_server.src.tasks import task_store
from template_mcp_server.src.tracing import (
    build_traceparent,
    extract_trace_from_headers,
    extract_trace_from_meta,
    generate_span_id,
)
from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger(settings.PYTHON_LOG_LEVEL)

server = TemplateMCPServer()

oauth_service_instance: Optional[OAuthService] = None

_local_development_token: Optional[str] = None

# SEP-2207: scopes_supported MUST NOT include offline_access.
# Refresh token support is advertised via grant_types_supported instead.
_SERVER_NAME = "template-mcp-server"

SCOPES_SUPPORTED = [_SERVER_NAME]

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

PUBLIC_PATH_PREFIXES = frozenset(
    {
        "/auth/client-metadata/",
    }
)


def _is_public_path(path: str) -> bool:
    """Check whether a request path is public (no auth required)."""
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES)


def _get_version() -> str:
    """Get the package version from installed metadata."""
    try:
        return version(_SERVER_NAME)
    except PackageNotFoundError:
        return "0.0.0-dev"


_MCP_PATHS = frozenset({"/mcp", "/mcp/"})

# SEP-2575(c): Methods removed in stateless mode.
_REMOVED_METHODS = frozenset(
    {
        "ping",
        "logging/setLevel",
        "notifications/roots/list_changed",
        "tasks/list",  # SEP-2663: removed in favor of tasks/get
    }
)

# SEP-2663: Task RPCs handled by the middleware.
_TASK_METHODS = frozenset({"tasks/get", "tasks/update", "tasks/cancel"})

# SEP-1865: Apps RPCs handled by the middleware.
_APPS_METHODS = frozenset({"apps/list", "apps/get"})

# SEP-2322: MRTR-enabled tool names (require user confirmation before executing).
_MRTR_TOOLS = frozenset({"send_email"})

# SEP-2322: MRTR confirmation request ID for email tool.
_MRTR_CONFIRM_SEND_ID = "confirm-send"

# SEP-1865: Register default MCP Apps.
app_registry.register(
    AppEntry(
        app_id="health-dashboard",
        name="Health Dashboard",
        description="Server health and diagnostics",
        ui_type="iframe",
        url="/health",
    )
)

# SEP-2133: Register extensions (SEP-1865 Apps, SEP-2663 Tasks).
if settings.MCP_EXTENSIONS_ENABLED:
    extension_registry.register(EXTENSION_APPS, app_registry.get_extension_config())
    extension_registry.register(
        EXTENSION_TASKS,
        {
            "methods": ["tasks/get", "tasks/update", "tasks/cancel"],
            "activeTaskCount": task_store.count,
        },
    )


def _jsonrpc_error(request_id, code: int, message: str) -> JSONResponse:
    """Build a JSON-RPC error response."""
    return JSONResponse(
        content={
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        },
    )


def get_server_discover_result() -> dict:
    """SEP-2575(a): Build the server/discover response payload."""
    capabilities: dict = {
        "tools": {"multiRoundTrip": settings.MCP_MRTR_ENABLED},
    }

    # SEP-2133: Include registered extensions in capabilities.
    if settings.MCP_EXTENSIONS_ENABLED:
        extension_registry.register(EXTENSION_APPS, app_registry.get_extension_config())
        extension_registry.register(
            EXTENSION_TASKS,
            {
                "methods": ["tasks/get", "tasks/update", "tasks/cancel"],
                "activeTaskCount": len(task_store.active_tasks()),
            },
        )
        extensions = extension_registry.get_capabilities()
        if extensions:
            capabilities["extensions"] = extensions

    result: dict = {
        "protocolVersion": settings.MCP_PROTOCOL_VERSION,
        "serverInfo": {
            "name": _SERVER_NAME,
            "version": _get_version(),
        },
        "capabilities": capabilities,
    }

    # SEP-2596: Include deprecation metadata.
    deprecations = deprecation_registry.to_list()
    if deprecations:
        result["deprecations"] = deprecations

    return result


class McpProtocolMiddleware(BaseHTTPMiddleware):
    """MCP protocol middleware handling multiple SEPs.

    SEP-2243: Mcp-Method / Mcp-Name header validation.
    SEP-2322: MRTR — inject resultType on tools/call results.
    SEP-2414: W3C Trace Context propagation.
    SEP-2575: server/discover, removed methods, per-request logLevel.
    SEP-2663: tasks/get, tasks/update, tasks/cancel RPCs.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        """Validate MCP headers and enforce stateless protocol rules."""
        if request.method != "POST" or request.url.path not in _MCP_PATHS:
            return await call_next(request)

        try:
            body_bytes = await request.body()
            body = json.loads(body_bytes)
        except Exception:
            return await call_next(request)

        rpc_method = body.get("method")
        request_id = body.get("id")

        if not rpc_method:
            return await call_next(request)

        # SEP-2243: Validate Mcp-Method header if present.
        header_method = request.headers.get("mcp-method")
        if header_method is not None and header_method != rpc_method:
            return _jsonrpc_error(
                request_id,
                HEADER_MISMATCH,
                f"Mcp-Method header '{header_method}' does not match "
                f"JSON-RPC method '{rpc_method}'",
            )

        # SEP-2243: Validate Mcp-Name header if present (for tools/call).
        tool_name = None
        if rpc_method == "tools/call":
            params = body.get("params", {})
            tool_name = params.get("name")
            header_name = request.headers.get("mcp-name")
            if header_name is not None and tool_name and header_name != tool_name:
                return _jsonrpc_error(
                    request_id,
                    HEADER_MISMATCH,
                    f"Mcp-Name header '{header_name}' does not match "
                    f"tool name '{tool_name}'",
                )

        # SEP-2575(a): Handle server/discover.
        if rpc_method == "server/discover":
            resp_headers = {"x-mcp-method": "server/discover"}
            resp_headers.update(self._trace_response_headers(request, body))
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": get_server_discover_result(),
                },
                headers=resp_headers,
            )

        # SEP-2575(c) + SEP-2663: Reject removed methods.
        if rpc_method in _REMOVED_METHODS:
            return _jsonrpc_error(
                request_id,
                METHOD_NOT_SUPPORTED,
                f"Method '{rpc_method}' is not supported (removed in {settings.MCP_PROTOCOL_VERSION} spec)",
            )

        # SEP-2663: Handle task RPCs.
        if rpc_method in _TASK_METHODS:
            return self._handle_task_rpc(rpc_method, request_id, body)

        # SEP-1865: Handle apps RPCs.
        if rpc_method in _APPS_METHODS:
            return self._handle_apps_rpc(rpc_method, request_id, body)

        # SEP-2322: Handle MRTR-enabled tool calls.
        if (
            settings.MCP_MRTR_ENABLED
            and rpc_method == "tools/call"
            and tool_name in _MRTR_TOOLS
        ):
            arguments = params.get("arguments", {}) if isinstance(params, dict) else {}
            input_responses = (
                params.get("inputResponses", []) if isinstance(params, dict) else []
            )
            self._bind_trace_context(request, body)
            resp = await self._handle_mrtr_tool_call(
                tool_name, request_id, arguments, input_responses
            )
            resp.headers["x-mcp-method"] = rpc_method
            if tool_name:
                resp.headers["x-mcp-name"] = tool_name
            trace_headers = self._trace_response_headers(request, body)
            for k, v in trace_headers.items():
                resp.headers[k] = v
            return resp

        # SEP-2575(d): Extract per-request logLevel from _meta.
        params = body.get("params", {})
        meta = params.get("_meta", {}) if isinstance(params, dict) else {}
        if isinstance(meta, dict) and "logLevel" in meta:
            import logging

            level_name = meta["logLevel"].upper()
            level = getattr(logging, level_name, None)
            if level is not None:
                logger.setLevel(level)

        # SEP-414: Bind trace context for structlog.
        self._bind_trace_context(request, body)

        response = await call_next(request)

        # SEP-2322: Inject resultType on tools/call results.
        if rpc_method == "tools/call":
            response = await self._inject_result_type(response)

        # SEP-2243: Set x-mcp-method / x-mcp-name response headers.
        response.headers["x-mcp-method"] = rpc_method
        if tool_name:
            response.headers["x-mcp-name"] = tool_name

        # SEP-414: Set trace context response headers.
        trace_headers = self._trace_response_headers(request, body)
        for key, value in trace_headers.items():
            response.headers[key] = value

        return response

    def _handle_task_rpc(
        self, rpc_method: str, request_id: object, body: dict
    ) -> JSONResponse:
        """SEP-2663: Handle tasks/get, tasks/update, tasks/cancel."""
        params = body.get("params", {})
        task_id = params.get("taskId") if isinstance(params, dict) else None

        if not task_id:
            return _jsonrpc_error(request_id, RESOURCE_NOT_FOUND, "taskId is required")

        if rpc_method == "tasks/get":
            entry = task_store.get(task_id)
            if entry is None:
                return _jsonrpc_error(
                    request_id, RESOURCE_NOT_FOUND, f"Task '{task_id}' not found"
                )
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": entry.to_dict(),
                }
            )

        if rpc_method == "tasks/cancel":
            entry = task_store.cancel(task_id)
            if entry is None:
                return _jsonrpc_error(
                    request_id,
                    RESOURCE_NOT_FOUND,
                    f"Task '{task_id}' not found or already terminal",
                )
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": entry.to_dict(),
                }
            )

        if rpc_method == "tasks/update":
            update_fields = {}
            if "status" in params:
                update_fields["status"] = params["status"]
            if "progress" in params:
                update_fields["progress"] = params["progress"]
            if "message" in params:
                update_fields["message"] = params["message"]
            if "result" in params:
                update_fields["result"] = params["result"]
            entry = task_store.update(task_id, **update_fields)
            if entry is None:
                return _jsonrpc_error(
                    request_id,
                    RESOURCE_NOT_FOUND,
                    f"Task '{task_id}' not found or cannot be updated",
                )
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": entry.to_dict(),
                }
            )

    def _handle_apps_rpc(
        self, rpc_method: str, request_id: object, body: dict
    ) -> JSONResponse:
        """SEP-1865: Handle apps/list and apps/get."""
        if rpc_method == "apps/list":
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"apps": app_registry.list_apps()},
                }
            )

        if rpc_method == "apps/get":
            params = body.get("params", {})
            app_id = params.get("appId") if isinstance(params, dict) else None
            if not app_id:
                return _jsonrpc_error(
                    request_id, RESOURCE_NOT_FOUND, "appId is required"
                )
            entry = app_registry.get(app_id)
            if entry is None:
                return _jsonrpc_error(
                    request_id, RESOURCE_NOT_FOUND, f"App '{app_id}' not found"
                )
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": entry.to_dict(),
                }
            )

    async def _handle_mrtr_tool_call(
        self,
        tool_name: str,
        request_id: object,
        arguments: dict,
        input_responses: list,
    ) -> JSONResponse:
        """SEP-2322: Dispatch an MRTR-enabled tool call."""
        if tool_name == "send_email":
            return await self._mrtr_send_email(request_id, arguments, input_responses)

        return _jsonrpc_error(
            request_id, RESOURCE_NOT_FOUND, f"Unknown MRTR tool: {tool_name}"
        )

    async def _mrtr_send_email(
        self,
        request_id: object,
        arguments: dict,
        input_responses: list,
    ) -> JSONResponse:
        """SEP-2322: MRTR handler for send_email — confirm before sending."""
        confirmation = get_response_value(input_responses, _MRTR_CONFIRM_SEND_ID)

        if confirmation is None:
            email_id = arguments.get("email_id", "unknown")
            subject = arguments.get("subject", "unknown")
            result = input_required_result(
                [
                    make_input_request(
                        title="Confirm email send",
                        description=(
                            f"Send email to '{email_id}' with subject '{subject}'?"
                        ),
                        schema={
                            "type": "object",
                            "properties": {
                                "confirmed": {
                                    "type": "boolean",
                                    "description": "Set to true to confirm sending",
                                }
                            },
                            "required": ["confirmed"],
                        },
                        request_id=_MRTR_CONFIRM_SEND_ID,
                    )
                ],
                message=f"Please confirm sending email to '{email_id}'.",
            )
            return JSONResponse(
                content={"jsonrpc": "2.0", "id": request_id, "result": result}
            )

        if not confirmation.get("confirmed", False):
            result = complete_result(
                {"status": "cancelled", "message": "Email send cancelled by user."},
                message="Email send cancelled by user.",
            )
            return JSONResponse(
                content={"jsonrpc": "2.0", "id": request_id, "result": result}
            )

        from template_mcp_server.src.tools.email_tool import send_email

        try:
            tool_output = await send_email(**arguments)
            result = complete_result(
                {"status": "success", "message": tool_output},
                message=tool_output,
            )
        except Exception as e:
            result = complete_result(
                {"status": "error", "message": str(e)},
                message=f"Email send failed: {e}",
            )
        return JSONResponse(
            content={"jsonrpc": "2.0", "id": request_id, "result": result}
        )

    @staticmethod
    def _extract_trace_context(request: Request, body: dict) -> dict:
        """SEP-414: Extract merged trace context from HTTP headers and _meta."""
        trace_ctx = extract_trace_from_headers(request.headers)

        params = body.get("params", {})
        meta = params.get("_meta", {}) if isinstance(params, dict) else {}
        if isinstance(meta, dict):
            meta_trace = extract_trace_from_meta(meta)
            if meta_trace and "traceparent" not in trace_ctx:
                trace_ctx.update(meta_trace)

        return trace_ctx

    def _bind_trace_context(self, request: Request, body: dict) -> None:
        """SEP-414: Extract and bind trace context for structlog."""
        if not settings.MCP_TRACE_CONTEXT_ENABLED:
            return

        try:
            import structlog.contextvars

            trace_ctx = self._extract_trace_context(request, body)

            if "traceparent" in trace_ctx:
                server_span = generate_span_id()
                structlog.contextvars.bind_contextvars(
                    trace_id=trace_ctx["traceparent"]["trace_id"],
                    span_id=server_span,
                )
        except Exception:
            pass

    def _trace_response_headers(self, request: Request, body: dict) -> dict:
        """SEP-414: Build trace context response headers."""
        if not settings.MCP_TRACE_CONTEXT_ENABLED:
            return {}

        headers: dict = {}
        trace_ctx = self._extract_trace_context(request, body)

        if "traceparent" in trace_ctx:
            server_span = generate_span_id()
            tp = build_traceparent(
                trace_ctx["traceparent"]["trace_id"],
                server_span,
                trace_ctx["traceparent"]["trace_flags"],
            )
            headers["traceparent"] = tp
        if "tracestate" in trace_ctx:
            headers["tracestate"] = trace_ctx["tracestate"]

        return headers

    async def _inject_result_type(self, response: Response) -> Response:
        """SEP-2322: Inject resultType='complete' into tools/call results."""
        body = b""
        try:
            body_parts = []
            async for chunk in response.body_iterator:
                body_parts.append(chunk if isinstance(chunk, bytes) else chunk.encode())
            body = b"".join(body_parts)

            if not body:
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

            data = json.loads(body)

            if (
                isinstance(data, dict)
                and "result" in data
                and isinstance(data["result"], dict)
                and "resultType" not in data["result"]
            ):
                data["result"]["resultType"] = "complete"

            new_headers = dict(response.headers)
            new_headers.pop("content-length", None)
            return JSONResponse(
                content=data,
                status_code=response.status_code,
                headers=new_headers,
            )
        except Exception:
            new_headers = dict(response.headers)
            new_headers.pop("content-length", None)
            return Response(
                content=body,
                status_code=response.status_code,
                headers=new_headers,
                media_type=response.media_type,
            )


# SEP-2567: stateless_http removes Mcp-Session-Id tracking.
mcp_app = server.mcp.http_app(path="/mcp", stateless_http=settings.MCP_STATELESS_HTTP)


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

        if _is_public_path(request.url.path):
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

        if _is_public_path(request.url.path):
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


# SEP-2243: MCP header validation (innermost — runs after auth).
app.add_middleware(McpProtocolMiddleware)

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


@app.get("/health")
async def health_check():
    """Health check endpoint for the MCP server."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": _SERVER_NAME,
            "transport_protocol": settings.MCP_TRANSPORT_PROTOCOL,
            "version": _get_version(),
        },
    )


TOKEN_ENDPOINT_AUTH_METHODS = [
    "client_secret_basic",
    "client_secret_post",
    "none",
]


def get_host() -> str:
    """Canonical host for OAuth discovery endpoints.

    Delegates to get_current_issuer() in oauth.service to avoid
    duplicating issuer-derivation logic.
    """
    return get_current_issuer()


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
        "registration_endpoint_is_deprecated": True,
        "client_metadata_endpoint": f"{host}/auth/client-metadata/{{client_id}}",
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
        "registration_endpoint_is_deprecated": True,
        "client_metadata_endpoint": f"{host}/auth/client-metadata/{{client_id}}",
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
