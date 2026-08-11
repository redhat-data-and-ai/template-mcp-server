"""Tests for W3C Trace Context propagation (SEP-414)."""

import pytest

from template_mcp_server.src.tracing import (
    META_BAGGAGE,
    META_TRACEPARENT,
    META_TRACESTATE,
    TRACEPARENT_REGEX,
    TRACEPARENT_VERSION,
    build_traceparent,
    extract_trace_from_headers,
    extract_trace_from_meta,
    generate_span_id,
    generate_trace_id,
    parse_traceparent,
    trace_context_processor,
)


class TestParseTraceparent:
    """Test W3C traceparent header parsing."""

    def test_valid_traceparent(self):
        tp = "00-4bf92f3577b68a0d3c3e6e8e4a7e6c0f-00f067aa0ba902b7-01"
        result = parse_traceparent(tp)
        assert result is not None
        assert result["version"] == "00"
        assert result["trace_id"] == "4bf92f3577b68a0d3c3e6e8e4a7e6c0f"
        assert result["parent_id"] == "00f067aa0ba902b7"
        assert result["trace_flags"] == "01"

    def test_valid_traceparent_not_sampled(self):
        tp = "00-abcdef1234567890abcdef1234567890-1234567890abcdef-00"
        result = parse_traceparent(tp)
        assert result is not None
        assert result["trace_flags"] == "00"

    def test_invalid_format_returns_none(self):
        assert parse_traceparent("not-a-traceparent") is None

    def test_all_zero_trace_id_rejected(self):
        tp = "00-00000000000000000000000000000000-00f067aa0ba902b7-01"
        assert parse_traceparent(tp) is None

    def test_all_zero_parent_id_rejected(self):
        tp = "00-4bf92f3577b68a0d3c3e6e8e4a7e6c0f-0000000000000000-01"
        assert parse_traceparent(tp) is None

    def test_whitespace_stripped(self):
        tp = "  00-4bf92f3577b68a0d3c3e6e8e4a7e6c0f-00f067aa0ba902b7-01  "
        result = parse_traceparent(tp)
        assert result is not None

    def test_empty_string_returns_none(self):
        assert parse_traceparent("") is None

    def test_wrong_length_returns_none(self):
        assert parse_traceparent("00-abc-def-01") is None


class TestGenerateIds:
    """Test trace ID and span ID generation."""

    def test_span_id_length(self):
        span = generate_span_id()
        assert len(span) == 16
        assert all(c in "0123456789abcdef" for c in span)

    def test_trace_id_length(self):
        trace = generate_trace_id()
        assert len(trace) == 32
        assert all(c in "0123456789abcdef" for c in trace)

    def test_span_ids_are_unique(self):
        spans = {generate_span_id() for _ in range(100)}
        assert len(spans) == 100

    def test_trace_ids_are_unique(self):
        traces = {generate_trace_id() for _ in range(100)}
        assert len(traces) == 100


class TestBuildTraceparent:
    """Test traceparent header construction."""

    def test_builds_valid_traceparent(self):
        tp = build_traceparent(
            "4bf92f3577b68a0d3c3e6e8e4a7e6c0f",
            "00f067aa0ba902b7",
        )
        assert tp == "00-4bf92f3577b68a0d3c3e6e8e4a7e6c0f-00f067aa0ba902b7-01"

    def test_custom_trace_flags(self):
        tp = build_traceparent(
            "4bf92f3577b68a0d3c3e6e8e4a7e6c0f",
            "00f067aa0ba902b7",
            "00",
        )
        assert tp.endswith("-00")

    def test_roundtrip_parse_build(self):
        original = "00-4bf92f3577b68a0d3c3e6e8e4a7e6c0f-00f067aa0ba902b7-01"
        parsed = parse_traceparent(original)
        rebuilt = build_traceparent(
            parsed["trace_id"], parsed["parent_id"], parsed["trace_flags"]
        )
        assert rebuilt == original

    def test_uses_version_constant(self):
        tp = build_traceparent("a" * 32, "b" * 16)
        assert tp.startswith(TRACEPARENT_VERSION + "-")


class TestExtractTraceFromMeta:
    """Test trace context extraction from MCP _meta fields."""

    def test_extracts_traceparent(self):
        meta = {
            META_TRACEPARENT: "00-4bf92f3577b68a0d3c3e6e8e4a7e6c0f-00f067aa0ba902b7-01"
        }
        result = extract_trace_from_meta(meta)
        assert "traceparent" in result
        assert result["traceparent"]["trace_id"] == "4bf92f3577b68a0d3c3e6e8e4a7e6c0f"

    def test_extracts_tracestate(self):
        meta = {META_TRACESTATE: "vendor1=value1,vendor2=value2"}
        result = extract_trace_from_meta(meta)
        assert result["tracestate"] == "vendor1=value1,vendor2=value2"

    def test_extracts_baggage(self):
        meta = {META_BAGGAGE: "userId=alice,serverNode=node-1"}
        result = extract_trace_from_meta(meta)
        assert result["baggage"] == "userId=alice,serverNode=node-1"

    def test_empty_meta_returns_empty(self):
        assert extract_trace_from_meta({}) == {}

    def test_invalid_traceparent_skipped(self):
        meta = {META_TRACEPARENT: "invalid"}
        result = extract_trace_from_meta(meta)
        assert "traceparent" not in result

    def test_all_three_extracted(self):
        meta = {
            META_TRACEPARENT: "00-4bf92f3577b68a0d3c3e6e8e4a7e6c0f-00f067aa0ba902b7-01",
            META_TRACESTATE: "state=val",
            META_BAGGAGE: "key=val",
        }
        result = extract_trace_from_meta(meta)
        assert "traceparent" in result
        assert "tracestate" in result
        assert "baggage" in result


class TestExtractTraceFromHeaders:
    """Test trace context extraction from HTTP headers."""

    def test_extracts_traceparent_header(self):
        headers = {
            "traceparent": "00-4bf92f3577b68a0d3c3e6e8e4a7e6c0f-00f067aa0ba902b7-01"
        }
        result = extract_trace_from_headers(headers)
        assert "traceparent" in result

    def test_extracts_tracestate_header(self):
        headers = {"tracestate": "vendor=value"}
        result = extract_trace_from_headers(headers)
        assert result["tracestate"] == "vendor=value"

    def test_extracts_baggage_header(self):
        headers = {"baggage": "key=val"}
        result = extract_trace_from_headers(headers)
        assert result["baggage"] == "key=val"

    def test_empty_headers(self):
        assert extract_trace_from_headers({}) == {}

    def test_invalid_traceparent_skipped(self):
        headers = {"traceparent": "bad"}
        result = extract_trace_from_headers(headers)
        assert "traceparent" not in result


class TestTraceContextProcessor:
    """Test structlog trace context processor."""

    def test_adds_trace_id_when_present(self):
        from unittest.mock import MagicMock, patch

        mock_structlog = MagicMock()
        mock_structlog.contextvars.get_contextvars.return_value = {
            "trace_id": "abc123",
            "span_id": "def456",
        }
        with patch.dict(
            "sys.modules",
            {
                "structlog": mock_structlog,
                "structlog.contextvars": mock_structlog.contextvars,
            },
        ):
            event_dict = {"event": "test"}
            result = trace_context_processor(None, "info", event_dict)
            assert result["trace_id"] == "abc123"
            assert result["span_id"] == "def456"

    def test_no_context_no_fields_added(self):
        from unittest.mock import MagicMock, patch

        mock_structlog = MagicMock()
        mock_structlog.contextvars.get_contextvars.return_value = {}
        with patch.dict(
            "sys.modules",
            {
                "structlog": mock_structlog,
                "structlog.contextvars": mock_structlog.contextvars,
            },
        ):
            event_dict = {"event": "test"}
            result = trace_context_processor(None, "info", event_dict)
            assert "trace_id" not in result

    def test_handles_exception_gracefully(self):
        from unittest.mock import MagicMock, patch

        mock_structlog = MagicMock()
        mock_structlog.contextvars.get_contextvars.side_effect = RuntimeError(
            "no context"
        )
        with patch.dict(
            "sys.modules",
            {
                "structlog": mock_structlog,
                "structlog.contextvars": mock_structlog.contextvars,
            },
        ):
            event_dict = {"event": "test"}
            result = trace_context_processor(None, "info", event_dict)
            assert result == {"event": "test"}


class TestConstants:
    """Test module constants."""

    def test_traceparent_regex_matches_valid(self):
        assert TRACEPARENT_REGEX.match(
            "00-4bf92f3577b68a0d3c3e6e8e4a7e6c0f-00f067aa0ba902b7-01"
        )

    def test_meta_key_prefixes(self):
        assert META_TRACEPARENT == "io.modelcontextprotocol/traceparent"
        assert META_TRACESTATE == "io.modelcontextprotocol/tracestate"
        assert META_BAGGAGE == "io.modelcontextprotocol/baggage"

    def test_version_constant(self):
        assert TRACEPARENT_VERSION == "00"
