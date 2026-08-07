"""Tests for the MCP server module."""

from unittest.mock import AsyncMock, Mock, patch

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


class TestSEP2549DeterministicToolOrder:
    """SEP-2549: Deterministic tools/list ordering.

    Ensures tools/list returns tools sorted by name for client caching
    and LLM prompt cache hits.
    """

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_list_tools_wrapped_after_init(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that list_tools is wrapped to sort after initialization."""
        mock_mcp = Mock()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"

        original_list_tools = mock_mcp.list_tools

        server = TemplateMCPServer()

        assert server.mcp.list_tools is not original_list_tools

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    @pytest.mark.asyncio
    async def test_list_tools_returns_sorted_by_name(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that list_tools returns tools in alphabetical order by name."""
        tool_z = Mock(name="z_tool")
        tool_z.name = "z_tool"
        tool_a = Mock(name="a_tool")
        tool_a.name = "a_tool"
        tool_m = Mock(name="m_tool")
        tool_m.name = "m_tool"

        mock_mcp = Mock()
        mock_mcp.list_tools = AsyncMock(return_value=[tool_z, tool_a, tool_m])
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"

        server = TemplateMCPServer()

        result = await server.mcp.list_tools()
        names = [t.name for t in result]
        assert names == ["a_tool", "m_tool", "z_tool"]

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    @pytest.mark.asyncio
    async def test_list_tools_already_sorted_stays_sorted(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that already-sorted tools remain sorted."""
        tool_a = Mock()
        tool_a.name = "alpha"
        tool_b = Mock()
        tool_b.name = "beta"
        tool_g = Mock()
        tool_g.name = "gamma"

        mock_mcp = Mock()
        mock_mcp.list_tools = AsyncMock(return_value=[tool_a, tool_b, tool_g])
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"

        server = TemplateMCPServer()

        result = await server.mcp.list_tools()
        names = [t.name for t in result]
        assert names == ["alpha", "beta", "gamma"]

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    @pytest.mark.asyncio
    async def test_list_tools_empty_returns_empty(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that empty tool list returns empty list."""
        mock_mcp = Mock()
        mock_mcp.list_tools = AsyncMock(return_value=[])
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"

        server = TemplateMCPServer()

        result = await server.mcp.list_tools()
        assert result == []

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    @pytest.mark.asyncio
    async def test_list_tools_single_tool_returns_unchanged(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that a single tool is returned as-is."""
        tool = Mock()
        tool.name = "only_tool"

        mock_mcp = Mock()
        mock_mcp.list_tools = AsyncMock(return_value=[tool])
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"

        server = TemplateMCPServer()

        result = await server.mcp.list_tools()
        assert len(result) == 1
        assert result[0].name == "only_tool"

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    @pytest.mark.asyncio
    async def test_list_tools_passes_kwargs_to_original(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that kwargs are forwarded to the original list_tools."""
        original_list_tools = AsyncMock(return_value=[])

        mock_mcp = Mock()
        mock_mcp.list_tools = original_list_tools
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"

        server = TemplateMCPServer()

        await server.mcp.list_tools(run_middleware=False)
        original_list_tools.assert_called_with(run_middleware=False)

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    @pytest.mark.asyncio
    async def test_list_tools_deterministic_across_calls(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that repeated calls produce identical ordering."""
        tool_c = Mock()
        tool_c.name = "calculate_bmi"
        tool_s = Mock()
        tool_s.name = "search_web"
        tool_v = Mock()
        tool_v.name = "validate_email"

        mock_mcp = Mock()
        mock_mcp.list_tools = AsyncMock(return_value=[tool_s, tool_c, tool_v])
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"

        server = TemplateMCPServer()

        result_1 = await server.mcp.list_tools()
        result_2 = await server.mcp.list_tools()

        names_1 = [t.name for t in result_1]
        names_2 = [t.name for t in result_2]
        assert names_1 == names_2
        assert names_1 == ["calculate_bmi", "search_web", "validate_email"]
