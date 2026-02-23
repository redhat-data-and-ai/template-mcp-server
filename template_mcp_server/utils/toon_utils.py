"""TOON (Token Oriented Object Notation) utility functions.

This module provides utilities for converting Python objects to TOON format,
which reduces token usage by 30-60% compared to JSON while maintaining
full data fidelity and human readability.
"""

from typing import Union

import toon_format

from template_mcp_server.src.settings import settings


def to_toon(data: dict | list | str | int | float | bool | None) -> str:
    r"""Convert Python data structure to TOON format string.

    Args:
        data: Python object to convert (dict, list, or primitive types)

    Returns:
        str: TOON-formatted string representation

    Examples:
        >>> to_toon({"success": True, "count": 42})
        'success: true\ncount: 42'

        >>> to_toon([{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}])
        '[2]{id,name}:\n  1,Alice\n  2,Bob'

        >>> to_toon({"sql": "SELECT *\nFROM users"})
        'sql: "SELECT *\\nFROM users"'
    """
    return toon_format.encode(data)


def from_toon(toon_str: str) -> dict | list | str | int | float | bool | None:
    r"""Parse TOON format string back to Python data structure.

    Args:
        toon_str: TOON-formatted string

    Returns:
        Python object (dict, list, or primitive type)

    Examples:
        >>> from_toon('success: true\ncount: 42')
        {'success': True, 'count': 42}

    """
    return toon_format.decode(toon_str)


def format_response(
    data: dict | list | str | int | float | bool | None,
) -> Union[str, dict, list, int, float, bool, None]:
    r"""Conditionally format response based on ENABLE_TOON_FORMAT setting.

    If ENABLE_TOON_FORMAT is True, returns TOON-formatted string.
    Otherwise, returns the original data structure (typically converted to JSON by FastAPI).

    Args:
        data: Python object to format

    Returns:
        TOON-formatted string if enabled, otherwise original data structure

    Examples:
        >>> # When ENABLE_TOON_FORMAT=True
        >>> format_response({"status": "success", "result": 42})
        'status: success\\nresult: 42'

        >>> # When ENABLE_TOON_FORMAT=False
        >>> format_response({"status": "success", "result": 42})
        {'status': 'success', 'result': 42}
    """
    if settings.ENABLE_TOON_FORMAT:
        return to_toon(data)
    return data
