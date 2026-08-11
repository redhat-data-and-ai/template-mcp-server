"""W3C Trace Context propagation for MCP requests (SEP-414).

Parses and generates W3C traceparent/tracestate headers, extracts trace
context from MCP _meta fields, and provides structlog integration.
"""

import os
import re
from typing import Any, Dict, Optional

TRACEPARENT_REGEX = re.compile(
    r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$"
)

TRACEPARENT_VERSION = "00"

META_TRACEPARENT = "io.modelcontextprotocol/traceparent"
META_TRACESTATE = "io.modelcontextprotocol/tracestate"
META_BAGGAGE = "io.modelcontextprotocol/baggage"


def parse_traceparent(value: str) -> Optional[Dict[str, str]]:
    """Parse a W3C traceparent header into its components.

    Returns None if the value is malformed or contains all-zero trace/span IDs.
    """
    match = TRACEPARENT_REGEX.match(value.strip())
    if not match:
        return None
    version, trace_id, parent_id, trace_flags = match.groups()
    if trace_id == "0" * 32 or parent_id == "0" * 16:
        return None
    return {
        "version": version,
        "trace_id": trace_id,
        "parent_id": parent_id,
        "trace_flags": trace_flags,
    }


def generate_span_id() -> str:
    """Generate a random 16-hex-char span ID."""
    return os.urandom(8).hex()


def generate_trace_id() -> str:
    """Generate a random 32-hex-char trace ID."""
    return os.urandom(16).hex()


def build_traceparent(trace_id: str, span_id: str, trace_flags: str = "01") -> str:
    """Build a W3C traceparent header value."""
    return f"{TRACEPARENT_VERSION}-{trace_id}-{span_id}-{trace_flags}"


def extract_trace_from_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Extract trace context from MCP _meta fields."""
    result: Dict[str, Any] = {}
    if META_TRACEPARENT in meta:
        parsed = parse_traceparent(str(meta[META_TRACEPARENT]))
        if parsed:
            result["traceparent"] = parsed
            result["raw_traceparent"] = meta[META_TRACEPARENT]
    if META_TRACESTATE in meta:
        result["tracestate"] = meta[META_TRACESTATE]
    if META_BAGGAGE in meta:
        result["baggage"] = meta[META_BAGGAGE]
    return result


def extract_trace_from_headers(headers: Any) -> Dict[str, Any]:
    """Extract W3C trace context from HTTP request headers."""
    result: Dict[str, Any] = {}
    traceparent = headers.get("traceparent")
    if traceparent:
        parsed = parse_traceparent(traceparent)
        if parsed:
            result["traceparent"] = parsed
            result["raw_traceparent"] = traceparent
    tracestate = headers.get("tracestate")
    if tracestate:
        result["tracestate"] = tracestate
    baggage = headers.get("baggage")
    if baggage:
        result["baggage"] = baggage
    return result


def trace_context_processor(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Structlog processor that injects trace context into log entries."""
    try:
        import structlog

        ctx = structlog.contextvars.get_contextvars()
        if "trace_id" in ctx:
            event_dict["trace_id"] = ctx["trace_id"]
        if "span_id" in ctx:
            event_dict["span_id"] = ctx["span_id"]
    except Exception:
        pass
    return event_dict
