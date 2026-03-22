"""Whimsify tool for the Template MCP Server.

This tool demonstrates a simple mathematical operation: whimsify(x) = (x+x)/2.
"""

from typing import Any, Dict

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


def whimsify(
    x: float,
) -> Dict[str, Any]:
    """Apply the whimsify operation to a number.

    CPU-bound operation - uses def for computational tasks.

    Args:
        x: Number to whimsify

    Returns:
        Dictionary containing the result of whimsify operation

    Raises:
        ValueError: If input is not a valid number
    """
    try:
        # Validate inputs
        if not isinstance(x, (int, float)):
            raise ValueError("Input must be a number")

        result = (x + x) / 2

        logger.info(f"Whimsify tool called: ({x}+{x})/2 = {result}")

        return {
            "status": "success",
            "operation": "whimsify",
            "x": x,
            "result": result,
            "message": f"Successfully whimsified {x}",
        }

    except Exception as e:
        logger.error(f"Error in whimsify tool: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to perform whimsify operation",
        }
