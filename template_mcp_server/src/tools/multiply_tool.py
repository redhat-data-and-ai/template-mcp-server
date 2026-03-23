"""Multiply tool for the Template MCP Server.

This tool demonstrates basic arithmetic functionality by multiplying two numbers.
"""

from typing import Any, Dict, Union

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


def multiply_numbers(
    a: Union[float, int],
    b: Union[float, int],
) -> Dict[str, Any]:
    """Multiply two numbers with comprehensive tool metadata.

    CPU-bound operation - uses def for computational tasks.

    Args:
        a: First number to multiply
        b: Second number to multiply

    Returns:
        Dictionary containing the result of multiplication
    """
    logger.info(
        "multiply_numbers invoked",
        extra={"input": {"a": a, "b": b}},
    )

    try:
        result = a * b

        logger.info(
            "Multiplication completed successfully",
            extra={"input": {"a": a, "b": b}, "output": {"result": result}},
        )

        output = {
            "status": "success",
            "operation": "multiplication",
            "a": a,
            "b": b,
            "result": result,
            "message": f"Successfully multiplied {a} and {b}",
        }

        logger.debug("multiply_numbers output", extra={"output": output})
        return output

    except Exception as e:
        logger.exception(
            "Error in multiply_numbers",
            extra={"input": {"a": a, "b": b}, "error": str(e)},
        )
        error_output = {
            "status": "error",
            "error": str(e),
            "message": "Failed to perform multiplication",
        }
        logger.debug("multiply_numbers error output", extra={"output": error_output})
        return error_output
