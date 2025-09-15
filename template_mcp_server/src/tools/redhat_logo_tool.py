"""Red Hat logo tool for the Template MCP Server.

This tool provides functionality to read and serve the Red Hat logo
as a base64 encoded resource for MCP clients as a tool.
"""

import base64
from pathlib import Path
from typing import Any, Dict

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


async def get_redhat_logo() -> Dict[str, Any]:
    """Return the Red Hat logo as a base64 encoded string.

    TOOL_NAME=get_redhat_logo
    DISPLAY_NAME=Get Red Hat Logo
    USECASE=Retrieve Red Hat logo for presentations, documentation, or branding
    INSTRUCTIONS=1. Call function (no parameters needed), 2. Receive base64-encoded logo data
    INPUT_DESCRIPTION=No input parameters required
    OUTPUT_DESCRIPTION=Dictionary with status, operation, logo metadata (name, description, mimeType), base64 data, size info, and message
    EXAMPLES=get_redhat_logo()
    PREREQUISITES=None - logo file must exist in assets directory
    RELATED_TOOLS=None - standalone asset retrieval

    Resource-as-tool pattern - async def for file I/O operations.

    Reads the Red Hat logo PNG file from the assets directory and returns
    it as a base64 encoded string for MCP clients to use.

    Returns:
        Dict[str, Any]: A dictionary containing the logo information with keys:
            - status: Operation status (success/error)
            - name: Display name for the logo
            - description: Description of the logo
            - mimeType: MIME type of the image (image/png)
            - data: Base64 encoded PNG data
            - message: Status message

    Note:
        If the logo file is not found or cannot be read, returns an error
        response with appropriate error information.
    """
    try:
        # Get the path to the assets directory relative to this file
        current_dir = Path(__file__).parent.parent  # Go up from tools to src
        assets_dir = current_dir / "assets"
        logo_path = assets_dir / "redhat.png"

        logger.info(f"Reading Red Hat logo from: {logo_path}")

        with open(logo_path, "rb") as f:
            logo_data = f.read()
            logo_base64 = base64.b64encode(logo_data).decode("utf-8")

        logger.info("Successfully read and encoded Red Hat logo")

        return {
            "status": "success",
            "operation": "get_redhat_logo",
            "name": "Red Hat Logo",
            "description": "Red Hat logo as base64 encoded PNG",
            "mimeType": "image/png",
            "data": logo_base64,
            "size_bytes": len(logo_data),
            "message": "Successfully retrieved Red Hat logo",
        }

    except FileNotFoundError:
        error_msg = f"Could not find logo file at {logo_path}"
        logger.error(error_msg)
        return {
            "status": "error",
            "operation": "get_redhat_logo",
            "error": "file_not_found",
            "message": error_msg,
        }
    except PermissionError:
        error_msg = f"Permission denied reading logo file at {logo_path}"
        logger.error(error_msg)
        return {
            "status": "error",
            "operation": "get_redhat_logo",
            "error": "permission_denied",
            "message": error_msg,
        }
    except Exception as e:
        error_msg = f"Error reading logo file: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "operation": "get_redhat_logo",
            "error": "generic_error",
            "message": error_msg,
        }
