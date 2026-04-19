"""Email tool for the Template MCP Server.

This tool provides email sending functionality using the Resend API,
supporting HTML email content.
"""

import asyncio
import threading

from template_mcp_server.src.settings import settings
from template_mcp_server.utils.pylogger import get_python_logger

try:
    import resend
except ImportError:
    resend = None

logger = get_python_logger()

RETRY_DELAYS_SECONDS = (1, 2)

# Lock to prevent race conditions in multi-tenant setups when setting api_key
_resend_lock = threading.Lock()


def invoke_email_agent(email_id: str, subject: str, body: str) -> str:
    """Send an email using Resend.

    Args:
        email_id: The email address to send the email to
        subject: The subject of the email
        body: The HTML body of the email

    Returns:
        str: Status message indicating success or error
    """
    logger.info(
        "invoke_email_agent called",
        extra={
            "input": {
                "email_id": email_id,
                "subject": subject,
                "body_length": len(body),
            }
        },
    )

    try:
        # Validate API key
        api_key = settings.RESEND_API_KEY
        if not api_key:
            error_msg = "RESEND_API_KEY is not configured"
            logger.error(
                "API key validation failed",
                extra={"error": error_msg},
            )
            return f"Error sending email: {error_msg}"

        # Check if resend package is installed
        if resend is None:
            error_msg = "resend package is not installed"
            logger.error(
                "Package validation failed",
                extra={"error": error_msg},
            )
            return f"Error sending email: {error_msg}"

        # Get recipient email from settings or use provided email_id
        to_email = settings.RESEND_TO_EMAIL or email_id
        from_email = settings.RESEND_FROM_EMAIL or "Acme <onboarding@resend.dev>"

        # Prepare email parameters
        params = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": body,
        }

        logger.info(
            "Sending email via Resend API",
            extra={
                "email_params": {
                    "from": from_email,
                    "to": to_email,
                    "subject": subject,
                    "body_length": len(body),
                }
            },
        )

        # Thread-safe: use lock to prevent race conditions in multi-tenant setups
        with _resend_lock:
            resend.api_key = api_key
            response = resend.Emails.send(params)

        logger.info(
            "Email sent successfully",
            extra={
                "input": {"email_id": email_id, "subject": subject},
                "output": {"status": "success", "response": str(response)},
            },
        )
        return "Email sent successfully."

    except Exception as e:
        logger.exception(
            "Error sending email",
            extra={
                "input": {"email_id": email_id, "subject": subject},
                "error": str(e),
            },
        )
        return f"Error sending email: {e}"


async def send_email(email_id: str, subject: str, body: str) -> str:
    """Send emails through the organization's email system to recipients.

    This tool allows composing and sending emails with customized subject lines and content.
    The system automatically adds the sender's information and properly formats the email.

    I/O-bound operation - uses async for network requests.

    Usage guidelines:
    - Keep subject lines clear and concise
    - Ensure body content is professional and complete

    Limitations:
    - Cannot send attachments through this interface
    - Emails are sent from the system's default account

    Args:
        email_id: The email address to send the email to
        subject: The subject line of the email (required, max 255 characters)
                 Should be descriptive and relevant to the content
        body: The main HTML content of the email (required, max 1000 characters)
              Should include a proper greeting and signature

    Returns:
        str: A text string containing the email delivery status and confirmation
    """
    logger.info(
        "send_email invoked",
        extra={
            "input": {
                "email_id": email_id,
                "subject": subject,
                "body_length": len(body),
            }
        },
    )

    # Run the synchronous email send in an executor to avoid blocking
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None, invoke_email_agent, email_id, subject, body
    )

    logger.info(
        "send_email completed",
        extra={
            "input": {"email_id": email_id, "subject": subject},
            "output": {"response": response},
        },
    )

    logger.debug("send_email output", extra={"output": response})
    return response
