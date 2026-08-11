"""Template MCP Server implementation.

This module contains the main Template MCP Server class that provides
tools for MCP clients. It uses FastMCP to register and manage MCP capabilities.
"""

from typing import Any, Dict

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from template_mcp_server.src.schema import validate_input_schema, validate_output_schema
from template_mcp_server.src.settings import settings
from template_mcp_server.src.tools.bmi_tool import (
    OUTPUT_SCHEMA as BMI_OUTPUT_SCHEMA,
)
from template_mcp_server.src.tools.bmi_tool import (
    calculate_bmi,
)
from template_mcp_server.src.tools.email_tool import (
    OUTPUT_SCHEMA as EMAIL_OUTPUT_SCHEMA,
)
from template_mcp_server.src.tools.email_tool import (
    send_email,
)
from template_mcp_server.src.tools.validate_email_tool import (
    OUTPUT_SCHEMA as VALIDATE_EMAIL_OUTPUT_SCHEMA,
)
from template_mcp_server.src.tools.validate_email_tool import (
    validate_email,
)
from template_mcp_server.src.tools.web_search_tool import (
    OUTPUT_SCHEMA as WEB_SEARCH_OUTPUT_SCHEMA,
)
from template_mcp_server.src.tools.web_search_tool import (
    search_web,
)
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
            self._validate_tool_schemas()
            self._ensure_deterministic_tool_order()

            logger.info("Template MCP Server initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Template MCP Server: {e}")
            raise

    def _get_cache_meta(self) -> Dict[str, Any]:
        """Build tool-level cache metadata from settings (SEP-2549)."""
        return {
            "ttlMs": settings.TOOL_CACHE_TTL_MS,
            "cacheScope": settings.TOOL_CACHE_SCOPE,
        }

    def _register_mcp_tools(self) -> None:
        """Register MCP tools for template operations (tools-first architecture).

        Registers all available tools with the FastMCP server instance.
        Each tool includes an outputSchema (SEP-2106), cache metadata (SEP-2549),
        and ToolAnnotations with behavioral hints for clients.
        """
        cache_meta = self._get_cache_meta()

        self.mcp.tool(
            output_schema=BMI_OUTPUT_SCHEMA,
            meta=cache_meta,
            annotations=ToolAnnotations(
                title="BMI Calculator",
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=False,
            ),
        )(calculate_bmi)
        self.mcp.tool(
            output_schema=WEB_SEARCH_OUTPUT_SCHEMA,
            meta=cache_meta,
            annotations=ToolAnnotations(
                title="Web Search",
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=True,
            ),
        )(search_web)
        self.mcp.tool(
            output_schema=EMAIL_OUTPUT_SCHEMA,
            meta=cache_meta,
            annotations=ToolAnnotations(
                title="Send Email",
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=False,
                openWorldHint=True,
            ),
        )(send_email)
        self.mcp.tool(
            output_schema=VALIDATE_EMAIL_OUTPUT_SCHEMA,
            meta=cache_meta,
            annotations=ToolAnnotations(
                title="Validate Email",
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=False,
            ),
        )(validate_email)

    def _validate_tool_schemas(self) -> None:
        """SEP-2106: Validate all registered tool schemas against JSON Schema 2020-12.

        Checks that every tool's inputSchema has type: "object" at root
        and that outputSchemas (if present) are well-formed.
        """
        components = self.mcp.local_provider._components
        for key, tool in components.items():
            if not key.startswith("tool:"):
                continue

            input_errors = validate_input_schema(tool.parameters)
            if input_errors:
                raise ValueError(
                    f"Tool {tool.name!r} inputSchema validation failed: "
                    + "; ".join(input_errors)
                )

            output_errors = validate_output_schema(tool.output_schema)
            if output_errors:
                raise ValueError(
                    f"Tool {tool.name!r} outputSchema validation failed: "
                    + "; ".join(output_errors)
                )

    def _ensure_deterministic_tool_order(self) -> None:
        """SEP-2549: Wrap list_tools to return tools sorted by name.

        Deterministic ordering enables client caching and LLM prompt cache hits.
        """
        original_list_tools = self.mcp.list_tools

        async def sorted_list_tools(**kwargs):
            tools = await original_list_tools(**kwargs)
            return sorted(tools, key=lambda t: t.name)

        self.mcp.list_tools = sorted_list_tools
