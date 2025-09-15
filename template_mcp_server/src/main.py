"""Main entry point for the Template MCP Server."""

import sys
from typing import NoReturn

import uvicorn

from template_mcp_server.src.api import app
from template_mcp_server.src.settings import settings
from template_mcp_server.src.settings import validate_config as validate_config_func
from template_mcp_server.utils.pylogger import get_python_logger, get_uvicorn_log_config

# Initialize logger
logger = get_python_logger()


def validate_config() -> None:
    """Validate configuration settings.

    Performs additional runtime validation of configuration values
    beyond what's done in the Config class initialization.

    Raises:
        ValueError: If required configuration values are missing or invalid.
        RuntimeError: If configuration is in an inconsistent state.
    """
    try:
        # Use the validate_config function from config.py
        validate_config_func(settings)

        # Additional validation specific to main.py
        # Validate host configuration
        if not settings.MCP_HOST:
            raise ValueError("MCP_HOST cannot be empty")

        logger.info("Configuration validation passed")

    except AttributeError as e:
        # Handle case where config object is not properly initialized
        raise RuntimeError(
            f"Configuration object is not properly initialized: {e}"
        ) from e
    except Exception as e:
        # Re-raise as ValueError for consistent error handling
        raise ValueError(f"Configuration validation failed: {e}") from e


def handle_startup_error(error: Exception, context: str = "server startup") -> NoReturn:
    """Handle startup errors with proper logging and exit codes.

    Args:
        error: The exception that occurred
        context: Context where the error occurred for better logging

    Raises:
        SystemExit: Always raises SystemExit with appropriate exit code
    """
    if isinstance(error, ValueError):
        # Configuration or validation errors
        logger.critical(f"Configuration error during {context}: {error}")
        sys.exit(1)
    elif isinstance(error, KeyboardInterrupt):
        # User interrupted the startup
        logger.info("Server startup interrupted by user")
        sys.exit(0)
    elif isinstance(error, PermissionError):
        # Permission issues (e.g., port binding)
        logger.critical(f"Permission error during {context}: {error}")
        sys.exit(1)
    elif isinstance(error, ConnectionError):
        # Network-related errors
        logger.critical(f"Connection error during {context}: {error}")
        sys.exit(1)
    else:
        # Unexpected errors
        logger.critical(f"Unexpected error during {context}: {error}", exc_info=True)
        sys.exit(1)


def main() -> None:
    """Main entry point for the MCP server.

    Initializes logging, loads configuration, and starts the Template MCP server.
    Handles graceful shutdown on keyboard interrupt and logs any startup errors.

    Raises:
        SystemExit: If the server fails to start due to configuration or other errors.
    """
    try:
        validate_config()

        logger.info(
            f"Server configured to use {settings.MCP_TRANSPORT_PROTOCOL} protocol"
        )

        uvicorn_config = {}
        if settings.MCP_SSL_KEYFILE and settings.MCP_SSL_CERTFILE:
            uvicorn_config["ssl_keyfile"] = settings.MCP_SSL_KEYFILE
            uvicorn_config["ssl_certfile"] = settings.MCP_SSL_CERTFILE
            logger.info(
                "Starting server with SSL",
                ssl_keyfile=settings.MCP_SSL_KEYFILE,
                ssl_certfile=settings.MCP_SSL_CERTFILE,
            )

        uvicorn.run(
            app,
            host=settings.MCP_HOST,
            port=settings.MCP_PORT,
            log_config=get_uvicorn_log_config(settings.PYTHON_LOG_LEVEL),
            **uvicorn_config,
        )

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
    except Exception as e:
        handle_startup_error(e, "server startup")
    finally:
        logger.info("Template MCP server shutting down")


def run() -> None:
    """Run the server with comprehensive error handling.

    Wraps the main function with additional error handling for graceful
    shutdown and proper exit codes. Provides a safety net for any
    unhandled exceptions.

    Raises:
        SystemExit: If the server fails to start or encounters critical errors.
    """
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        # This should rarely be reached due to handle_startup_error
        logger.error("Server failed to start", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run()
