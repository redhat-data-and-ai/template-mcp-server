"""Tests for the MCP server module."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from mcp.types import ToolAnnotations

from template_mcp_server.src.mcp import TemplateMCPServer


def _make_mock_mcp():
    """Create a Mock FastMCP with the internal structure TemplateMCPServer expects."""
    mock_mcp = Mock()
    mock_mcp.local_provider._components = {}
    return mock_mcp


class TestTemplateMCPServer:
    """Test the TemplateMCPServer class."""

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_init_success(self, mock_fastmcp, mock_settings, mock_force_reconfigure):
        """Test successful initialization of TemplateMCPServer."""
        mock_mcp = _make_mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

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
        mock_mcp = _make_mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

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

        mock_mcp = _make_mock_mcp()
        mock_mcp.list_tools = AsyncMock(return_value=[tool_z, tool_a, tool_m])
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

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

        mock_mcp = _make_mock_mcp()
        mock_mcp.list_tools = AsyncMock(return_value=[tool_a, tool_b, tool_g])
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

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
        mock_mcp = _make_mock_mcp()
        mock_mcp.list_tools = AsyncMock(return_value=[])
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

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

        mock_mcp = _make_mock_mcp()
        mock_mcp.list_tools = AsyncMock(return_value=[tool])
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

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

        mock_mcp = _make_mock_mcp()
        mock_mcp.list_tools = original_list_tools
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

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

        mock_mcp = _make_mock_mcp()
        mock_mcp.list_tools = AsyncMock(return_value=[tool_s, tool_c, tool_v])
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        server = TemplateMCPServer()

        result_1 = await server.mcp.list_tools()
        result_2 = await server.mcp.list_tools()

        names_1 = [t.name for t in result_1]
        names_2 = [t.name for t in result_2]
        assert names_1 == names_2
        assert names_1 == ["calculate_bmi", "search_web", "validate_email"]


class TestSEP2106SchemaValidation:
    """SEP-2106: JSON Schema 2020-12 support.

    Validates that tool schemas are checked during initialization.
    """

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_validate_tool_schemas_called_on_init(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that _validate_tool_schemas runs during initialization."""
        mock_mcp = _make_mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        server = TemplateMCPServer()

        assert server.mcp == mock_mcp

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_rejects_input_schema_without_object_root(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that a tool with non-object inputSchema root is rejected."""
        bad_tool = Mock()
        bad_tool.name = "bad_tool"
        bad_tool.parameters = {"type": "array", "items": {"type": "string"}}
        bad_tool.output_schema = None

        mock_mcp = _make_mock_mcp()
        mock_mcp.local_provider._components = {"tool:bad_tool@": bad_tool}
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        with pytest.raises(ValueError, match="inputSchema root must have type"):
            TemplateMCPServer()

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_accepts_schema_with_composition_keywords(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that 2020-12 composition keywords are accepted in input schemas."""
        tool = Mock()
        tool.name = "complex_tool"
        tool.parameters = {
            "type": "object",
            "properties": {
                "input": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "number"},
                    ]
                }
            },
            "$defs": {
                "Metric": {"type": "object", "properties": {"unit": {"type": "string"}}}
            },
        }
        tool.output_schema = None

        mock_mcp = _make_mock_mcp()
        mock_mcp.local_provider._components = {"tool:complex_tool@": tool}
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        server = TemplateMCPServer()
        assert server.mcp == mock_mcp

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_rejects_invalid_output_schema(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that a tool with invalid outputSchema is rejected (covers line 107)."""
        bad_tool = Mock()
        bad_tool.name = "bad_output_tool"
        bad_tool.parameters = {"type": "object", "properties": {}}
        bad_tool.output_schema = {
            "type": "object",
            "properties": {"data": {"$ref": "#/$defs/Missing"}},
        }

        mock_mcp = _make_mock_mcp()
        mock_mcp.local_provider._components = {"tool:bad_output_tool@": bad_tool}
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        with pytest.raises(ValueError, match="outputSchema validation failed"):
            TemplateMCPServer()

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_rejects_unresolved_ref(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that $ref pointing to missing $defs entry is rejected."""
        tool = Mock()
        tool.name = "broken_ref_tool"
        tool.parameters = {
            "type": "object",
            "properties": {"data": {"$ref": "#/$defs/NonExistent"}},
        }
        tool.output_schema = None

        mock_mcp = _make_mock_mcp()
        mock_mcp.local_provider._components = {"tool:broken_ref_tool@": tool}
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        with pytest.raises(ValueError, match="does not resolve"):
            TemplateMCPServer()

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_output_schema_passed_to_tool_registration(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that output_schema is passed when registering tools."""
        mock_mcp = _make_mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        TemplateMCPServer()

        calls = mock_mcp.tool.call_args_list
        for call in calls:
            assert "output_schema" in call.kwargs
            assert call.kwargs["output_schema"] is not None

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_skips_non_tool_components(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that _validate_tool_schemas skips non-tool components."""
        mock_mcp = _make_mock_mcp()
        mock_mcp.local_provider._components = {
            "resource:some_resource@": Mock(),
            "prompt:some_prompt@": Mock(),
        }
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        server = TemplateMCPServer()
        assert server.mcp == mock_mcp


class TestSEP2549CacheMetadata:
    """SEP-2549: TTL and cache scope on tools/list.

    Verifies that cache metadata (ttlMs, cacheScope) is set on each tool
    via the meta kwarg during registration.
    """

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_cache_meta_passed_to_tool_registration(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that meta with ttlMs and cacheScope is passed to each tool."""
        mock_mcp = _make_mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        TemplateMCPServer()

        calls = mock_mcp.tool.call_args_list
        for call in calls:
            meta = call.kwargs.get("meta", {})
            assert meta["ttlMs"] == 300000
            assert meta["cacheScope"] == "public"

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_cache_meta_uses_settings_values(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that cache metadata reads from settings (not hardcoded)."""
        mock_mcp = _make_mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 60000
        mock_settings.TOOL_CACHE_SCOPE = "private"

        TemplateMCPServer()

        calls = mock_mcp.tool.call_args_list
        for call in calls:
            meta = call.kwargs.get("meta", {})
            assert meta["ttlMs"] == 60000
            assert meta["cacheScope"] == "private"

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_all_four_tools_get_cache_meta(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that all 4 registered tools receive cache metadata."""
        mock_mcp = _make_mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        TemplateMCPServer()

        calls = mock_mcp.tool.call_args_list
        assert len(calls) == 4
        for call in calls:
            assert "meta" in call.kwargs

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_get_cache_meta_returns_expected_dict(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test _get_cache_meta builds correct dict from settings."""
        mock_mcp = _make_mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 120000
        mock_settings.TOOL_CACHE_SCOPE = "private"

        server = TemplateMCPServer()

        meta = server._get_cache_meta()
        assert meta == {"ttlMs": 120000, "cacheScope": "private"}


class TestToolAnnotations:
    """Test that all tools are registered with correct ToolAnnotations."""

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_all_tools_have_annotations(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Test that every tool registration includes annotations."""
        mock_mcp = _make_mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        TemplateMCPServer()

        calls = mock_mcp.tool.call_args_list
        assert len(calls) == 4
        for call in calls:
            assert "annotations" in call.kwargs
            ann = call.kwargs["annotations"]
            assert isinstance(ann, ToolAnnotations)

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_bmi_tool_annotations(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """BMI calculator: read-only, not destructive, idempotent, closed-world."""
        mock_mcp = _make_mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        TemplateMCPServer()

        ann = mock_mcp.tool.call_args_list[0].kwargs["annotations"]
        assert ann.title == "BMI Calculator"
        assert ann.readOnlyHint is True
        assert ann.destructiveHint is False
        assert ann.idempotentHint is True
        assert ann.openWorldHint is False

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_web_search_tool_annotations(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Web search: read-only, not destructive, idempotent, open-world."""
        mock_mcp = _make_mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        TemplateMCPServer()

        ann = mock_mcp.tool.call_args_list[1].kwargs["annotations"]
        assert ann.title == "Web Search"
        assert ann.readOnlyHint is True
        assert ann.destructiveHint is False
        assert ann.idempotentHint is True
        assert ann.openWorldHint is True

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_send_email_tool_annotations(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Send email: not read-only, destructive, not idempotent, open-world."""
        mock_mcp = _make_mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        TemplateMCPServer()

        ann = mock_mcp.tool.call_args_list[2].kwargs["annotations"]
        assert ann.title == "Send Email"
        assert ann.readOnlyHint is False
        assert ann.destructiveHint is True
        assert ann.idempotentHint is False
        assert ann.openWorldHint is True

    @patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers")
    @patch("template_mcp_server.src.mcp.settings")
    @patch("template_mcp_server.src.mcp.FastMCP")
    def test_validate_email_tool_annotations(
        self, mock_fastmcp, mock_settings, mock_force_reconfigure
    ):
        """Validate email: read-only, not destructive, idempotent, closed-world."""
        mock_mcp = _make_mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.TOOL_CACHE_TTL_MS = 300000
        mock_settings.TOOL_CACHE_SCOPE = "public"

        TemplateMCPServer()

        ann = mock_mcp.tool.call_args_list[3].kwargs["annotations"]
        assert ann.title == "Validate Email"
        assert ann.readOnlyHint is True
        assert ann.destructiveHint is False
        assert ann.idempotentHint is True
        assert ann.openWorldHint is False
