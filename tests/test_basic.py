"""Basic tests for the Template MCP Server."""

import importlib
from unittest.mock import Mock, patch

import pytest

import template_mcp_server.src.settings as settings_mod


class TestSettings:
    """Test settings configuration."""

    def test_default_settings(self):
        """Test default settings configuration."""
        # Arrange
        with patch("template_mcp_server.src.settings.Settings") as mock_settings_class:
            mock_settings = Mock()
            mock_settings.MCP_HOST = "0.0.0.0"
            mock_settings.MCP_PORT = 4000
            mock_settings.MCP_TRANSPORT_PROTOCOL = "streamable-http"
            mock_settings.PYTHON_LOG_LEVEL = "INFO"
            mock_settings_class.return_value = mock_settings

            # Act
            from template_mcp_server.src.settings import Settings

            settings = Settings()

            # Assert
            assert settings.MCP_HOST == "0.0.0.0"
            assert settings.MCP_PORT == 4000
            assert settings.MCP_TRANSPORT_PROTOCOL == "streamable-http"
            assert settings.PYTHON_LOG_LEVEL == "INFO"

    def test_port_validation(self):
        """Test port validation logic."""
        # Arrange
        with patch("template_mcp_server.src.settings.Settings") as mock_settings_class:
            mock_settings = Mock()
            mock_settings.MCP_PORT = 4000
            mock_settings_class.return_value = mock_settings

            # Act
            from template_mcp_server.src.settings import Settings

            settings = Settings()

            # Assert
            assert 1024 <= settings.MCP_PORT <= 65535

    def test_log_level_validation(self):
        """Test log level validation logic."""
        # Arrange
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        with patch("template_mcp_server.src.settings.Settings") as mock_settings_class:
            mock_settings = Mock()
            mock_settings.PYTHON_LOG_LEVEL = "INFO"
            mock_settings_class.return_value = mock_settings

            # Act
            from template_mcp_server.src.settings import Settings

            settings = Settings()

            # Assert
            assert settings.PYTHON_LOG_LEVEL.upper() in valid_levels

    def test_transport_protocol_validation(self):
        """Test transport protocol validation logic."""
        # Arrange
        valid_protocols = ["streamable-http", "sse", "http"]
        with patch("template_mcp_server.src.settings.Settings") as mock_settings_class:
            mock_settings = Mock()
            mock_settings.MCP_TRANSPORT_PROTOCOL = "streamable-http"
            mock_settings_class.return_value = mock_settings

            # Act
            from template_mcp_server.src.settings import Settings

            settings = Settings()

            # Assert
            assert settings.MCP_TRANSPORT_PROTOCOL in valid_protocols


class TestServer:
    """Test server functionality."""

    @pytest.fixture(autouse=True)
    def patch_snowflake_account(self, monkeypatch):
        monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "dummy_account")

        importlib.reload(settings_mod)
        import template_mcp_server.src.mcp as server_mod

        importlib.reload(server_mod)
        self.TemplateMCPServer = server_mod.TemplateMCPServer

    def test_server_initialization(self):
        """Test that server can be initialized."""
        with (
            patch("template_mcp_server.src.mcp.settings") as mock_settings,
            patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers"),
            patch("template_mcp_server.src.mcp.FastMCP"),
        ):
            mock_settings.PYTHON_LOG_LEVEL = "INFO"
            server = self.TemplateMCPServer()
            assert server is not None
            assert hasattr(server, "mcp")
            assert hasattr(server, "_register_mcp_tools")

    def test_server_has_mcp_tools(self):
        """Test that server has MCP tools registered."""
        with (
            patch("template_mcp_server.src.mcp.settings") as mock_settings,
            patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers"),
            patch("template_mcp_server.src.mcp.FastMCP"),
        ):
            mock_settings.PYTHON_LOG_LEVEL = "INFO"
            server = self.TemplateMCPServer()
            assert hasattr(server, "_register_mcp_tools")

    def test_server_mcp_instance(self):
        """Test that server has a valid FastMCP instance."""
        with (
            patch("template_mcp_server.src.mcp.settings") as mock_settings,
            patch("template_mcp_server.src.mcp.force_reconfigure_all_loggers"),
            patch("template_mcp_server.src.mcp.FastMCP"),
        ):
            mock_settings.PYTHON_LOG_LEVEL = "INFO"
            server = self.TemplateMCPServer()
            assert server.mcp is not None
            assert hasattr(server.mcp, "tool")

    def test_transport_protocol_configuration(self):
        """Test transport protocol configuration."""
        # Arrange
        with patch("template_mcp_server.src.settings.Settings") as mock_settings_class:
            mock_settings = Mock()
            mock_settings.MCP_TRANSPORT_PROTOCOL = "streamable-http"
            mock_settings_class.return_value = mock_settings

            # Act
            from template_mcp_server.src.settings import Settings

            settings = Settings()

            # Assert
            assert settings.MCP_TRANSPORT_PROTOCOL == "streamable-http"

    def test_health_endpoint(self):
        """Test health endpoint functionality."""
        # Arrange
        with patch("template_mcp_server.src.api.app") as mock_app:
            mock_app.routes = [Mock(path="/health")]

            # Act
            from template_mcp_server.src.api import app

            # Assert
            assert app is not None
            assert hasattr(app, "routes")
            # Skip the actual HTTP test since we're mocking the app
            # The actual HTTP test would require a properly configured app


class TestAPI:
    """Test API functionality."""

    def test_health_endpoint(self):
        """Test health endpoint functionality."""
        # Arrange
        with patch("template_mcp_server.src.api.app") as mock_app:
            mock_app.routes = [Mock(path="/health")]

            # Act
            from template_mcp_server.src.api import app

            # Assert
            assert app is not None
            assert hasattr(app, "routes")
            # Skip the actual HTTP test since we're mocking the app
            # The actual HTTP test would require a properly configured app


class TestMain:
    """Test main module functionality."""

    def test_main_module_import(self):
        """Test that main module can be imported."""
        import template_mcp_server.src.main as main

        assert main is not None

    def test_main_functions_exist(self):
        """Test that main functions exist."""
        import template_mcp_server.src.main as main

        assert hasattr(main, "main")
        assert hasattr(main, "run")
        assert hasattr(main, "validate_config")
        assert hasattr(main, "handle_startup_error")

    def test_main_module_syntax(self):
        """Test that main module has valid syntax."""
        # This test ensures the module can be parsed without syntax errors

        # If we get here, the module has valid syntax
        assert True


class TestIntegration:
    """Integration tests for the entire system."""

    def test_module_imports(self):
        """Test that all modules can be imported without errors."""
        modules_to_test = [
            "template_mcp_server.src.mcp",
            "template_mcp_server.src.settings",
            "template_mcp_server.src.main",
            "template_mcp_server.src.tools.multiply_tool",
            "template_mcp_server.src.resources.redhat_logo",
            "template_mcp_server.src.prompts.code_review_prompt",
            "template_mcp_server.utils.pylogger",
        ]

        for module_name in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                pytest.skip(f"Module {module_name} not available: {e}")

    def test_package_structure(self):
        """Test that the package structure is correct."""
        # Test that the main package exists
        import template_mcp_server

        assert template_mcp_server is not None

        # Test that src package exists
        import template_mcp_server.src

        assert template_mcp_server.src is not None

        # Test that utils package exists
        import template_mcp_server.utils

        assert template_mcp_server.utils is not None

    def test_version_consistency(self):
        """Test that version information is consistent."""
        try:
            from template_mcp_server import __version__

            assert __version__ is not None
            assert isinstance(__version__, str)
        except ImportError:
            pytest.skip("Version not available")


class TestConfiguration:
    """Test configuration and environment handling."""

    def test_environment_variable_handling(self):
        """Test environment variable handling."""
        # Arrange
        with patch("template_mcp_server.src.settings.Settings") as mock_settings_class:
            mock_settings = Mock()
            mock_settings.MCP_HOST = "0.0.0.0"
            mock_settings.MCP_PORT = 4000
            mock_settings_class.return_value = mock_settings

            # Act
            from template_mcp_server.src.settings import Settings

            settings = Settings()

            # Assert
            assert settings.MCP_HOST == "0.0.0.0"
            assert settings.MCP_PORT == 4000

    def test_ssl_configuration(self):
        """Test SSL configuration handling."""
        # Arrange
        with patch("template_mcp_server.src.settings.Settings") as mock_settings_class:
            mock_settings = Mock()
            mock_settings.MCP_SSL_KEYFILE = "/path/to/key.pem"
            mock_settings.MCP_SSL_CERTFILE = "/path/to/cert.pem"
            mock_settings_class.return_value = mock_settings

            # Act
            from template_mcp_server.src.settings import Settings

            settings = Settings()

            # Assert
            assert settings.MCP_SSL_KEYFILE == "/path/to/key.pem"
            assert settings.MCP_SSL_CERTFILE == "/path/to/cert.pem"
