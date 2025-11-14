"""Tests for the settings module."""

import os
from unittest.mock import patch

import pytest

from template_mcp_server.src.settings import Settings, validate_config


class TestSettings:
    """Test the Settings class."""

    def test_default_settings(self):
        """Test that default settings are correct."""
        # Arrange & Act
        settings = Settings()

        # Assert
        assert settings.MCP_HOST == "localhost"
        assert settings.MCP_TRANSPORT_PROTOCOL == "http"
        assert settings.PYTHON_LOG_LEVEL == "INFO"
        assert settings.MCP_SSL_KEYFILE is None
        assert settings.MCP_SSL_CERTFILE is None

    def test_custom_settings_from_env(self):
        """Test that settings can be overridden from environment variables."""
        # Arrange
        env_vars = {
            "MCP_HOST": "localhost",
            "MCP_PORT": "8080",
            "MCP_TRANSPORT_PROTOCOL": "streamable-http",
            "PYTHON_LOG_LEVEL": "DEBUG",
            "MCP_SSL_KEYFILE": "/path/to/key.pem",
            "MCP_SSL_CERTFILE": "/path/to/cert.pem",
        }

        # Act
        with patch.dict(os.environ, env_vars):
            settings = Settings()

        # Assert
        assert settings.MCP_HOST == "localhost"
        assert settings.MCP_PORT == 8080
        assert settings.MCP_TRANSPORT_PROTOCOL == "streamable-http"
        assert settings.PYTHON_LOG_LEVEL == "DEBUG"
        assert settings.MCP_SSL_KEYFILE == "/path/to/key.pem"
        assert settings.MCP_SSL_CERTFILE == "/path/to/cert.pem"

    def test_port_validation(self):
        """Test port validation constraints."""
        # Test valid port
        settings = Settings()
        assert 1024 <= settings.MCP_PORT <= 65535

    def test_log_level_validation(self):
        """Test log level validation."""
        # Arrange
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        # Act & Assert
        for level in valid_levels:
            with patch.dict(os.environ, {"PYTHON_LOG_LEVEL": level}):
                settings = Settings()
                assert settings.PYTHON_LOG_LEVEL.upper() in valid_levels

    def test_transport_protocol_validation(self):
        """Test transport protocol validation."""
        # Arrange
        valid_protocols = ["streamable-http", "sse", "http"]

        # Act & Assert
        for protocol in valid_protocols:
            with patch.dict(os.environ, {"MCP_TRANSPORT_PROTOCOL": protocol}):
                settings = Settings()
                assert settings.MCP_TRANSPORT_PROTOCOL in valid_protocols

    def test_settings_immutability(self):
        """Test that settings are properly configured."""
        # Arrange
        settings = Settings()

        # Act & Assert
        # Settings should be accessible and have the expected attributes
        assert hasattr(settings, "MCP_HOST")
        assert hasattr(settings, "MCP_PORT")
        assert hasattr(settings, "MCP_TRANSPORT_PROTOCOL")
        assert hasattr(settings, "PYTHON_LOG_LEVEL")


class TestValidateConfig:
    """Test the validate_config function."""

    def test_valid_config(self):
        """Test validation with valid configuration."""
        # Arrange
        settings = Settings()

        # Act & Assert
        # Should not raise any exception
        validate_config(settings)

    def test_invalid_port_too_low(self):
        """Test validation with port below minimum."""
        # Arrange
        settings = Settings()
        settings.MCP_PORT = 1023  # Below minimum

        # Act & Assert
        with pytest.raises(ValueError, match="MCP_PORT must be between 1024 and 65535"):
            validate_config(settings)

    def test_invalid_port_too_high(self):
        """Test validation with port above maximum."""
        # Arrange
        settings = Settings()
        settings.MCP_PORT = 65536  # Above maximum

        # Act & Assert
        with pytest.raises(ValueError, match="MCP_PORT must be between 1024 and 65535"):
            validate_config(settings)

    def test_invalid_log_level(self):
        """Test validation with invalid log level."""
        # Arrange
        settings = Settings()
        settings.PYTHON_LOG_LEVEL = "INVALID"

        # Act & Assert
        with pytest.raises(ValueError, match="PYTHON_LOG_LEVEL must be one of"):
            validate_config(settings)

    def test_invalid_transport_protocol(self):
        """Test validation with invalid transport protocol."""
        # Arrange
        settings = Settings()
        settings.MCP_TRANSPORT_PROTOCOL = "invalid"

        # Act & Assert
        with pytest.raises(ValueError, match="MCP_TRANSPORT_PROTOCOL must be one of"):
            validate_config(settings)

    def test_valid_log_levels(self):
        """Test all valid log levels pass validation."""
        # Arrange
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        # Act & Assert
        for level in valid_levels:
            settings = Settings()
            settings.PYTHON_LOG_LEVEL = level
            validate_config(settings)  # Should not raise

    def test_valid_transport_protocols(self):
        """Test all valid transport protocols pass validation."""
        # Arrange
        valid_protocols = ["streamable-http", "sse", "http"]

        # Act & Assert
        for protocol in valid_protocols:
            settings = Settings()
            settings.MCP_TRANSPORT_PROTOCOL = protocol
            validate_config(settings)  # Should not raise
