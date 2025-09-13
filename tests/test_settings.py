"""Test cases for the settings configuration."""

import os
import pytest
from unittest.mock import patch

from template_mcp_server.src.settings import Settings, validate_config


class TestSettings:
    """Test cases for the Settings configuration class."""

    def test_default_settings(self, clean_environment):
        """Test default settings values."""
        settings = Settings()
        
        assert settings.MCP_HOST == "0.0.0.0"
        assert settings.MCP_PORT == 3000
        assert settings.MCP_TRANSPORT_PROTOCOL == "streamable-http"
        assert settings.MCP_SSL_KEYFILE is None
        assert settings.MCP_SSL_CERTFILE is None
        assert settings.PYTHON_LOG_LEVEL == "INFO"

    def test_settings_from_environment(self):
        """Test settings loaded from environment variables."""
        env_vars = {
            "MCP_HOST": "localhost",
            "MCP_PORT": "8080",
            "MCP_TRANSPORT_PROTOCOL": "http",
            "MCP_SSL_KEYFILE": "/path/to/key.pem",
            "MCP_SSL_CERTFILE": "/path/to/cert.pem",
            "PYTHON_LOG_LEVEL": "DEBUG"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.MCP_HOST == "localhost"
            assert settings.MCP_PORT == 8080
            assert settings.MCP_TRANSPORT_PROTOCOL == "http"
            assert settings.MCP_SSL_KEYFILE == "/path/to/key.pem"
            assert settings.MCP_SSL_CERTFILE == "/path/to/cert.pem"
            assert settings.PYTHON_LOG_LEVEL == "DEBUG"

    def test_port_validation_valid_range(self):
        """Test port validation with valid port numbers."""
        valid_ports = [1024, 3000, 8080, 9000, 65535]
        
        for port in valid_ports:
            with patch.dict(os.environ, {"MCP_PORT": str(port)}):
                settings = Settings()
                assert settings.MCP_PORT == port

    def test_port_validation_field_constraints(self):
        """Test port field constraints from Pydantic."""
        # Test port too low
        with patch.dict(os.environ, {"MCP_PORT": "1023"}):
            with pytest.raises(Exception):  # Pydantic validation error
                Settings()
        
        # Test port too high  
        with patch.dict(os.environ, {"MCP_PORT": "65536"}):
            with pytest.raises(Exception):  # Pydantic validation error
                Settings()

    def test_transport_protocol_options(self):
        """Test different transport protocol options."""
        protocols = ["http", "sse", "streamable-http"]
        
        for protocol in protocols:
            with patch.dict(os.environ, {"MCP_TRANSPORT_PROTOCOL": protocol}):
                settings = Settings()
                assert settings.MCP_TRANSPORT_PROTOCOL == protocol

    def test_log_level_options(self):
        """Test different log level options."""
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in log_levels:
            with patch.dict(os.environ, {"PYTHON_LOG_LEVEL": level}):
                settings = Settings()
                assert settings.PYTHON_LOG_LEVEL == level

    def test_ssl_certificate_settings(self):
        """Test SSL certificate configuration."""
        ssl_config = {
            "MCP_SSL_KEYFILE": "/etc/ssl/private/server.key",
            "MCP_SSL_CERTFILE": "/etc/ssl/certs/server.crt"
        }
        
        with patch.dict(os.environ, ssl_config):
            settings = Settings()
            assert settings.MCP_SSL_KEYFILE == "/etc/ssl/private/server.key"
            assert settings.MCP_SSL_CERTFILE == "/etc/ssl/certs/server.crt"

    def test_partial_environment_override(self, clean_environment):
        """Test partial environment variable override with defaults."""
        with patch.dict(os.environ, {"MCP_HOST": "custom-host", "MCP_PORT": "9999"}):
            settings = Settings()
            
            # Overridden values
            assert settings.MCP_HOST == "custom-host"
            assert settings.MCP_PORT == 9999
            
            # Default values
            assert settings.MCP_TRANSPORT_PROTOCOL == "streamable-http"
            assert settings.PYTHON_LOG_LEVEL == "INFO"
            assert settings.MCP_SSL_KEYFILE is None


class TestValidateConfig:
    """Test cases for the validate_config function."""

    def test_validate_config_success(self):
        """Test successful configuration validation."""
        settings = Settings()
        # Should not raise any exception
        validate_config(settings)

    def test_validate_config_invalid_port_low(self):
        """Test validation with port too low."""
        settings = Settings()
        settings.MCP_PORT = 1023
        
        with pytest.raises(ValueError, match="MCP_PORT must be between 1024 and 65535"):
            validate_config(settings)

    def test_validate_config_invalid_port_high(self):
        """Test validation with port too high."""
        settings = Settings()
        settings.MCP_PORT = 65536
        
        with pytest.raises(ValueError, match="MCP_PORT must be between 1024 and 65535"):
            validate_config(settings)

    def test_validate_config_valid_port_boundaries(self):
        """Test validation with boundary port values."""
        settings = Settings()
        
        # Test lower boundary
        settings.MCP_PORT = 1024
        validate_config(settings)  # Should not raise
        
        # Test upper boundary
        settings.MCP_PORT = 65535
        validate_config(settings)  # Should not raise

    def test_validate_config_invalid_log_level(self):
        """Test validation with invalid log level."""
        settings = Settings()
        settings.PYTHON_LOG_LEVEL = "INVALID"
        
        with pytest.raises(ValueError, match="PYTHON_LOG_LEVEL must be one of"):
            validate_config(settings)

    def test_validate_config_valid_log_levels(self):
        """Test validation with all valid log levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            settings = Settings()
            settings.PYTHON_LOG_LEVEL = level
            validate_config(settings)  # Should not raise

    def test_validate_config_case_insensitive_log_level(self):
        """Test validation handles case insensitive log levels."""
        settings = Settings()
        settings.PYTHON_LOG_LEVEL = "debug"  # lowercase
        validate_config(settings)  # Should not raise (converts to uppercase)

    def test_validate_config_invalid_transport_protocol(self):
        """Test validation with invalid transport protocol."""
        settings = Settings()
        settings.MCP_TRANSPORT_PROTOCOL = "invalid-protocol"
        
        with pytest.raises(ValueError, match="MCP_TRANSPORT_PROTOCOL must be one of"):
            validate_config(settings)

    def test_validate_config_valid_transport_protocols(self):
        """Test validation with all valid transport protocols."""
        valid_protocols = ["streamable-http", "sse", "http"]
        
        for protocol in valid_protocols:
            settings = Settings()
            settings.MCP_TRANSPORT_PROTOCOL = protocol
            validate_config(settings)  # Should not raise

    def test_validate_config_multiple_errors(self):
        """Test validation with multiple configuration errors."""
        settings = Settings()
        settings.MCP_PORT = 999  # Invalid port
        settings.PYTHON_LOG_LEVEL = "INVALID"  # Invalid log level
        
        # Should raise the first error encountered (port validation)
        with pytest.raises(ValueError, match="MCP_PORT must be between"):
            validate_config(settings)

    def test_validate_config_edge_cases(self):
        """Test validation with edge case values."""
        settings = Settings()
        
        # Test with exactly valid values
        settings.MCP_PORT = 1024
        settings.PYTHON_LOG_LEVEL = "CRITICAL"
        settings.MCP_TRANSPORT_PROTOCOL = "streamable-http"
        
        validate_config(settings)  # Should not raise

    def test_validate_config_with_ssl_settings(self):
        """Test validation with SSL settings configured."""
        settings = Settings()
        settings.MCP_SSL_KEYFILE = "/path/to/key.pem"
        settings.MCP_SSL_CERTFILE = "/path/to/cert.pem"
        
        validate_config(settings)  # Should not raise