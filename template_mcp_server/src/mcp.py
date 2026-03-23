"""Template MCP Server implementation.

This module contains the main Template MCP Server class that provides
tools for MCP clients. It uses FastMCP to register and manage MCP capabilities.
"""

from fastmcp import FastMCP

from template_mcp_server.src.settings import settings
from template_mcp_server.src.tools.bmi_tool import calculate_bmi
from template_mcp_server.src.tools.email_tool import (
    send_email,
)

# Import tools from the tools package
from template_mcp_server.src.tools.multiply_tool import (
    multiply_numbers,
)
from template_mcp_server.src.tools.web_search_tool import search_web
from template_mcp_server.src.tools.whimsify_tool import whimsify_number
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
        """Register MCP tools for template operations (tools-first architecture).

        Registers all available tools with the FastMCP server instance.
        In tools-first architecture, the server only provides tools.
        Currently includes:
        - multiply_numbers: Basic arithmetic operations
        - calculate_bmi: BMI calculator
        - search_web: Web search using Tavily API for current information
        - send_email: Email operations
        - whimsify_number: Whimsify operation (x+x)/2
        """
        # Register all the imported tools
        self.mcp.tool()(multiply_numbers)
        self.mcp.tool()(calculate_bmi)
        self.mcp.tool()(search_web)
        self.mcp.tool()(send_email)
        self.mcp.tool()(whimsify_number)
