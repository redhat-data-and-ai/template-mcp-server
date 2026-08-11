"""Basic tests for the Template MCP Server."""


class TestImports:
    """Test that core modules can be imported."""

    def test_package_imports(self):
        """Test that main package modules can be imported."""
        import template_mcp_server.src.mcp
        import template_mcp_server.src.settings
        import template_mcp_server.utils.pylogger

        assert all([template_mcp_server.src.mcp, template_mcp_server.src.settings])
