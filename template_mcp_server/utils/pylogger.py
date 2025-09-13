"""Logger utility for the Template MCP server."""

import structlog


def get_python_logger(log_level="INFO"):
    """Get a structlog logger with the specified configuration.

    Sets up structured logging with structlog using JSON formatting and
    comprehensive log processors for production-ready logging.

    Args:
        log_level (str): Logging level (default: "INFO"). Will be converted to uppercase.

    Returns:
        structlog.BoundLogger: Configured structlog logger instance.

    Note:
        The logger is configured with the following processors:
        - Level filtering
        - Logger name addition
        - Log level addition
        - Positional arguments formatting
        - ISO timestamp formatting
        - Stack info rendering
        - Exception info formatting
        - Unicode decoding
        - JSON rendering
    """
    log_level = log_level.upper()

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()
