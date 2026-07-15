"""Tests for Jinja2 security utilities."""

from unittest.mock import patch

import pytest
from jinja2 import Environment

from template_mcp_server.utils.jinja2_security import (
    JINJA2_INJECTION_PATTERNS,
    escape_jinja2_delimiters,
    get_secure_jinja2_env,
    validate_user_query_for_jinja2,
)


class TestEscapeJinja2Delimiters:
    """Test escape_jinja2_delimiters."""

    @pytest.mark.parametrize(
        ("input_text", "expected"),
        [
            ("{{ user }}", "{ { user } }"),
            ("{% if x %}", "{ % if x % }"),
            ("{# comment #}", "{ # comment # }"),
            ("safe text", "safe text"),
            ("", ""),
        ],
    )
    def test_escapes_all_delimiters_when_enabled(self, input_text, expected):
        """Test that all Jinja2 delimiter sequences are neutralized."""
        # Act
        result = escape_jinja2_delimiters(input_text, enabled=True)

        # Assert
        assert result == expected

    def test_returns_original_text_when_disabled(self):
        """Test that escaping is skipped when security is disabled."""
        # Arrange
        malicious = "{{ 7*7 }}"

        # Act
        result = escape_jinja2_delimiters(malicious, enabled=False)

        # Assert
        assert result == malicious

    def test_escaped_text_is_not_executable_in_secure_env(self):
        """Test that escaped user input cannot execute template expressions."""
        # Arrange
        user_input = "{{ 7*7 }}"
        escaped = escape_jinja2_delimiters(user_input, enabled=True)
        env = get_secure_jinja2_env(enabled=True)
        template = env.from_string("User said: {{ message }}")

        # Act
        rendered = template.render(message=escaped)

        # Assert
        assert rendered == "User said: { { 7*7 } }"
        assert "49" not in rendered


class TestValidateUserQueryForJinja2:
    """Test validate_user_query_for_jinja2."""

    @pytest.mark.parametrize(
        "query",
        [
            "{{",
            "}}",
            "{%",
            "%}",
            "{#",
            "#}",
            "Hello {{ name }}",
            "before {% end %} after",
            "note {# hidden #}",
        ],
    )
    def test_raises_on_injection_patterns_when_enabled(self, query):
        """Test that each Jinja2 delimiter pattern is rejected."""
        # Act & Assert
        with pytest.raises(ValueError, match="Potential Jinja2 template injection"):
            validate_user_query_for_jinja2(query, enabled=True)

    def test_allows_safe_input_when_enabled(self):
        """Test that safe user input passes validation."""
        # Act & Assert
        validate_user_query_for_jinja2("show me sales data", enabled=True)

    def test_skips_validation_when_disabled(self):
        """Test that validation is skipped when security is disabled."""
        # Act & Assert
        validate_user_query_for_jinja2("{{ 7*7 }}", enabled=False)

    @patch("template_mcp_server.utils.jinja2_security.logger")
    def test_logs_warning_when_injection_blocked(self, mock_logger):
        """Test that blocked injection attempts are logged at WARNING."""
        # Act
        with pytest.raises(ValueError):
            validate_user_query_for_jinja2("{{ exploit }}", enabled=True)

        # Assert
        mock_logger.warning.assert_called_once()
        assert (
            mock_logger.warning.call_args[0][0]
            == "Blocked potential Jinja2 template injection in user input"
        )


class TestGetSecureJinja2Env:
    """Test get_secure_jinja2_env."""

    def test_enables_autoescape_when_security_enabled(self):
        """Test that autoescaping is enabled when security is on."""
        # Act
        env = get_secure_jinja2_env(enabled=True)

        # Assert
        assert env.autoescape is True

    def test_disables_autoescape_when_security_disabled(self):
        """Test that autoescaping is disabled for debugging when security is off."""
        # Act
        env = get_secure_jinja2_env(enabled=False)

        # Assert
        assert env.autoescape is False

    def test_returns_jinja2_environment(self):
        """Test that a Jinja2 Environment instance is returned."""
        # Act
        env = get_secure_jinja2_env(enabled=True)

        # Assert
        assert isinstance(env, Environment)

    def test_secure_env_escapes_html_in_output(self):
        """Test that autoescape prevents HTML injection in rendered output."""
        # Arrange
        env = get_secure_jinja2_env(enabled=True)
        template = env.from_string("<p>{{ content }}</p>")

        # Act
        rendered = template.render(content="<script>alert(1)</script>")

        # Assert
        assert "<script>" not in rendered
        assert "&lt;script&gt;" in rendered

    def test_security_flag_overrides_autoescape_kwarg(self):
        """Test that enabled security cannot be bypassed via kwargs."""
        # Act
        env = get_secure_jinja2_env(enabled=True, autoescape=False)

        # Assert
        assert env.autoescape is True


class TestJinja2SecurityConstants:
    """Test module constants."""

    def test_injection_patterns_cover_required_delimiters(self):
        """Test that all required delimiter patterns are defined."""
        # Assert
        assert "{{" in JINJA2_INJECTION_PATTERNS
        assert "}}" in JINJA2_INJECTION_PATTERNS
        assert "{%" in JINJA2_INJECTION_PATTERNS
        assert "%}" in JINJA2_INJECTION_PATTERNS
        assert "{#" in JINJA2_INJECTION_PATTERNS
        assert "#}" in JINJA2_INJECTION_PATTERNS
