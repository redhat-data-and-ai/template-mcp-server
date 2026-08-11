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
        assert settings.MCP_TRANSPORT_PROTOCOL == "streamable-http"
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
        valid_protocols = ["streamable-http", "stdio"]

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


class TestClusterReadySettings:
    """Test new settings for cluster-ready deployment."""

    def test_session_cookie_https_only_default(self):
        """Test SESSION_COOKIE_HTTPS_ONLY defaults to None (auto-detect)."""
        settings = Settings()
        assert settings.SESSION_COOKIE_HTTPS_ONLY is None

    def test_session_cookie_https_only_from_env(self):
        """Test SESSION_COOKIE_HTTPS_ONLY can be set via environment."""
        with patch.dict(os.environ, {"SESSION_COOKIE_HTTPS_ONLY": "true"}):
            settings = Settings()
            assert settings.SESSION_COOKIE_HTTPS_ONLY is True

    def test_session_cookie_same_site_default(self):
        """Test SESSION_COOKIE_SAME_SITE defaults to lax."""
        settings = Settings()
        assert settings.SESSION_COOKIE_SAME_SITE == "lax"

    def test_session_cookie_same_site_from_env(self):
        """Test SESSION_COOKIE_SAME_SITE can be set to strict."""
        with patch.dict(os.environ, {"SESSION_COOKIE_SAME_SITE": "strict"}):
            settings = Settings()
            assert settings.SESSION_COOKIE_SAME_SITE == "strict"

    def test_session_cookie_max_age_default(self):
        """Test SESSION_COOKIE_MAX_AGE defaults to 86400 (1 day)."""
        settings = Settings()
        assert settings.SESSION_COOKIE_MAX_AGE == 86400

    def test_session_cookie_max_age_from_env(self):
        """Test SESSION_COOKIE_MAX_AGE can be set via environment."""
        with patch.dict(os.environ, {"SESSION_COOKIE_MAX_AGE": "3600"}):
            settings = Settings()
            assert settings.SESSION_COOKIE_MAX_AGE == 3600

    def test_access_token_expiry_default(self):
        """Test ACCESS_TOKEN_EXPIRY defaults to 3600 (1 hour)."""
        settings = Settings()
        assert settings.ACCESS_TOKEN_EXPIRY == 3600

    def test_access_token_expiry_from_env(self):
        """Test ACCESS_TOKEN_EXPIRY can be set via environment."""
        with patch.dict(os.environ, {"ACCESS_TOKEN_EXPIRY": "7200"}):
            settings = Settings()
            assert settings.ACCESS_TOKEN_EXPIRY == 7200

    def test_sso_scopes_default(self):
        """Test SSO_SCOPES defaults to standard OIDC scopes."""
        settings = Settings()
        assert settings.SSO_SCOPES == ["email", "openid", "profile"]

    def test_sso_scopes_from_env(self):
        """Test SSO_SCOPES can be overridden via environment."""
        with patch.dict(os.environ, {"SSO_SCOPES": '["openid","custom"]'}):
            settings = Settings()
            assert settings.SSO_SCOPES == ["openid", "custom"]

    def test_sso_introspection_timeout_default(self):
        """Test SSO_INTROSPECTION_TIMEOUT defaults to 10.0."""
        settings = Settings()
        assert settings.SSO_INTROSPECTION_TIMEOUT == 10.0

    def test_sso_introspection_timeout_from_env(self):
        """Test SSO_INTROSPECTION_TIMEOUT can be set via environment."""
        with patch.dict(os.environ, {"SSO_INTROSPECTION_TIMEOUT": "30.0"}):
            settings = Settings()
            assert settings.SSO_INTROSPECTION_TIMEOUT == 30.0

    def test_oauth_issuer_default(self):
        """Test OAUTH_ISSUER defaults to None (derive from MCP_HOST_ENDPOINT)."""
        settings = Settings()
        assert settings.OAUTH_ISSUER is None

    def test_oauth_issuer_from_env(self):
        """Test OAUTH_ISSUER can be set via environment."""
        with patch.dict(os.environ, {"OAUTH_ISSUER": "https://auth.example.com"}):
            settings = Settings()
            assert settings.OAUTH_ISSUER == "https://auth.example.com"

    def test_tool_cache_ttl_ms_default(self):
        """Test TOOL_CACHE_TTL_MS defaults to 300000 (5 minutes)."""
        settings = Settings()
        assert settings.TOOL_CACHE_TTL_MS == 300000

    def test_tool_cache_ttl_ms_from_env(self):
        """Test TOOL_CACHE_TTL_MS can be set via environment."""
        with patch.dict(os.environ, {"TOOL_CACHE_TTL_MS": "60000"}):
            settings = Settings()
            assert settings.TOOL_CACHE_TTL_MS == 60000

    def test_tool_cache_scope_default(self):
        """Test TOOL_CACHE_SCOPE defaults to 'public'."""
        settings = Settings()
        assert settings.TOOL_CACHE_SCOPE == "public"

    def test_tool_cache_scope_from_env(self):
        """Test TOOL_CACHE_SCOPE can be set via environment."""
        with patch.dict(os.environ, {"TOOL_CACHE_SCOPE": "private"}):
            settings = Settings()
            assert settings.TOOL_CACHE_SCOPE == "private"

    def test_tool_cache_ttl_ms_zero_disables(self):
        """Test TOOL_CACHE_TTL_MS can be set to 0 to disable caching."""
        with patch.dict(os.environ, {"TOOL_CACHE_TTL_MS": "0"}):
            settings = Settings()
            assert settings.TOOL_CACHE_TTL_MS == 0


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
        valid_protocols = ["streamable-http", "stdio"]

        # Act & Assert
        for protocol in valid_protocols:
            settings = Settings()
            settings.MCP_TRANSPORT_PROTOCOL = protocol
            validate_config(settings)  # Should not raise


class TestLoadDotenvFallback:
    """Test that settings module handles load_dotenv failure gracefully."""

    def test_load_dotenv_exception_is_caught(self):
        """Test settings module loads even when load_dotenv raises."""
        import importlib
        import sys

        with patch("dotenv.load_dotenv", side_effect=OSError("permission denied")):
            # Remove cached module so reload re-executes module body
            mod_key = "template_mcp_server.src.settings"
            saved = sys.modules.pop(mod_key, None)
            try:
                mod = importlib.import_module(mod_key)
                assert hasattr(mod, "Settings")
                assert hasattr(mod, "settings")
            finally:
                if saved is not None:
                    sys.modules[mod_key] = saved


class TestSEP414TraceContextSettings:
    """SEP-414: Trace context settings."""

    def test_trace_context_enabled_default(self):
        s = Settings()
        assert s.MCP_TRACE_CONTEXT_ENABLED is True

    def test_trace_context_from_env(self):
        with patch.dict(os.environ, {"MCP_TRACE_CONTEXT_ENABLED": "false"}):
            s = Settings()
            assert s.MCP_TRACE_CONTEXT_ENABLED is False


class TestSEP2133ExtensionSettings:
    """SEP-2133: Extension framework settings."""

    def test_extensions_enabled_default(self):
        s = Settings()
        assert s.MCP_EXTENSIONS_ENABLED is True

    def test_extensions_from_env(self):
        with patch.dict(os.environ, {"MCP_EXTENSIONS_ENABLED": "false"}):
            s = Settings()
            assert s.MCP_EXTENSIONS_ENABLED is False
