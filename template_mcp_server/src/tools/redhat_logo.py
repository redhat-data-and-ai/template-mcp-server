"""Red Hat logo resource module for the Template MCP Server.

This module provides functionality to read and serve the Red Hat logo
as a base64 encoded resource for MCP clients.
"""

import base64
from pathlib import Path

# Optional: Add a simple resource example


async def read_redhat_logo_content() -> dict:
    """Return the Red Hat logo as a base64 encoded string.

    Reads the Red Hat logo PNG file from the assets directory and returns
    it as a base64 encoded string for MCP clients to use.

    Returns:
        dict: A dictionary containing the logo information with keys:
            - name: Display name for the resource
            - description: Description of the resource
            - mimeType: MIME type of the image (image/png)
            - text: Base64 encoded PNG data

    Note:
        If the logo file is not found or cannot be read, returns an error
        message in the same dictionary format.
    """
    # Get the path to the assets directory relative to this file
    current_dir = Path(__file__).parent
    assets_dir = current_dir / "assets"
    logo_path = assets_dir / "redhat.png"

    try:
        with open(logo_path, "rb") as f:
            logo_data = f.read()
            logo_base64 = base64.b64encode(logo_data).decode("utf-8")

        return {
            "name": "Red Hat Logo",
            "description": "Red Hat logo as base64 encoded PNG",
            "mimeType": "image/png",
            "text": logo_base64,
        }
    except FileNotFoundError:
        return {
            "name": "Red Hat Logo Error",
            "description": "Could not find Red Hat logo file",
            "mimeType": "text/plain",
            "text": f"Error: Could not find logo file at {logo_path}",
        }
    except Exception as e:
        return {
            "name": "Red Hat Logo Error",
            "description": "Error reading Red Hat logo file",
            "mimeType": "text/plain",
            "text": f"Error: {str(e)}",
        }
