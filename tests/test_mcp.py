"""Tests for the MCP server module."""

from unittest.mock import Mock, patch

import pytest

from template_mcp_server.src.mcp import TemplateMCPServer


class TestTemplateMCPServer:
    """Test the TemplateMCPServer class."""

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_init_success(self, mock_fastmcp, mock_settings, mock_force_reconfigure):
        """Test successful initialization of TemplateMCPServer."""
        mock_mcp = Mock()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"

        server = TemplateMCPServer()

        assert server.mcp == mock_mcp
        mock_mcp.tool.assert_called()

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_init_failure(self, mock_fastmcp, mock_settings, mock_force_reconfigure):
        """Test initialization failure handling."""
        mock_fastmcp.side_effect = Exception("Test error")
        mock_settings.PYTHON_LOG_LEVEL = "INFO"

        with pytest.raises(Exception, match="Test error"):
            TemplateMCPServer()
