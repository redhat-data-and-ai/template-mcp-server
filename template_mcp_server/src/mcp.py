"""Template MCP Server implementation.

This module contains the main Template MCP Server class that provides
tools for MCP clients. It uses FastMCP to register and manage MCP capabilities.
"""

from fastmcp import FastMCP

from template_mcp_server.src.settings import settings
from template_mcp_server.src.tools_loader import load_tool_registry
from template_mcp_server.utils.pylogger import (
    force_reconfigure_all_loggers,
    get_python_logger,
)

logger = get_python_logger()


class TemplateMCPServer:
    """Main Template MCP Server implementation following tools-first architecture.

    This server provides only tools, not resources or prompts, adhering to
    the tools-first architectural pattern for MCP servers.
    """

    def __init__(self):
        """Initialize the MCP server with template tools following tools-first architecture."""
        try:
            # Initialize FastMCP server
            self.mcp = FastMCP("template")

            # Force reconfigure all loggers after FastMCP initialization to ensure structured logging
            force_reconfigure_all_loggers(settings.PYTHON_LOG_LEVEL)

            self._register_mcp_tools()

            logger.info("Template MCP Server initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Template MCP Server: {e}")
            raise

    def _register_mcp_tools(self) -> None:
        """Register MCP tools from config/tools YAML definitions.

        Tools are loaded from YAML config (see template_mcp_server/config/tools/)
        and wired to Python handlers via explicit handler: module:attr references.
        """
        registry = load_tool_registry()
        for tool_fn in registry.values():
            self.mcp.tool()(tool_fn)
