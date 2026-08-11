"""SEP-2322: Multi Round-Trip Requests (MRTR) support.

Provides models and helpers for tools that need additional input
from the client before completing. Replaces the deprecated
elicitation/create pattern.
"""

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class InputRequest:
    """A request for additional input from the client."""

    request_id: str
    title: str
    description: str
    schema: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to camelCase dict for JSON-RPC response."""
        return {
            "requestId": self.request_id,
            "title": self.title,
            "description": self.description,
            "schema": self.schema,
        }


def make_input_request(
    title: str,
    description: str,
    schema: Dict[str, Any],
    request_id: Optional[str] = None,
) -> InputRequest:
    """Create an InputRequest with auto-generated ID if not provided."""
    return InputRequest(
        request_id=request_id or uuid.uuid4().hex[:12],
        title=title,
        description=description,
        schema=schema,
    )


def get_response_value(
    input_responses: List[Dict[str, Any]],
    request_id: str,
) -> Optional[Any]:
    """Get the value for a specific request ID from input responses."""
    for resp in input_responses:
        if resp.get("requestId") == request_id:
            return resp.get("value")
    return None


def input_required_result(
    input_requests: List[InputRequest],
    message: str = "Additional input required to proceed.",
) -> Dict[str, Any]:
    """Build a tools/call result indicating more input is needed."""
    return {
        "resultType": "input_required",
        "inputRequests": [r.to_dict() for r in input_requests],
        "content": [{"type": "text", "text": message}],
    }


def complete_result(
    structured_content: Dict[str, Any],
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a tools/call result for a completed call."""
    text = message or str(structured_content.get("message", "Tool call completed."))
    return {
        "resultType": "complete",
        "content": [{"type": "text", "text": text}],
        "structuredContent": structured_content,
    }
