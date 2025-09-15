"""Structured logger utility for the Template MCP server."""

import logging
import sys
from typing import Any, Dict, List, Set

import structlog

# HTTP clients
HTTP_CLIENT_LOGGERS = {
    "urllib3",
    "urllib3.connectionpool",
    "urllib3.util",
    "urllib3.util.retry",
    "requests",
    "httpx",
}

# AWS SDK
AWS_LOGGERS = {
    "botocore",
    "botocore.client",
    "botocore.credentials",
    "botocore.httpsession",
    "boto3",
    "boto3.resources",
}

# MCP (custom platform)
MCP_LOGGERS = {
    "fastmcp",
    "fastmcp.server",
    "fastmcp.server.http",
    "fastmcp.utilities",
    "fastmcp.utilities.logging",
    "fastmcp.client",
    "fastmcp.transports",
}

# ML/AI frameworks
ML_AI_LOGGERS = {
    "sentence_transformers",
    "transformers",
    "transformers.models",
    "transformers.tokenization_utils",
    "transformers.tokenization_utils_base",
    "transformers.configuration_utils",
    "transformers.modeling_utils",
    "huggingface_hub",
    "huggingface_hub.utils",
    "langchain_huggingface",
    "torch",
    "torch.nn",
}

# Observability / telemetry
OBSERVABILITY_LOGGERS = {
    "langfuse",
    "langfuse.client",
    "langfuse.api",
    "langfuse.callback",
}

# --- Aggregated Sets ---

THIRD_PARTY_LOGGERS: Set[str] = (
    HTTP_CLIENT_LOGGERS
    | AWS_LOGGERS
    | MCP_LOGGERS
    | ML_AI_LOGGERS
    | OBSERVABILITY_LOGGERS
)

ERROR_ONLY_LOGGERS: Set[str] = ML_AI_LOGGERS | OBSERVABILITY_LOGGERS

_LOGGING_CONFIGURED = False


# --- Internal helpers ---


def _clear_handlers(logger: logging.Logger) -> None:
    logger.handlers.clear()
    logger.filters.clear()


def _setup_logger(logger_name: str, level: str) -> None:
    logger = logging.getLogger(logger_name)
    _clear_handlers(logger)
    logger.setLevel(logging.ERROR if logger_name in ERROR_ONLY_LOGGERS else level)
    logger.propagate = True


def _configure_third_party_loggers(log_level: str) -> None:
    """Apply structured logging to selected third-party loggers."""
    logging.getLogger().handlers.clear()

    for name in THIRD_PARTY_LOGGERS:
        _setup_logger(name, log_level)


# --- Public API ---


def force_reconfigure_all_loggers(log_level: str = "INFO") -> None:
    """Force logger reconfiguration, even if already initialized."""
    global _LOGGING_CONFIGURED
    _LOGGING_CONFIGURED = False
    get_python_logger(log_level)


def get_python_logger(log_level: str = "INFO") -> structlog.BoundLogger:
    """Get a configured structlog logger."""
    global _LOGGING_CONFIGURED
    log_level = log_level.upper()

    if not _LOGGING_CONFIGURED:
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=log_level,
        )

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

        _LOGGING_CONFIGURED = True

    _configure_third_party_loggers(log_level)
    return structlog.get_logger()


def get_uvicorn_log_config(log_level: str = "INFO") -> Dict[str, Any]:
    """Return a Uvicorn-compatible logging config that integrates with structlog."""
    log_level = log_level.upper()
    default_formatter = {
        "()": "structlog.stdlib.ProcessorFormatter",
        "processor": structlog.processors.JSONRenderer(),
        "foreign_pre_chain": [
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ],
    }

    def make_logger_config(names: List[str], level: str) -> Dict[str, Any]:
        return {
            name: {
                "handlers": ["default"],
                "level": level,
                "propagate": False,
            }
            for name in names
        }

    # Base uvicorn loggers
    base_loggers = ["", "uvicorn", "uvicorn.error", "uvicorn.asgi", "uvicorn.protocols"]
    access_loggers = ["uvicorn.access"]

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": default_formatter,
            "access": default_formatter,
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            **make_logger_config(base_loggers, log_level),
            **make_logger_config(access_loggers, log_level),
            **make_logger_config(
                list(THIRD_PARTY_LOGGERS - ERROR_ONLY_LOGGERS), log_level
            ),
            **make_logger_config(list(ERROR_ONLY_LOGGERS), "ERROR"),
        },
    }
