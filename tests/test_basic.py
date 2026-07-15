"""Basic tests for the Template MCP Server."""

from unittest.mock import patch


class TestServer:
    """Test server functionality."""

    def test_server_initialization(self):
        """Test that server can be initialized."""
        with (
            patch("template_mcp_server.src.mcp.settings") as mock_settings,
            patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers"),
            patch("template_mcp_server.src.mcp.FastMCP"),
        ):
            mock_settings.PYTHON_LOG_LEVEL = "INFO"
            from template_mcp_server.src.mcp import TemplateMCPServer

            server = TemplateMCPServer()
            assert server is not None


class TestImports:
    """Test that core modules can be imported."""

    def test_package_imports(self):
        """Test that main package modules can be imported."""
        import template_mcp_server.src.mcp
        import template_mcp_server.src.settings
        import template_mcp_server.utils.pylogger

        assert all([template_mcp_server.src.mcp, template_mcp_server.src.settings])
