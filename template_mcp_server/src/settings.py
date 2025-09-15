"""Settings for the Template MCP Server."""

from typing import List, Optional

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
        default="localhost",
        json_schema_extra={
            "env": "MCP_HOST",
            "description": "Host address for the MCP server",
            "example": "localhost",
        },
    )
    MCP_PORT: int = Field(
        default=8080,
        ge=1024,
        le=65535,
        json_schema_extra={
            "env": "MCP_PORT",
            "description": "Port number for the MCP server",
            "example": 8080,
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
        default="http",
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
    CORS_ENABLED: bool = Field(
        default=False,
        json_schema_extra={
            "env": "CORS_ENABLED",
            "description": "Enable CORS for the MCP server",
            "example": True,
        },
    )
    CORS_ORIGINS: List[str] = Field(
        default=["*"],
        json_schema_extra={
            "env": "CORS_ORIGINS",
            "description": "Origins allowed to access the MCP server",
            "example": ["*"],
        },
    )
    CORS_CREDENTIALS: bool = Field(
        default=True,
        json_schema_extra={
            "env": "CORS_CREDENTIALS",
            "description": "Allow credentials for CORS requests",
            "example": True,
        },
    )
    CORS_METHODS: List[str] = Field(
        default=["*"],
        json_schema_extra={
            "env": "CORS_METHODS",
            "description": "Methods allowed for CORS requests",
            "example": ["*"],
        },
    )
    CORS_HEADERS: List[str] = Field(
        default=["*"],
        json_schema_extra={
            "env": "CORS_HEADERS",
            "description": "Headers allowed for CORS requests",
            "example": ["*"],
        },
    )
    SSO_CLIENT_ID: str = Field(
        default="",
        json_schema_extra={
            "env": "SSO_CLIENT_ID",
            "description": "Client ID for the SSO",
            "example": "1234567890",
        },
    )
    SSO_CLIENT_SECRET: str = Field(
        default="",
        json_schema_extra={
            "env": "SSO_CLIENT_SECRET",
            "description": "Client secret for the SSO",
            "example": "1234567890",
        },
    )
    SSO_CALLBACK_URL: str = Field(
        default="",
        json_schema_extra={
            "env": "SSO_CALLBACK_URL",
            "description": "Callback URL for the SSO",
            "example": "http://localhost:3000/auth/callback",
        },
    )
    SSO_AUTHORIZATION_URL: str = Field(
        default="",
        json_schema_extra={
            "env": "SSO_AUTHORIZATION_URL",
            "description": "SSO authorization endpoint URL",
        },
    )
    SSO_TOKEN_URL: str = Field(
        default="",
        json_schema_extra={
            "env": "SSO_TOKEN_URL",
            "description": "SSO token endpoint URL",
        },
    )
    SSO_INTROSPECTION_URL: str = Field(
        default="",
        json_schema_extra={
            "env": "SSO_INTROSPECTION_URL",
            "description": "SSO token introspection endpoint URL",
        },
    )
    SESSION_SECRET: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "SESSION_SECRET",
            "description": "Secret key for session middleware (required in production)",
            "example": "your-super-secret-session-key-here",
            "sensitive": True,
        },
    )
    USE_EXTERNAL_BROWSER_AUTH: bool = Field(
        default=False,
        json_schema_extra={
            "env": "USE_EXTERNAL_BROWSER_AUTH",
            "description": "Whether the application is running in local development mode",
            "example": "true",
        },
    )

    # PostgreSQL Configuration
    POSTGRES_HOST: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "POSTGRES_HOST",
            "description": "PostgreSQL host address",
            "example": "localhost",
        },
    )
    POSTGRES_PORT: Optional[int] = Field(
        default=None,
        ge=1024,
        le=65535,
        json_schema_extra={
            "env": "POSTGRES_PORT",
            "description": "PostgreSQL port number",
            "example": 5432,
        },
    )
    POSTGRES_DB: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "POSTGRES_DB",
            "description": "PostgreSQL database name",
            "example": "template_mcp_server",
        },
    )
    POSTGRES_USER: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "POSTGRES_USER",
            "description": "PostgreSQL username",
            "example": "postgres",
        },
    )
    POSTGRES_PASSWORD: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "POSTGRES_PASSWORD",
            "description": "PostgreSQL password",
            "example": "secretpassword",
            "sensitive": True,
        },
    )
    POSTGRES_POOL_SIZE: int = Field(
        default=10,
        ge=1,
        le=100,
        json_schema_extra={
            "env": "POSTGRES_POOL_SIZE",
            "description": "PostgreSQL connection pool minimum size",
            "example": 10,
        },
    )
    POSTGRES_MAX_CONNECTIONS: int = Field(
        default=20,
        ge=1,
        le=200,
        json_schema_extra={
            "env": "POSTGRES_MAX_CONNECTIONS",
            "description": "PostgreSQL connection pool maximum size",
            "example": 20,
        },
    )
    MCP_HOST_ENDPOINT: str = Field(
        default="http://localhost:8080",
        json_schema_extra={
            "env": "MCP_HOST_ENDPOINT",
            "description": "Host endpoint for the MCP server",
            "example": "http://localhost:8080",
        },
    )
    ENVIRONMENT: str = Field(
        default="development",
        json_schema_extra={
            "env": "ENVIRONMENT",
            "description": "Environment for the MCP server",
            "example": "development",
        },
    )
    COMPATIBLE_WITH_CURSOR: bool = Field(
        default=False,
        json_schema_extra={
            "env": "COMPATIBLE_WITH_CURSOR",
            "description": "Whether the MCP server is compatible with Cursor OAuth2 flow",
            "example": True,
        },
    )
    ENABLE_AUTH: bool = Field(
        default=True,
        json_schema_extra={
            "env": "ENABLE_AUTH",
            "description": "Enable authentication for the MCP server",
            "example": "true",
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
