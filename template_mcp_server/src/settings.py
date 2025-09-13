"""Settings for the Template MCP Server."""

from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

from template_mcp_server.utils.pylogger import get_python_logger

# Initialize logger
logger = get_python_logger()

# Load environment variables with error handling
try:
    load_dotenv()
except Exception as e:
    # Log error but don't fail - environment variables might be set directly
    logger.warning(f"Could not load .env file: {e}")


class Settings(BaseSettings):
    """Configuration settings for the Template MCP Server.

    Uses Pydantic BaseSettings to load and validate configuration from environment variables.
    Provides default values for optional settings and validation for required ones.
    """

    MCP_HOST: str = Field(
        default="0.0.0.0",
        json_schema_extra={
            "env": "MCP_HOST",
            "description": "Host address for the MCP server",
            "example": "localhost",
        },
    )
    MCP_PORT: int = Field(
        default=3000,
        ge=1024,
        le=65535,
        json_schema_extra={
            "env": "MCP_PORT",
            "description": "Port number for the MCP server",
            "example": 3000,
        },
    )
    MCP_SSL_KEYFILE: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "MCP_SSL_KEYFILE",
            "description": "Path to SSL private key file for HTTPS",
            "example": "/path/to/key.pem",
        },
    )
    MCP_SSL_CERTFILE: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "MCP_SSL_CERTFILE",
            "description": "Path to SSL certificate file for HTTPS",
            "example": "/path/to/cert.pem",
        },
    )
    MCP_TRANSPORT_PROTOCOL: str = Field(
        default="streamable-http",
        json_schema_extra={
            "env": "MCP_TRANSPORT_PROTOCOL",
            "description": "Transport protocol for the MCP server",
            "example": "streamable-http",
            "enum": ["streamable-http", "sse", "http"],
        },
    )
    PYTHON_LOG_LEVEL: str = Field(
        default="INFO",
        json_schema_extra={
            "env": "PYTHON_LOG_LEVEL",
            "description": "Logging level for the application",
            "example": "INFO",
            "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        },
    )


def validate_config(settings: Settings) -> None:
    """Validate configuration settings.

    Performs validation to ensure required settings are present and values
    are within acceptable ranges.

    Args:
        settings: Settings instance to validate.

    Raises:
        ValueError: If required configuration is missing or invalid.
    """
    # Validate port range
    if not (1024 <= settings.MCP_PORT <= 65535):
        raise ValueError(
            f"MCP_PORT must be between 1024 and 65535, got {settings.MCP_PORT}"
        )

    # Validate log level
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if settings.PYTHON_LOG_LEVEL.upper() not in valid_log_levels:
        raise ValueError(
            f"PYTHON_LOG_LEVEL must be one of {valid_log_levels}, got {settings.PYTHON_LOG_LEVEL}"
        )

    # Validate transport protocol
    valid_transport_protocols = ["streamable-http", "sse", "http"]
    if settings.MCP_TRANSPORT_PROTOCOL not in valid_transport_protocols:
        raise ValueError(
            f"MCP_TRANSPORT_PROTOCOL must be one of {valid_transport_protocols}, got {settings.MCP_TRANSPORT_PROTOCOL}"
        )


# Create config instance without validation (validation happens in main.py)
settings = Settings()
