"""Tests for the main module."""

from unittest.mock import Mock, patch

import pytest

from template_mcp_server.src.main import validate_config


class TestValidateConfig:
    """Test the validate_config function."""

    @patch("template_mcp_server.src.main.validate_config_func")
    def test_validate_config_success(self, mock_validate_func):
        """Test successful configuration validation."""
        validate_config()
        mock_validate_func.assert_called_once()

    @patch("template_mcp_server.src.main.validate_config_func")
    def test_validate_config_error(self, mock_validate_func):
        """Test validation error handling."""
        mock_validate_func.side_effect = ValueError("Test error")

        with pytest.raises(ValueError):
            validate_config()


class TestMain:
    """Test the main function."""

    @patch("template_mcp_server.src.main.validate_config")
    @patch("template_mcp_server.src.main.uvicorn")
    def test_main_success(self, mock_uvicorn, mock_validate):
        """Test successful main execution."""
        mock_settings = Mock()
        mock_settings.MCP_HOST = "0.0.0.0"
        mock_settings.MCP_PORT = 4000
        mock_settings.MCP_TRANSPORT_PROTOCOL = "streamable-http"
        mock_settings.MCP_SSL_KEYFILE = None
        mock_settings.MCP_SSL_CERTFILE = None

        with patch("template_mcp_server.src.main.settings", mock_settings):
            from template_mcp_server.src.main import main

            main()
            mock_uvicorn.run.assert_called_once()
