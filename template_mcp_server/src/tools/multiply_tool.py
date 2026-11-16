"""Multiply tool handler for the Template MCP Server."""

from typing import Any, Dict

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


def multiply_numbers(a: float, b: float) -> Dict[str, Any]:
    """Multiply two numbers. Surface metadata lives in config/tools/multiply_numbers.yaml."""
    try:
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise ValueError("Both inputs must be numbers")

        result = a * b

        logger.info(f"Multiply tool called: {a} * {b} = {result}")

        return {
            "status": "success",
            "operation": "multiplication",
            "a": a,
            "b": b,
            "result": result,
            "message": f"Successfully multiplied {a} and {b}",
        }

    except Exception as e:
        logger.error(f"Error in multiply tool: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to perform multiplication",
        }
