"""Integration tests for the Template MCP Server."""

import os
import pytest
from unittest.mock import patch

from template_mcp_server.src.mcp import TemplateMCPServer
from template_mcp_server.src.settings import Settings
from template_mcp_server.src.tools.multiply_tool import multiply_numbers
from template_mcp_server.src.tools.redhat_logo import read_redhat_logo_content
from template_mcp_server.src.tools.code_review_prompt_tool import get_code_review_prompt


@pytest.mark.integration
class TestMCPServerIntegration:
    """Integration tests for the complete MCP server setup."""

    def test_server_initialization_with_real_settings(self, clean_environment):
        """Test server initialization with real settings."""
        # Set up environment
        env_vars = {
            "MCP_HOST": "127.0.0.1",
            "MCP_PORT": "9000",
            "MCP_TRANSPORT_PROTOCOL": "http",
            "PYTHON_LOG_LEVEL": "INFO"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            # Verify settings loaded correctly
            assert settings.MCP_HOST == "127.0.0.1"
            assert settings.MCP_PORT == 9000
            assert settings.MCP_TRANSPORT_PROTOCOL == "http"
            assert settings.PYTHON_LOG_LEVEL == "INFO"
            
            # Initialize server with these settings
            with patch('template_mcp_server.src.mcp.FastMCP'):
                server = TemplateMCPServer()
                assert server is not None

    @pytest.mark.asyncio
    async def test_all_tools_work_together(self, sample_code, mock_png_data):
        """Test that all tools can be used together."""
        # Test multiply tool
        multiply_result = multiply_numbers(6, 7)
        assert multiply_result["status"] == "success"
        assert multiply_result["result"] == 42
        
        # Test code review prompt tool
        prompt_result = get_code_review_prompt(sample_code, "python")
        assert isinstance(prompt_result, list)
        assert len(prompt_result) == 1
        assert "python" in prompt_result[0]["content"].lower()
        
        # Test logo tool (mocked file)
        with patch("builtins.open", side_effect=FileNotFoundError()):
            logo_result = await read_redhat_logo_content()
            # Should handle the error gracefully
            assert logo_result["name"] == "Red Hat Logo Error"

    @pytest.mark.asyncio
    async def test_async_tools_integration(self, mock_png_data):
        """Test integration of async tools."""
        from unittest.mock import mock_open
        
        # Test the async logo tool
        with patch("builtins.open", mock_open(read_data=mock_png_data)):
            result = await read_redhat_logo_content()
            assert result["name"] == "Red Hat Logo"
            assert result["mimeType"] == "image/png"
            assert len(result["text"]) > 0  # Should have base64 data

    def test_error_propagation_through_system(self):
        """Test that errors propagate correctly through the system."""
        # Test multiply tool with invalid input
        result = multiply_numbers("invalid", 5)
        assert result["status"] == "error"
        assert "error" in result
        
        # Test that server initialization fails with bad FastMCP
        with patch('template_mcp_server.src.mcp.FastMCP', side_effect=Exception("FastMCP failed")):
            with pytest.raises(Exception, match="FastMCP failed"):
                TemplateMCPServer()

    def test_configuration_validation_integration(self, clean_environment):
        """Test that configuration validation works with server initialization."""
        from template_mcp_server.src.settings import validate_config
        
        # Test with invalid configuration
        bad_env = {
            "MCP_PORT": "999",  # Invalid port
            "PYTHON_LOG_LEVEL": "INVALID"  # Invalid log level
        }
        
        with patch.dict(os.environ, bad_env):
            with pytest.raises(Exception):  # Pydantic validation should fail
                Settings()

    @pytest.mark.slow
    def test_large_data_processing(self):
        """Test processing of large data through the system."""
        # Test multiply tool with large numbers
        large_result = multiply_numbers(999999, 1000001)
        assert large_result["status"] == "success"
        assert large_result["result"] == 999999999999
        
        # Test code review prompt with large code
        large_code = "\n".join([f"def function_{i}():\n    return {i}" for i in range(1000)])
        prompt_result = get_code_review_prompt(large_code, "python")
        assert isinstance(prompt_result, list)
        assert "function_0" in prompt_result[0]["content"]
        assert "function_999" in prompt_result[0]["content"]

    def test_multiple_tool_calls_in_sequence(self, sample_code):
        """Test multiple tool calls in sequence to verify state management."""
        # Multiple multiply operations
        results = []
        for i in range(5):
            result = multiply_numbers(i, i + 1)
            results.append(result)
            assert result["status"] == "success"
            assert result["result"] == i * (i + 1)
        
        # Multiple prompt generations
        languages = ["python", "javascript", "java"]
        for lang in languages:
            result = get_code_review_prompt(sample_code, lang)
            assert isinstance(result, list)
            assert lang in result[0]["content"].lower()

    def test_concurrent_tool_usage(self, sample_code):
        """Test that tools can be used concurrently (simulation)."""
        import concurrent.futures
        
        def multiply_task(a, b):
            return multiply_numbers(a, b)
        
        def prompt_task(code, lang):
            return get_code_review_prompt(code, lang)
        
        # Simulate concurrent usage
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit multiple tasks
            futures = []
            futures.append(executor.submit(multiply_task, 5, 10))
            futures.append(executor.submit(multiply_task, 3, 7))
            futures.append(executor.submit(prompt_task, sample_code, "python"))
            
            # Collect results
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Verify all tasks completed successfully
            assert len(results) == 3
            for result in results:
                if isinstance(result, dict) and "status" in result:
                    assert result["status"] == "success"
                elif isinstance(result, list):
                    assert len(result) == 1

    def test_environment_isolation(self, clean_environment):
        """Test that different environment configurations are isolated."""
        # First configuration
        env1 = {"MCP_PORT": "3000", "PYTHON_LOG_LEVEL": "INFO"}
        with patch.dict(os.environ, env1):
            settings1 = Settings()
            assert settings1.MCP_PORT == 3000
            assert settings1.PYTHON_LOG_LEVEL == "INFO"
        
        # Second configuration (should not affect first)
        env2 = {"MCP_PORT": "8080", "PYTHON_LOG_LEVEL": "DEBUG"}
        with patch.dict(os.environ, env2):
            settings2 = Settings()
            assert settings2.MCP_PORT == 8080
            assert settings2.PYTHON_LOG_LEVEL == "DEBUG"
        
        # Verify isolation
        assert settings1.MCP_PORT != settings2.MCP_PORT
        assert settings1.PYTHON_LOG_LEVEL != settings2.PYTHON_LOG_LEVEL

    def test_full_server_lifecycle(self, clean_environment):
        """Test the complete server lifecycle from initialization to tool usage."""
        # Set up environment
        env_vars = {
            "MCP_HOST": "localhost",
            "MCP_PORT": "3000",
            "MCP_TRANSPORT_PROTOCOL": "streamable-http",
            "PYTHON_LOG_LEVEL": "INFO"
        }
        
        with patch.dict(os.environ, env_vars):
            # 1. Load configuration
            settings = Settings()
            assert settings.MCP_HOST == "localhost"
            
            # 2. Initialize server
            with patch('template_mcp_server.src.mcp.FastMCP') as mock_fastmcp:
                mock_instance = mock_fastmcp.return_value
                mock_instance.tool.return_value = lambda x: x
                
                server = TemplateMCPServer()
                assert server.mcp == mock_instance
                
                # 3. Verify tools are registered
                assert mock_instance.tool.call_count == 3
                
                # 4. Test tool functionality
                multiply_result = multiply_numbers(8, 9)
                assert multiply_result["status"] == "success"
                assert multiply_result["result"] == 72