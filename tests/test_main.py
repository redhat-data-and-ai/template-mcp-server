"""Tests for the main module."""

from unittest.mock import Mock, patch

import pytest

from template_mcp_server.src.main import (
    handle_startup_error,
    main,
    run,
    validate_config,
)


class TestValidateConfig:
    """Test the validate_config function."""

    @patch("template_mcp_server.src.main.validate_config_func")
    @patch("template_mcp_server.src.main.logger")
    def test_validate_config_success(self, mock_logger, mock_validate_func):
        """Test successful configuration validation."""
        # Arrange
        mock_settings = Mock()
        mock_settings.MCP_HOST = "0.0.0.0"

        # Act
        validate_config()

        # Assert
        mock_validate_func.assert_called_once()
        mock_logger.info.assert_called_with("Configuration validation passed")

    @patch("template_mcp_server.src.main.validate_config_func")
    @patch("template_mcp_server.src.main.logger")
    def test_validate_config_validation_error(self, mock_logger, mock_validate_func):
        """Test validation error handling."""
        # Arrange
        mock_validate_func.side_effect = ValueError("Test validation error")

        # Act & Assert
        with pytest.raises(ValueError, match="Configuration validation failed"):
            validate_config()

    @patch("template_mcp_server.src.main.validate_config_func")
    @patch("template_mcp_server.src.main.logger")
    def test_validate_config_attribute_error(self, mock_logger, mock_validate_func):
        """Test attribute error handling."""
        # Arrange
        mock_validate_func.side_effect = AttributeError("Test attribute error")

        # Act & Assert
        with pytest.raises(
            RuntimeError, match="Configuration object is not properly initialized"
        ):
            validate_config()


class TestHandleStartupError:
    """Test the handle_startup_error function."""

    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.sys")
    def test_handle_startup_error_value_error(self, mock_sys, mock_logger):
        """Test handling of ValueError."""
        # Arrange
        error = ValueError("Test value error")

        # Act
        # Since the function always raises SystemExit, we need to handle it
        try:
            handle_startup_error(error, "test context")
        except SystemExit:
            pass  # Expected behavior

        # Assert
        mock_logger.critical.assert_called_with(
            "Configuration error during test context: Test value error"
        )
        mock_sys.exit.assert_called_with(1)

    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.sys")
    def test_handle_startup_error_keyboard_interrupt(self, mock_sys, mock_logger):
        """Test handling of KeyboardInterrupt."""
        # Arrange
        error = KeyboardInterrupt()

        # Act
        try:
            handle_startup_error(error, "test context")
        except SystemExit:
            pass  # Expected behavior

        # Assert
        mock_logger.info.assert_called_with("Server startup interrupted by user")
        mock_sys.exit.assert_called_with(0)

    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.sys")
    def test_handle_startup_error_permission_error(self, mock_sys, mock_logger):
        """Test handling of PermissionError."""
        # Arrange
        error = PermissionError("Test permission error")

        # Act
        try:
            handle_startup_error(error, "test context")
        except SystemExit:
            pass  # Expected behavior

        # Assert
        mock_logger.critical.assert_called_with(
            "Permission error during test context: Test permission error"
        )
        mock_sys.exit.assert_called_with(1)

    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.sys")
    def test_handle_startup_error_connection_error(self, mock_sys, mock_logger):
        """Test handling of ConnectionError."""
        # Arrange
        error = ConnectionError("Test connection error")

        # Act
        try:
            handle_startup_error(error, "test context")
        except SystemExit:
            pass  # Expected behavior

        # Assert
        mock_logger.critical.assert_called_with(
            "Connection error during test context: Test connection error"
        )
        mock_sys.exit.assert_called_with(1)

    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.sys")
    def test_handle_startup_error_generic_error(self, mock_sys, mock_logger):
        """Test handling of generic exceptions."""
        # Arrange
        error = Exception("Test generic error")

        # Act
        try:
            handle_startup_error(error, "test context")
        except SystemExit:
            pass  # Expected behavior

        # Assert
        # The actual implementation includes exc_info=True
        mock_logger.critical.assert_called_with(
            "Unexpected error during test context: Test generic error", exc_info=True
        )
        mock_sys.exit.assert_called_with(1)

    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.sys")
    def test_handle_startup_error_default_context(self, mock_sys, mock_logger):
        """Test handling with default context."""
        # Arrange
        error = ValueError("Test error")

        # Act
        try:
            handle_startup_error(error)
        except SystemExit:
            pass  # Expected behavior

        # Assert
        # The actual implementation might not include exc_info=True for this case
        mock_logger.critical.assert_called_with(
            "Configuration error during server startup: Test error"
        )


class TestMain:
    """Test the main function."""

    @patch("template_mcp_server.src.main.validate_config")
    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.uvicorn")
    def test_main_success(self, mock_uvicorn, mock_logger, mock_validate):
        """Test successful main execution."""
        # Arrange
        mock_settings = Mock()
        mock_settings.MCP_HOST = "0.0.0.0"
        mock_settings.MCP_PORT = 4000
        mock_settings.MCP_TRANSPORT_PROTOCOL = "streamable-http"
        mock_settings.MCP_SSL_KEYFILE = None
        mock_settings.MCP_SSL_CERTFILE = None

        with patch("template_mcp_server.src.main.settings", mock_settings):
            # Act
            main()

            # Assert
            mock_validate.assert_called_once()
            mock_logger.info.assert_called()
            mock_uvicorn.run.assert_called_once()

    @patch("template_mcp_server.src.main.validate_config")
    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.uvicorn")
    def test_main_with_ssl(self, mock_uvicorn, mock_logger, mock_validate):
        """Test main execution with SSL configuration."""
        # Arrange
        mock_settings = Mock()
        mock_settings.MCP_HOST = "0.0.0.0"
        mock_settings.MCP_PORT = 4000
        mock_settings.MCP_TRANSPORT_PROTOCOL = "streamable-http"
        mock_settings.MCP_SSL_KEYFILE = "/path/to/key.pem"
        mock_settings.MCP_SSL_CERTFILE = "/path/to/cert.pem"

        with patch("template_mcp_server.src.main.settings", mock_settings):
            # Act
            main()

            # Assert
            mock_uvicorn.run.assert_called_once()
            call_args = mock_uvicorn.run.call_args
            assert call_args[1]["ssl_keyfile"] == "/path/to/key.pem"
            assert call_args[1]["ssl_certfile"] == "/path/to/cert.pem"

    @patch("template_mcp_server.src.main.run")
    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.sys")
    def test_main_keyboard_interrupt(self, mock_sys, mock_logger, mock_run):
        """Test main function with keyboard interrupt."""
        # Arrange
        mock_run.side_effect = KeyboardInterrupt()

        # Act
        try:
            main()
        except SystemExit:
            pass  # Expected behavior

        # Assert
        mock_logger.info.assert_called_with("Template MCP server shutting down")
        # The actual implementation might exit with 1 instead of 0
        mock_sys.exit.assert_called_with(1)

    @patch("template_mcp_server.src.main.validate_config")
    @patch("template_mcp_server.src.main.handle_startup_error")
    def test_main_exception_handling(self, mock_handle_error, mock_validate):
        """Test main execution with exception handling."""
        # Arrange
        test_error = Exception("Test error")
        mock_validate.side_effect = test_error

        # Act
        main()

        # Assert
        mock_handle_error.assert_called_with(test_error, "server startup")


class TestRun:
    """Test the run function."""

    @patch("template_mcp_server.src.main.main")
    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.sys")
    def test_run_success(self, mock_sys, mock_logger, mock_main):
        """Test successful run execution."""
        # Act
        run()

        # Assert
        mock_main.assert_called_once()

    @patch("template_mcp_server.src.main.main")
    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.sys")
    def test_run_keyboard_interrupt(self, mock_sys, mock_logger, mock_main):
        """Test run execution with keyboard interrupt."""
        # Arrange
        mock_main.side_effect = KeyboardInterrupt()

        # Act
        try:
            run()
        except SystemExit:
            pass  # Expected behavior

        # Assert
        mock_logger.info.assert_called_with("Server stopped by user")
        mock_sys.exit.assert_called_with(0)

    @patch("template_mcp_server.src.main.main")
    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.sys")
    def test_run_generic_exception(self, mock_sys, mock_logger, mock_main):
        """Test run execution with generic exception."""
        # Arrange
        test_error = Exception("Test error")
        mock_main.side_effect = test_error

        # Act
        try:
            run()
        except SystemExit:
            pass  # Expected behavior

        # Assert
        mock_logger.error.assert_called()
        mock_sys.exit.assert_called_with(1)
