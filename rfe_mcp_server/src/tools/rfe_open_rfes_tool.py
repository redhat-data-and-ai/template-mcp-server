"""Open RHEL RFEs with linked customer cases tool for the RFE MCP Server.

Retrieves open RHEL Story-type issues from Jira Cloud that have at least one
linked customer case (customfield_10978), returning structured data for
internal Sales and Support users.
"""

from typing import Any, Dict, Optional

import httpx

from rfe_mcp_server.src.settings import settings
from rfe_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()

_JQL = (
    "project = RHEL AND cf[10978] is not EMPTY AND type = Story "
    'AND status IN ("In Progress", Integration, New, Planning, Refinement)'
)
_FIELDS = ["key", "summary", "status", "priority", "customfield_10978"]
_PAGE_SIZE = 50

_ERROR_RESPONSE_BASE: Dict[str, Any] = {
    "operation": "rfe_get_open_rfes_with_cases",
    "total": 0,
    "issues": [],
}


def _make_error(message: str) -> Dict[str, Any]:
    """Return a structured error response dict."""
    return {**_ERROR_RESPONSE_BASE, "status": "error", "message": message}


def _extract_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the required fields from a raw Jira issue dict."""
    fields = issue.get("fields") or {}
    priority_field = fields.get("priority")
    cf_raw = fields.get("customfield_10978")
    # customfield_10978 is returned as a plain string by this Jira instance
    if isinstance(cf_raw, dict):
        linked_cases_value = cf_raw.get("value")
    else:
        linked_cases_value = cf_raw
    return {
        "id": issue.get("key", ""),
        "summary": fields.get("summary", ""),
        "status": (fields.get("status") or {}).get("name", ""),
        "priority": priority_field.get("name") if priority_field else None,
        "linked_cases_value": linked_cases_value,
    }


async def rfe_get_open_rfes_with_cases() -> Dict[str, Any]:
    """Retrieve all open RHEL RFEs with linked customer cases from Jira Cloud.

    TOOL_NAME=rfe_get_open_rfes_with_cases
    DISPLAY_NAME=Get Open RHEL RFEs with Customer Cases
    USECASE=Retrieve open RHEL RFE Stories from Jira that have at least one linked customer case
    INSTRUCTIONS=1. Call this tool with no parameters, 2. Receive structured list of open RHEL RFEs that have linked customer cases
    INPUT_DESCRIPTION=No parameters. Returns all matching RFEs up to the JIRA_MAX_RESULTS environment variable limit (default 500).
    OUTPUT_DESCRIPTION=Dictionary with status, operation, total count, list of RFE records (id, summary, status, priority, linked_cases_value), and message.
    EXAMPLES=rfe_get_open_rfes_with_cases()
    PREREQUISITES=JIRA_BASE_URL and JIRA_API_TOKEN environment variables must be configured. JIRA_USER_EMAIL must be set when using Basic auth.
    RELATED_TOOLS=None

    I/O-bound operation — uses async def for HTTP calls to Jira Cloud.

    Queries Jira Cloud for RHEL Stories with non-done statuses that have a
    non-empty customfield_10978 (linked customer cases field). The JQL filter
    ensures that only issues with linked cases are returned; no app-layer
    filtering is required.

    Auth: if JIRA_USER_EMAIL is set, uses HTTP Basic auth (email:token),
    which is the standard Jira Cloud API token mechanism. If JIRA_USER_EMAIL
    is empty, falls back to Bearer token authentication.

    Results are capped at JIRA_MAX_RESULTS (default 500). Increase this
    environment variable if more results are needed.

    Returns:
        Dictionary containing:
            - status: "success" or "error"
            - operation: always "rfe_get_open_rfes_with_cases"
            - total: count of issues returned
            - issues: list of RFE records
            - message: human-readable summary or error description

        Each issue record contains:
            - id: Jira issue key (e.g. "RHEL-116409")
            - summary: issue title
            - status: Jira status name
            - priority: priority name or None
            - linked_cases_value: raw value of customfield_10978 (opaque string)
    """
    logger.info("rfe_get_open_rfes_with_cases invoked")

    if not settings.JIRA_BASE_URL or not settings.JIRA_API_TOKEN:
        logger.error("Jira credentials not configured")
        return _make_error(
            "Jira credentials not configured: JIRA_BASE_URL and JIRA_API_TOKEN must be set"
        )

    base_url = settings.JIRA_BASE_URL.rstrip("/")
    url = f"{base_url}/rest/api/3/search/jql"

    auth: Optional[httpx.BasicAuth] = None
    extra_headers: Dict[str, str] = {}
    if settings.JIRA_USER_EMAIL:
        auth = httpx.BasicAuth(settings.JIRA_USER_EMAIL, settings.JIRA_API_TOKEN)
    else:
        extra_headers["Authorization"] = f"Bearer {settings.JIRA_API_TOKEN}"

    all_issues: list[Dict[str, Any]] = []
    next_page_token: Optional[str] = None
    page_num = 0
    capped = False

    try:
        async with httpx.AsyncClient(headers=extra_headers) as client:
            while True:
                payload: Dict[str, Any] = {
                    "jql": _JQL,
                    "fields": _FIELDS,
                    "maxResults": _PAGE_SIZE,
                }
                # /rest/api/3/search/jql uses cursor-based pagination; startAt is not valid
                if next_page_token:
                    payload["nextPageToken"] = next_page_token

                logger.info(
                    f"Fetching Jira page {page_num} (nextPageToken={'set' if next_page_token else 'none'})"
                )
                response = await client.post(url, json=payload, auth=auth)

                if response.status_code in (401, 403):
                    logger.error(f"Jira authentication failed: {response.status_code}")
                    return _make_error(
                        f"Jira authentication failed: {response.status_code}"
                    )
                if response.status_code >= 500:
                    logger.error(f"Jira server error: {response.status_code}")
                    return _make_error(f"Jira server error: {response.status_code}")
                if response.status_code >= 400:
                    logger.error(
                        f"Jira request failed: {response.status_code} — {response.text}"
                    )
                    return _make_error(f"Jira request failed: {response.status_code}")

                data = response.json()
                page_issues = data.get("issues") or []
                is_last: bool = data.get("isLast", True)
                next_page_token = data.get("nextPageToken")
                all_issues.extend(_extract_issue(i) for i in page_issues)
                page_num += 1

                if len(all_issues) >= settings.JIRA_MAX_RESULTS:
                    if len(all_issues) > settings.JIRA_MAX_RESULTS:
                        all_issues = all_issues[: settings.JIRA_MAX_RESULTS]
                    if not is_last:
                        capped = True
                    break

                if is_last or not page_issues or not next_page_token:
                    break

    except httpx.RequestError as exc:
        exc_type = type(exc).__name__
        logger.error(f"Failed to reach Jira: {exc_type}: {exc}")
        return _make_error(f"Failed to reach Jira: {exc_type}")
    except Exception as exc:
        logger.error(f"Unexpected error in rfe_get_open_rfes_with_cases: {exc}")
        return _make_error(f"Unexpected error: {type(exc).__name__}")

    total = len(all_issues)
    logger.info(f"rfe_get_open_rfes_with_cases returning {total} issues")

    if total == 0:
        message = "No open RHEL RFEs with linked cases found"
    elif capped:
        message = (
            f"Results capped at JIRA_MAX_RESULTS ({settings.JIRA_MAX_RESULTS}). "
            "Increase JIRA_MAX_RESULTS to retrieve more."
        )
    else:
        message = (
            f"Successfully retrieved {total} open RHEL RFEs with linked customer cases"
        )

    return {
        "status": "success",
        "operation": "rfe_get_open_rfes_with_cases",
        "total": total,
        "issues": all_issues,
        "message": message,
    }
