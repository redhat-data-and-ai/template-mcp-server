"""Jinja2 security utilities for preventing server-side template injection.

These utilities provide defense-in-depth when handling untrusted input that may
later be passed to Jinja2 templates. They help prevent accidental template
injection but do not make it safe to construct Jinja2 template source from
user-controlled data.

Applications should validate untrusted input before rendering, avoid building
templates from user input, and treat delimiter escaping as a supplementary
control rather than a complete SSTI defense.
"""

from __future__ import annotations

from typing import Any

from jinja2 import Environment

from template_mcp_server.src.settings import settings
from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger(settings.PYTHON_LOG_LEVEL)

JINJA2_INJECTION_PATTERNS: tuple[str, ...] = (
    "{{",
    "}}",
    "{%",
    "%}",
    "{#",
    "#}",
)

_DELIMITER_ESCAPE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("{{", "{ {"),
    ("}}", "} }"),
    ("{%", "{ %"),
    ("%}", "% }"),
    ("{#", "{ #"),
    ("#}", "# }"),
)


def _security_enabled(enabled: bool | None) -> bool:
    """Resolve whether Jinja2 security checks are active."""
    if enabled is None:
        return settings.ENABLE_JINJA2_SECURITY
    return enabled


def _find_injection_pattern(text: str) -> str | None:
    """Return the first Jinja2 delimiter pattern found in text, if any."""
    for pattern in JINJA2_INJECTION_PATTERNS:
        if pattern in text:
            return pattern
    return None


def escape_jinja2_delimiters(text: str, *, enabled: bool | None = None) -> str:
    """Neutralize Jinja2 delimiter sequences in untrusted text.

    Use this only when untrusted input must be embedded as template variable
    data. Escaping is a supplementary control and does not replace input
    validation or safe template design.

    Args:
        text: Untrusted input that may be embedded in a template context.
        enabled: Override for ``ENABLE_JINJA2_SECURITY``. When security is
            disabled, the original text is returned unchanged.

    Returns:
        Text with Jinja2 delimiters broken so they cannot be executed.
    """
    if not _security_enabled(enabled):
        return text

    escaped = text
    for delimiter, replacement in _DELIMITER_ESCAPE_REPLACEMENTS:
        escaped = escaped.replace(delimiter, replacement)
    return escaped


def validate_user_query_for_jinja2(query: str, *, enabled: bool | None = None) -> None:
    """Reject user input that contains Jinja2 template delimiter sequences.

    Call this before rendering or persisting untrusted input that will later
    reach a Jinja2 template. Validation is the preferred first-line control;
    it should run before rendering and before relying on delimiter escaping.

    Args:
        query: Untrusted user input to inspect.
        enabled: Override for ``ENABLE_JINJA2_SECURITY``. When security is
            disabled, validation is skipped.

    Raises:
        ValueError: If a Jinja2 delimiter sequence is detected while security
            checks are enabled.
    """
    if not _security_enabled(enabled):
        return

    matched_pattern = _find_injection_pattern(query)
    if matched_pattern is not None:
        logger.warning(
            "Blocked potential Jinja2 template injection in user input",
            matched_pattern=matched_pattern,
        )
        raise ValueError("Potential Jinja2 template injection detected in user input")


def get_secure_jinja2_env(
    *,
    enabled: bool | None = None,
    **kwargs: Any,
) -> Environment:
    """Return a Jinja2 environment configured for safe template rendering.

    Autoescaping limits HTML/XML injection in rendered output. Callers must
    still validate untrusted input before rendering and must not build template
    source from user-controlled data.

    When security is enabled, ``autoescape`` is always enforced and cannot be
    overridden through ``kwargs``.

    Args:
        enabled: Override for ``ENABLE_JINJA2_SECURITY``. When security is
            disabled, autoescaping is turned off for debugging only.
        **kwargs: Additional keyword arguments forwarded to ``Environment``.

    Returns:
        Configured Jinja2 ``Environment`` instance.
    """
    use_autoescape = _security_enabled(enabled)
    environment_kwargs: dict[str, Any] = dict(kwargs)
    environment_kwargs.pop("autoescape", None)
    if use_autoescape:
        return Environment(autoescape=True, **environment_kwargs)
    # Intentional debug-only path when ENABLE_JINJA2_SECURITY=False.
    return Environment(autoescape=False, **environment_kwargs)  # nosec B701
