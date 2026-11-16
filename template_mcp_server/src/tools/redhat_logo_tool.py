"""Red Hat logo tool handler for the Template MCP Server."""

import base64
from pathlib import Path
from typing import Any, Dict

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


async def get_redhat_logo() -> Dict[str, Any]:
    """Return the Red Hat logo as base64. Metadata lives in config/tools/get_redhat_logo.yaml."""
    try:
        current_dir = Path(__file__).parent.parent
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
