"""Email validation tool for the Template MCP Server.

This tool validates email addresses using standard email format validation,
checking for proper structure and common format issues.
"""

import re
from typing import Any, Dict

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()

# RFC 5322 compliant email regex pattern (simplified)
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)


def validate_email(email: str) -> Dict[str, Any]:
    """Validate an email address format.

    This tool checks whether an email address follows standard email format conventions.
    It validates the structure, checks for common issues, and provides detailed feedback
    on the validation result.

    CPU-bound operation - uses def for computational tasks.

    Args:
        email: Email address to validate (e.g., "user@example.com")

    Returns:
        Dictionary containing validation result and details

    Raises:
        ValueError: If the email input is empty or invalid type
    """
    logger.info(
        "validate_email invoked",
        extra={"input": {"email": email}},
    )

    try:
        # Check if email is empty
        if not email or not email.strip():
            error_msg = "Email address cannot be empty"
            logger.error(
                "Empty email validation failed",
                extra={"error": error_msg},
            )
            raise ValueError(error_msg)

        # Trim whitespace
        email = email.strip()

        # Check length constraints
        if len(email) > 254:
            logger.info(
                "Email validation failed: too long",
                extra={
                    "input": {"email": email},
                    "output": {
                        "valid": False,
                        "reason": "Email too long (max 254 characters)",
                    },
                },
            )
            return {
                "status": "success",
                "operation": "email_validation",
                "email": email,
                "valid": False,
                "reason": "Email address exceeds maximum length of 254 characters",
                "message": "Invalid email format",
            }

        # Check for @ symbol
        if email.count("@") != 1:
            logger.info(
                "Email validation failed: invalid @ count",
                extra={
                    "input": {"email": email},
                    "output": {"valid": False, "reason": "Invalid @ symbol count"},
                },
            )
            return {
                "status": "success",
                "operation": "email_validation",
                "email": email,
                "valid": False,
                "reason": "Email must contain exactly one @ symbol",
                "message": "Invalid email format",
            }

        # Split into local and domain parts
        local, domain = email.rsplit("@", 1)

        # Validate local part length
        if len(local) == 0 or len(local) > 64:
            logger.info(
                "Email validation failed: invalid local part length",
                extra={
                    "input": {"email": email},
                    "output": {"valid": False, "reason": "Invalid local part length"},
                },
            )
            return {
                "status": "success",
                "operation": "email_validation",
                "email": email,
                "valid": False,
                "reason": "Local part (before @) must be 1-64 characters",
                "message": "Invalid email format",
            }

        # Validate domain part
        if len(domain) == 0 or len(domain) > 253:
            logger.info(
                "Email validation failed: invalid domain length",
                extra={
                    "input": {"email": email},
                    "output": {"valid": False, "reason": "Invalid domain length"},
                },
            )
            return {
                "status": "success",
                "operation": "email_validation",
                "email": email,
                "valid": False,
                "reason": "Domain part (after @) must be 1-253 characters",
                "message": "Invalid email format",
            }

        # Check for valid domain (must have at least one dot and valid TLD)
        if "." not in domain:
            logger.info(
                "Email validation failed: no domain extension",
                extra={
                    "input": {"email": email},
                    "output": {"valid": False, "reason": "No domain extension"},
                },
            )
            return {
                "status": "success",
                "operation": "email_validation",
                "email": email,
                "valid": False,
                "reason": "Domain must have a valid extension (e.g., .com, .org)",
                "message": "Invalid email format",
            }

        # Validate against regex pattern
        if not EMAIL_PATTERN.match(email):
            logger.info(
                "Email validation failed: pattern mismatch",
                extra={
                    "input": {"email": email},
                    "output": {"valid": False, "reason": "Pattern validation failed"},
                },
            )
            return {
                "status": "success",
                "operation": "email_validation",
                "email": email,
                "valid": False,
                "reason": "Email contains invalid characters or format",
                "message": "Invalid email format",
            }

        # Email is valid
        logger.info(
            "Email validation completed successfully",
            extra={
                "input": {"email": email},
                "output": {"valid": True},
            },
        )

        output = {
            "status": "success",
            "operation": "email_validation",
            "email": email,
            "valid": True,
            "reason": "Email format is valid",
            "message": f"Email '{email}' is valid",
        }

        logger.debug("validate_email output", extra={"output": output})
        return output

    except Exception as e:
        logger.exception(
            "Error in validate_email",
            extra={"input": {"email": email}, "error": str(e)},
        )
        error_output = {
            "status": "error",
            "error": str(e),
            "message": "Failed to validate email",
        }
        logger.debug("validate_email error output", extra={"output": error_output})
        return error_output
