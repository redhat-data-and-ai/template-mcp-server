"""Tests for the main module — 100% coverage."""

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
    def test_validate_config_success(self, mock_validate_func):
        validate_config()
        mock_validate_func.assert_called_once()

    @patch("template_mcp_server.src.main.validate_config_func")
    def test_validate_config_error(self, mock_validate_func):
        mock_validate_func.side_effect = ValueError("Test error")
        with pytest.raises(ValueError):
            validate_config()

    @patch("template_mcp_server.src.main.validate_config_func")
    def test_validate_config_empty_host(self, mock_validate_func):
        mock_settings = Mock()
        mock_settings.MCP_HOST = ""
        with (
            patch("template_mcp_server.src.main.settings", mock_settings),
            pytest.raises(ValueError, match="MCP_HOST cannot be empty"),
        ):
            validate_config()

    @patch("template_mcp_server.src.main.validate_config_func")
    def test_validate_config_attribute_error(self, mock_validate_func):
        mock_validate_func.side_effect = AttributeError("no attr")
        with pytest.raises(RuntimeError, match="not properly initialized"):
            validate_config()


class TestHandleStartupError:
    """Test handle_startup_error for all exception types."""

    def test_value_error_exits_1(self):
        with pytest.raises(SystemExit) as exc_info:
            handle_startup_error(ValueError("bad config"))
        assert exc_info.value.code == 1

    def test_keyboard_interrupt_exits_0(self):
        with pytest.raises(SystemExit) as exc_info:
            handle_startup_error(KeyboardInterrupt())
        assert exc_info.value.code == 0

    def test_permission_error_exits_1(self):
        with pytest.raises(SystemExit) as exc_info:
            handle_startup_error(PermissionError("port 80"))
        assert exc_info.value.code == 1

    def test_connection_error_exits_1(self):
        with pytest.raises(SystemExit) as exc_info:
            handle_startup_error(ConnectionError("refused"))
        assert exc_info.value.code == 1

    def test_unexpected_error_exits_1(self):
        with pytest.raises(SystemExit) as exc_info:
            handle_startup_error(RuntimeError("unknown"))
        assert exc_info.value.code == 1

    def test_custom_context(self):
        with pytest.raises(SystemExit):
            handle_startup_error(ValueError("x"), "database init")


class TestMain:
    """Test the main function."""

    @patch("template_mcp_server.src.main.validate_config")
    @patch("template_mcp_server.src.main.uvicorn")
    def test_main_success(self, mock_uvicorn, mock_validate):
        mock_settings = Mock()
        mock_settings.MCP_HOST = "0.0.0.0"
        mock_settings.MCP_PORT = 4000
        mock_settings.MCP_TRANSPORT_PROTOCOL = "streamable-http"
        mock_settings.MCP_SSL_KEYFILE = None
        mock_settings.MCP_SSL_CERTFILE = None

        with patch("template_mcp_server.src.main.settings", mock_settings):
            main()
            mock_uvicorn.run.assert_called_once()

    @patch("template_mcp_server.src.main.validate_config")
    @patch("template_mcp_server.src.main.asyncio")
    def test_main_stdio_transport(self, mock_asyncio, mock_validate):
        mock_settings = Mock()
        mock_settings.MCP_TRANSPORT_PROTOCOL = "stdio"

        mock_server_instance = Mock()
        mock_mcp_server_class = Mock(return_value=mock_server_instance)

        with (
            patch("template_mcp_server.src.main.settings", mock_settings),
            patch(
                "template_mcp_server.src.mcp.TemplateMCPServer",
                mock_mcp_server_class,
            ),
        ):
            main()
            mock_asyncio.run.assert_called_once_with(
                mock_server_instance.mcp.run_stdio_async()
            )

    @patch("template_mcp_server.src.main.validate_config")
    @patch("template_mcp_server.src.main.uvicorn")
    def test_main_with_ssl(self, mock_uvicorn, mock_validate):
        mock_settings = Mock()
        mock_settings.MCP_HOST = "0.0.0.0"
        mock_settings.MCP_PORT = 4000
        mock_settings.MCP_TRANSPORT_PROTOCOL = "streamable-http"
        mock_settings.MCP_SSL_KEYFILE = "/path/to/key.pem"
        mock_settings.MCP_SSL_CERTFILE = "/path/to/cert.pem"
        mock_settings.PYTHON_LOG_LEVEL = "INFO"

        with patch("template_mcp_server.src.main.settings", mock_settings):
            main()
            call_kwargs = mock_uvicorn.run.call_args
            assert call_kwargs.kwargs["ssl_keyfile"] == "/path/to/key.pem"
            assert call_kwargs.kwargs["ssl_certfile"] == "/path/to/cert.pem"

    @patch("template_mcp_server.src.main.validate_config")
    def test_main_keyboard_interrupt(self, mock_validate):
        mock_validate.side_effect = KeyboardInterrupt()
        main()

    @patch("template_mcp_server.src.main.validate_config")
    def test_main_exception_calls_handle_startup_error(self, mock_validate):
        mock_validate.side_effect = PermissionError("port 80")
        with pytest.raises(SystemExit):
            main()


class TestRun:
    """Test the run() entry point wrapper."""

    @patch("template_mcp_server.src.main.main")
    def test_run_success(self, mock_main):
        run()
        mock_main.assert_called_once()

    @patch("template_mcp_server.src.main.main")
    def test_run_keyboard_interrupt(self, mock_main):
        mock_main.side_effect = KeyboardInterrupt()
        with pytest.raises(SystemExit) as exc_info:
            run()
        assert exc_info.value.code == 0

    @patch("template_mcp_server.src.main.main")
    def test_run_unexpected_error(self, mock_main):
        mock_main.side_effect = RuntimeError("crash")
        with pytest.raises(SystemExit) as exc_info:
            run()
        assert exc_info.value.code == 1
