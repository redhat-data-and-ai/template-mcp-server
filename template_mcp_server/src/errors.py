"""MCP error codes and exception classes per 2026-07-28 specification.

Defines error code allocation policy, MCP-reserved error codes,
and exception classes integrating with the MCP SDK's McpError/ErrorData.
"""

from typing import Any, Optional

from mcp.shared.exceptions import McpError
from mcp.types import ErrorData

# ── Error Code Allocation Ranges ──────────────────────────────────────
# -32000 to -32019: implementation-defined (server-specific)
# -32020 to -32099: MCP protocol reserved
# -32600 to -32700: standard JSON-RPC (defined in mcp.types)

IMPL_DEFINED_RANGE_MIN = -32019
IMPL_DEFINED_RANGE_MAX = -32000

MCP_RESERVED_RANGE_MIN = -32099
MCP_RESERVED_RANGE_MAX = -32020


# ── MCP Protocol Reserved Error Codes ────────────────────────────────

HEADER_MISMATCH = -32020
MISSING_REQUIRED_CLIENT_CAPABILITY = -32021
UNSUPPORTED_PROTOCOL_VERSION = -32022


# ── Renumbered Error Codes ────────────────────────────────────────────
# Resource not found renumbered from -32002 to -32602 per 2026-07-28 spec.

RESOURCE_NOT_FOUND = -32602


# ── Exception Classes ─────────────────────────────────────────────────


class HeaderMismatchError(McpError):
    """Raised when HTTP headers don't match the JSON-RPC request body."""

    def __init__(
        self,
        message: str = "Header/body mismatch",
        data: Optional[Any] = None,
    ):
        """Initialize with optional message and data."""
        super().__init__(ErrorData(code=HEADER_MISMATCH, message=message, data=data))


class MissingRequiredClientCapabilityError(McpError):
    """Raised when the client lacks a required capability."""

    def __init__(
        self,
        message: str = "Missing required client capability",
        data: Optional[Any] = None,
    ):
        """Initialize with optional message and data."""
        super().__init__(
            ErrorData(
                code=MISSING_REQUIRED_CLIENT_CAPABILITY, message=message, data=data
            )
        )


class UnsupportedProtocolVersionError(McpError):
    """Raised when the client requests an unsupported protocol version."""

    def __init__(
        self,
        message: str = "Unsupported protocol version",
        data: Optional[Any] = None,
    ):
        """Initialize with optional message and data."""
        super().__init__(
            ErrorData(code=UNSUPPORTED_PROTOCOL_VERSION, message=message, data=data)
        )


class ResourceNotFoundError(McpError):
    """Raised when a requested resource cannot be found."""

    def __init__(
        self,
        message: str = "Resource not found",
        data: Optional[Any] = None,
    ):
        """Initialize with optional message and data."""
        super().__init__(ErrorData(code=RESOURCE_NOT_FOUND, message=message, data=data))
