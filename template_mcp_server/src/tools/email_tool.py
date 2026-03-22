"""Email tool for the Template MCP Server.

This tool provides email sending functionality using the Resend API,
supporting HTML email content.
"""

import asyncio

from template_mcp_server.src.settings import settings
from template_mcp_server.utils.pylogger import get_python_logger

try:
    import resend
except ImportError:
    resend = None

logger = get_python_logger()

RETRY_DELAYS_SECONDS = (1, 2)


def invoke_email_agent(email_id: str, subject: str, body: str) -> str:
    """Send an email using Resend.

    Args:
        email_id: The email address to send the email to
        subject: The subject of the email
        body: The HTML body of the email

    Returns:
        str: Status message indicating success or error
    """
    try:
        # Validate API key
        api_key = settings.RESEND_API_KEY
        if not api_key:
            error_msg = "RESEND_API_KEY is not configured"
            logger.error(error_msg)
            return f"Error sending email: {error_msg}"

        # Check if resend package is installed
        if resend is None:
            error_msg = "resend package is not installed"
            logger.error(error_msg)
            return f"Error sending email: {error_msg}"

        # Set API key
        resend.api_key = api_key

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

        logger.info(f"Sending email with params: {params} to {email_id}")

        # Send the email
        resend.Emails.send(params)

        logger.info("Email sent successfully.")
        return "Email sent successfully."

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return f"Error sending email: {e}"


async def email_tool(email_id: str, subject: str, body: str) -> str:
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
    logger.info("Invoking Email Agent tool")
    logger.info(f"Email ID: {email_id}, Subject: {subject}, Body: {body}")

    # Run the synchronous email send in an executor to avoid blocking
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None, invoke_email_agent, email_id, subject, body
    )

    logger.info(f"Response: {response}")
    logger.info("Email Agent tool invoked")
    return response
