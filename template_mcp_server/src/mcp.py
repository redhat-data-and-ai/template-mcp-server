"""Template MCP Server implementation.

This module contains the main Template MCP Server class that provides
tools for MCP clients. It uses FastMCP to
register and manage MCP capabilities.
"""

from fastmcp import FastMCP

# Import tools from the tools package
from template_mcp_server.src.tools.multiply_tool import (
    multiply_numbers,
)
from template_mcp_server.src.tools.code_review_prompt_tool import (
    get_code_review_prompt,
)
from template_mcp_server.src.tools.redhat_logo import (
    read_redhat_logo_content,
)
from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


class TemplateMCPServer:
    """Main Template MCP Server implementation."""

    def __init__(self):
        """Initialize the MCP server with template tools."""
        try:
            # Initialize FastMCP server
            self.mcp = FastMCP("template")

            # Register MCP tools
            self._register_mcp_tools()

            logger.info("Template MCP Server initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Template MCP Server: {e}")
            raise

    def _register_mcp_tools(self) -> None:
        """Register MCP tools for template operations.

        Registers all available tools with the FastMCP server instance.
        """
        # Register all the imported tools
        self.mcp.tool()(multiply_numbers)
        self.mcp.tool()(read_redhat_logo_content)
        self.mcp.tool()(get_code_review_prompt)