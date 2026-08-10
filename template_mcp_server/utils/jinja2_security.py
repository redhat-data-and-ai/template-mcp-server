"""Jinja2 template-injection safeguards for user-controlled text."""

from __future__ import annotations

from jinja2 import Environment

from template_mcp_server.src.settings import settings
from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()

_JINJA2_DELIMITER_REPLACEMENTS = {
    "{{": "{ {",
    "}}": "} }",
    "{%": "{ %",
    "%}": "% }",
    "{#": "{ #",
    "#}": "# }",
}


def escape_jinja2_delimiters(text: str, *, enabled: bool | None = None) -> str:
    """Escape Jinja2 delimiter pairs in user-controlled text.

    Escaping preserves the text while preventing Jinja2 from interpreting user input
    as a template expression, statement, or comment block.
    """
    if not _jinja2_security_enabled(enabled):
        return text

    escaped = text
    for delimiter, replacement in _JINJA2_DELIMITER_REPLACEMENTS.items():
        escaped = escaped.replace(delimiter, replacement)
    return escaped


def validate_user_query_for_jinja2(query: str, *, enabled: bool | None = None) -> str:
    """Validate user input before it is interpolated into a Jinja2 template."""
    if not _jinja2_security_enabled(enabled):
        return query

    for delimiter in _JINJA2_DELIMITER_REPLACEMENTS:
        if delimiter in query:
            logger.warning(
                "Potential Jinja2 template injection blocked",
                delimiter=delimiter,
            )
            raise ValueError("Potential Jinja2 template injection detected")
    return query


def get_secure_jinja2_env(*, enabled: bool | None = None, **kwargs) -> Environment:
    """Return a Jinja2 environment with autoescape enabled by default."""
    if _jinja2_security_enabled(enabled):
        kwargs.setdefault("autoescape", True)
    return Environment(**kwargs)


def _jinja2_security_enabled(enabled: bool | None) -> bool:
    if enabled is not None:
        return enabled
    return settings.ENABLE_JINJA2_SECURITY
