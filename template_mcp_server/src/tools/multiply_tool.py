"""Multiply tool for the Template MCP Server.

This tool demonstrates basic arithmetic functionality by multiplying two numbers.
"""

from template_mcp_server.utils.pylogger import get_python_logger
from template_mcp_server.utils.toon_utils import format_response

logger = get_python_logger()


def multiply_numbers(
    a: float,
    b: float,
):
    """Multiply two numbers with comprehensive tool metadata.

    TOOL_NAME=multiply_numbers
    DISPLAY_NAME=Number Multiplication
    USECASE=Multiply two (floating point) numbers together
    INSTRUCTIONS=1. Provide two numeric values (int or float), 2. Call function, 3. Receive result
    INPUT_DESCRIPTION=Two parameters: a (number), b (number). Examples: (4, 5), (3.14, 2.0), (-1, 10)
    OUTPUT_DESCRIPTION=Response with status, operation, input values (a, b), result, and message (TOON format if enabled)
    EXAMPLES=multiply_numbers(4, 5), multiply_numbers(3.14, 2.0)
    PREREQUISITES=None - standalone arithmetic operation
    RELATED_TOOLS=None - basic math operation

    CPU-bound operation - uses def for computational tasks.

    This is a simple arithmetic tool that multiplies two floating-point numbers.
    Returns data in TOON format (if ENABLE_TOON_FORMAT=True) for 30-60% token reduction,
    otherwise returns standard JSON/dict format.

    Args:
        a: First number to multiply
        b: Second number to multiply

    Returns:
        TOON-formatted string (if enabled) or dict containing the result of multiplication

    Raises:
        ValueError: If either input is not a valid number
    """
    try:
        # Validate inputs
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise ValueError("Both inputs must be numbers")

        result = a * b

        logger.info(f"Multiply tool called: {a} * {b} = {result}")

        return format_response(
            {
                "status": "success",
                "operation": "multiplication",
                "a": a,
                "b": b,
                "result": result,
                "message": f"Successfully multiplied {a} and {b}",
            }
        )

    except Exception as e:
        logger.error(f"Error in multiply tool: {e}")
        return format_response(
            {
                "status": "error",
                "error": str(e),
                "message": "Failed to perform multiplication",
            }
        )
