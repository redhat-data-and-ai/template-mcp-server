"""Whimsify tool for the Template MCP Server.

This tool demonstrates a simple mathematical operation: whimsify(x) = (x+x)/2.
"""

from typing import Any, Dict, Union

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


def whimsify_number(
    x: Union[float, int],
) -> Dict[str, Any]:
    """Apply the whimsify operation to a number.

    CPU-bound operation - uses def for computational tasks.

    Args:
        x: Number to whimsify

    Returns:
        Dictionary containing the result of whimsify operation
    """
    logger.info(
        "whimsify_number invoked",
        extra={"input": {"x": x}},
    )

    try:
        result = (x + x) / 2

        logger.info(
            "Whimsify operation completed successfully",
            extra={"input": {"x": x}, "output": {"result": result}},
        )

        output = {
            "status": "success",
            "operation": "whimsify",
            "x": x,
            "result": result,
            "message": f"Successfully whimsified {x}",
        }

        logger.debug("whimsify_number output", extra={"output": output})
        return output

    except Exception as e:
        logger.exception(
            "Error in whimsify_number",
            extra={"input": {"x": x}, "error": str(e)},
        )
        error_output = {
            "status": "error",
            "error": str(e),
            "message": "Failed to perform whimsify operation",
        }
        logger.debug("whimsify_number error output", extra={"output": error_output})
        return error_output
