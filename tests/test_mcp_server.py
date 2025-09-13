"""Test cases for the MCP server."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from template_mcp_server.src.mcp import TemplateMCPServer


class TestTemplateMCPServer:
    """Test cases for the TemplateMCPServer class."""

    def test_server_initialization_success(self):
        """Test successful MCP server initialization."""
        with patch("template_mcp_server.src.mcp.FastMCP") as mock_fastmcp:
            mock_mcp_instance = Mock()
            mock_fastmcp.return_value = mock_mcp_instance

            server = TemplateMCPServer()

            assert server.mcp == mock_mcp_instance
            mock_fastmcp.assert_called_once_with("template")

    def test_server_initialization_failure(self):
        """Test MCP server initialization failure."""
        with patch(
            "template_mcp_server.src.mcp.FastMCP",
            side_effect=Exception("FastMCP error"),
        ):
            with pytest.raises(Exception, match="FastMCP error"):
                TemplateMCPServer()

    def test_register_mcp_tools_called(self):
        """Test that _register_mcp_tools is called during initialization."""
        with patch("template_mcp_server.src.mcp.FastMCP") as mock_fastmcp:
            mock_mcp_instance = Mock()
            mock_fastmcp.return_value = mock_mcp_instance

            with patch.object(
                TemplateMCPServer, "_register_mcp_tools"
            ) as mock_register:
                TemplateMCPServer()
                mock_register.assert_called_once()

    def test_register_mcp_tools_multiply_numbers(self):
        """Test that multiply_numbers tool is registered."""
        with patch("template_mcp_server.src.mcp.FastMCP") as mock_fastmcp:
            mock_mcp_instance = Mock()
            mock_tool_decorator = Mock()
            mock_mcp_instance.tool.return_value = mock_tool_decorator
            mock_fastmcp.return_value = mock_mcp_instance

            server = TemplateMCPServer()

            # Verify tool decorator was called for multiply_numbers
            assert mock_mcp_instance.tool.called
            assert mock_tool_decorator.called

    def test_register_mcp_tools_all_tools(self):
        """Test that all tools are registered correctly."""
        with patch("template_mcp_server.src.mcp.FastMCP") as mock_fastmcp:
            mock_mcp_instance = Mock()
            mock_tool_decorator = Mock()
            mock_mcp_instance.tool.return_value = mock_tool_decorator
            mock_fastmcp.return_value = mock_mcp_instance

            server = TemplateMCPServer()

            # Should be called 3 times (for 3 tools)
            assert mock_mcp_instance.tool.call_count == 3
            assert mock_tool_decorator.call_count == 3

    def test_tool_registration_order(self):
        """Test that tools are registered in expected order."""
        with patch("template_mcp_server.src.mcp.FastMCP") as mock_fastmcp:
            mock_mcp_instance = Mock()
            mock_tool_decorator = Mock()
            mock_mcp_instance.tool.return_value = mock_tool_decorator
            mock_fastmcp.return_value = mock_mcp_instance

            # Track the actual function calls
            called_functions = []

            def track_calls(func):
                called_functions.append(func.__name__)
                return func

            mock_tool_decorator.side_effect = track_calls

            server = TemplateMCPServer()

            # Verify all expected tools are registered
            expected_tools = [
                "multiply_numbers",
                "read_redhat_logo_content",
                "get_code_review_prompt",
            ]
            assert len(called_functions) == len(expected_tools)
            for tool in expected_tools:
                assert tool in called_functions

    def test_server_logging_on_success(self):
        """Test that success is logged when server initializes."""
        with patch("template_mcp_server.src.mcp.FastMCP"):
            with patch("template_mcp_server.src.mcp.logger") as mock_logger:
                TemplateMCPServer()
                mock_logger.info.assert_called_with(
                    "Template MCP Server initialized successfully"
                )

    def test_server_logging_on_failure(self):
        """Test that failure is logged when server initialization fails."""
        with patch(
            "template_mcp_server.src.mcp.FastMCP", side_effect=Exception("Test error")
        ):
            with patch("template_mcp_server.src.mcp.logger") as mock_logger:
                with pytest.raises(Exception):
                    TemplateMCPServer()

                mock_logger.error.assert_called_with(
                    "Failed to initialize Template MCP Server: Test error"
                )

    def test_server_mcp_instance_accessible(self):
        """Test that the FastMCP instance is accessible through the server."""
        with patch("template_mcp_server.src.mcp.FastMCP") as mock_fastmcp:
            mock_mcp_instance = Mock()
            mock_fastmcp.return_value = mock_mcp_instance

            server = TemplateMCPServer()

            assert hasattr(server, "mcp")
            assert server.mcp == mock_mcp_instance

    def test_register_tools_error_handling(self):
        """Test error handling in tool registration."""
        with patch("template_mcp_server.src.mcp.FastMCP") as mock_fastmcp:
            mock_mcp_instance = Mock()
            mock_mcp_instance.tool.side_effect = Exception("Tool registration error")
            mock_fastmcp.return_value = mock_mcp_instance

            with pytest.raises(Exception):
                TemplateMCPServer()

    def test_server_imports_available(self):
        """Test that required imports are available."""
        # This test verifies that the server can import all required tools
        with patch("template_mcp_server.src.mcp.FastMCP"):
            try:
                server = TemplateMCPServer()
                # If we get here, all imports worked
                assert True
            except ImportError as e:
                pytest.fail(f"Failed to import required modules: {e}")

    @patch("template_mcp_server.src.mcp.multiply_numbers")
    @patch("template_mcp_server.src.mcp.read_redhat_logo_content")
    @patch("template_mcp_server.src.mcp.get_code_review_prompt")
    def test_tool_functions_imported(self, mock_prompt, mock_logo, mock_multiply):
        """Test that all tool functions are properly imported."""
        with patch("template_mcp_server.src.mcp.FastMCP"):
            server = TemplateMCPServer()

            # Verify that the tool functions exist and are callable
            assert callable(mock_multiply)
            assert callable(mock_logo)
            assert callable(mock_prompt)

    def test_server_class_structure(self):
        """Test the basic structure of the TemplateMCPServer class."""
        with patch("template_mcp_server.src.mcp.FastMCP"):
            server = TemplateMCPServer()

            # Check that required methods exist
            assert hasattr(server, "_register_mcp_tools")
            assert callable(getattr(server, "_register_mcp_tools"))

            # Check that mcp attribute exists
            assert hasattr(server, "mcp")

    def test_multiple_server_instances(self):
        """Test that multiple server instances can be created."""
        with patch("template_mcp_server.src.mcp.FastMCP") as mock_fastmcp:
            # Create different mock instances for each call
            mock_fastmcp.side_effect = [Mock(), Mock()]

            server1 = TemplateMCPServer()
            server2 = TemplateMCPServer()

            assert server1 is not server2
            assert server1.mcp is not server2.mcp
            assert mock_fastmcp.call_count == 2

    def test_server_initialization_idempotent(self):
        """Test that server initialization is idempotent."""
        with patch("template_mcp_server.src.mcp.FastMCP") as mock_fastmcp:
            mock_mcp_instance = Mock()
            mock_fastmcp.return_value = mock_mcp_instance

            server = TemplateMCPServer()
            initial_mcp = server.mcp

            # Multiple calls to _register_mcp_tools should not change the mcp instance
            server._register_mcp_tools()
            assert server.mcp is initial_mcp
