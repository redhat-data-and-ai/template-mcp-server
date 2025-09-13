"""This module sets up the FastAPI application for the Template MCP server.

It initializes the FastAPI app, configures CORS middleware, and sets up
the MCP server with appropriate transport protocols.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from template_mcp_server.src.mcp import TemplateMCPServer
from template_mcp_server.src.settings import settings
from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger(settings.PYTHON_LOG_LEVEL)

server = TemplateMCPServer()

# Choose the appropriate transport protocol based on settings
if settings.MCP_TRANSPORT_PROTOCOL == "sse":
    from fastmcp.server.http import create_sse_app

    mcp_app = create_sse_app(server.mcp, message_path="/sse/message", sse_path="/sse")
else:  # Default to standard HTTP (works for both "http" and "streamable-http")
    mcp_app = server.mcp.http_app(path="/mcp")

app = FastAPI(lifespan=mcp_app.lifespan)


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


app.mount("/", mcp_app)
