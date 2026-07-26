"""Tests for Jinja2 template-injection security utilities."""

from unittest.mock import Mock, patch

import pytest
from jinja2 import Environment

from template_mcp_server.src.settings import Settings
from template_mcp_server.utils.jinja2_security import (
    escape_jinja2_delimiters,
    get_secure_jinja2_env,
    validate_user_query_for_jinja2,
)


@pytest.mark.parametrize("delimiter", ["{{", "}}", "{%", "%}", "{#", "#}"])
def test_escape_jinja2_delimiters_escapes_injection_delimiters(delimiter):
    escaped = escape_jinja2_delimiters(f"user input {delimiter} dangerous")

    assert delimiter not in escaped
    assert "user input" in escaped
    assert "dangerous" in escaped


@pytest.mark.parametrize("query", ["{{ config }}", "{% for x in xs %}", "{# hidden #}"])
def test_validate_user_query_for_jinja2_blocks_injection_patterns(query):
    with pytest.raises(ValueError, match="Potential Jinja2 template injection"):
        validate_user_query_for_jinja2(query)


def test_validate_user_query_for_jinja2_logs_blocked_attempt():
    logger = Mock()

    with patch("template_mcp_server.utils.jinja2_security.logger", logger):
        with pytest.raises(ValueError):
            validate_user_query_for_jinja2("hello {{ user }}")

    logger.warning.assert_called_once()


def test_validate_user_query_for_jinja2_allows_plain_text():
    assert validate_user_query_for_jinja2("plain user search text") == "plain user search text"


def test_get_secure_jinja2_env_enables_autoescape_by_default():
    env = get_secure_jinja2_env()

    assert isinstance(env, Environment)
    assert env.autoescape is True


def test_jinja2_security_feature_flag_defaults_to_true():
    settings = Settings()

    assert settings.ENABLE_JINJA2_SECURITY is True


def test_validate_user_query_for_jinja2_respects_disabled_feature_flag():
    assert validate_user_query_for_jinja2("{{ trusted_template }}", enabled=False) == "{{ trusted_template }}"


def test_escape_jinja2_delimiters_respects_disabled_feature_flag():
    assert escape_jinja2_delimiters("{{ trusted_template }}", enabled=False) == "{{ trusted_template }}"
