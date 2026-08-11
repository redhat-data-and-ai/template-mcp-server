"""Tests for MCP error codes and exception classes."""

import pytest
from mcp.shared.exceptions import McpError
from mcp.types import CONNECTION_CLOSED, ErrorData

from template_mcp_server.src.errors import (
    HEADER_MISMATCH,
    IMPL_DEFINED_RANGE_MAX,
    IMPL_DEFINED_RANGE_MIN,
    MCP_RESERVED_RANGE_MAX,
    MCP_RESERVED_RANGE_MIN,
    METHOD_NOT_SUPPORTED,
    MISSING_REQUIRED_CLIENT_CAPABILITY,
    RESOURCE_NOT_FOUND,
    UNSUPPORTED_PROTOCOL_VERSION,
    HeaderMismatchError,
    MethodNotSupportedError,
    MissingRequiredClientCapabilityError,
    ResourceNotFoundError,
    UnsupportedProtocolVersionError,
)


class TestAllocationRanges:
    """Test error code allocation range boundaries."""

    def test_impl_defined_range_bounds(self):
        assert IMPL_DEFINED_RANGE_MIN == -32019
        assert IMPL_DEFINED_RANGE_MAX == -32000

    def test_mcp_reserved_range_bounds(self):
        assert MCP_RESERVED_RANGE_MIN == -32099
        assert MCP_RESERVED_RANGE_MAX == -32020

    def test_ranges_are_non_overlapping(self):
        assert MCP_RESERVED_RANGE_MIN < IMPL_DEFINED_RANGE_MIN
        assert MCP_RESERVED_RANGE_MAX > IMPL_DEFINED_RANGE_MIN or (
            MCP_RESERVED_RANGE_MAX < IMPL_DEFINED_RANGE_MIN
        )
        impl_set = set(range(IMPL_DEFINED_RANGE_MIN, IMPL_DEFINED_RANGE_MAX + 1))
        mcp_set = set(range(MCP_RESERVED_RANGE_MIN, MCP_RESERVED_RANGE_MAX + 1))
        assert impl_set.isdisjoint(mcp_set)

    def test_sdk_connection_closed_in_impl_defined_range(self):
        assert IMPL_DEFINED_RANGE_MIN <= CONNECTION_CLOSED <= IMPL_DEFINED_RANGE_MAX


class TestErrorCodeValues:
    """Test that error code constants match the 2026-07-28 specification."""

    def test_header_mismatch_value(self):
        assert HEADER_MISMATCH == -32020

    def test_missing_required_client_capability_value(self):
        assert MISSING_REQUIRED_CLIENT_CAPABILITY == -32021

    def test_unsupported_protocol_version_value(self):
        assert UNSUPPORTED_PROTOCOL_VERSION == -32022

    def test_method_not_supported_value(self):
        assert METHOD_NOT_SUPPORTED == -32023

    def test_resource_not_found_value(self):
        assert RESOURCE_NOT_FOUND == -32602

    def test_mcp_reserved_codes_within_range(self):
        for code in (
            HEADER_MISMATCH,
            MISSING_REQUIRED_CLIENT_CAPABILITY,
            UNSUPPORTED_PROTOCOL_VERSION,
            METHOD_NOT_SUPPORTED,
        ):
            assert MCP_RESERVED_RANGE_MIN <= code <= MCP_RESERVED_RANGE_MAX

    def test_all_mcp_reserved_codes_are_unique(self):
        codes = [
            HEADER_MISMATCH,
            MISSING_REQUIRED_CLIENT_CAPABILITY,
            UNSUPPORTED_PROTOCOL_VERSION,
            METHOD_NOT_SUPPORTED,
        ]
        assert len(codes) == len(set(codes))


class TestHeaderMismatchError:
    """Test HeaderMismatchError exception class."""

    def test_default_message(self):
        err = HeaderMismatchError()
        assert err.error.code == HEADER_MISMATCH
        assert err.error.message == "Header/body mismatch"
        assert err.error.data is None

    def test_custom_message(self):
        msg = "Mcp-Method header does not match JSON-RPC method"
        err = HeaderMismatchError(message=msg)
        assert err.error.message == msg
        assert err.error.code == HEADER_MISMATCH

    def test_with_data(self):
        detail = {"header": "tools/call", "body": "tools/list"}
        err = HeaderMismatchError(data=detail)
        assert err.error.data == detail

    def test_extends_mcp_error(self):
        assert isinstance(HeaderMismatchError(), McpError)

    def test_str_matches_message(self):
        err = HeaderMismatchError(message="custom")
        assert str(err) == "custom"


class TestMissingRequiredClientCapabilityError:
    """Test MissingRequiredClientCapabilityError exception class."""

    def test_default_message(self):
        err = MissingRequiredClientCapabilityError()
        assert err.error.code == MISSING_REQUIRED_CLIENT_CAPABILITY
        assert err.error.message == "Missing required client capability"
        assert err.error.data is None

    def test_custom_message(self):
        msg = "Client does not support extensions"
        err = MissingRequiredClientCapabilityError(message=msg)
        assert err.error.message == msg
        assert err.error.code == MISSING_REQUIRED_CLIENT_CAPABILITY

    def test_with_data(self):
        detail = {"capability": "extensions", "required_by": "io.mcp/tasks"}
        err = MissingRequiredClientCapabilityError(data=detail)
        assert err.error.data == detail

    def test_extends_mcp_error(self):
        assert isinstance(MissingRequiredClientCapabilityError(), McpError)

    def test_str_matches_message(self):
        err = MissingRequiredClientCapabilityError(message="custom")
        assert str(err) == "custom"


class TestUnsupportedProtocolVersionError:
    """Test UnsupportedProtocolVersionError exception class."""

    def test_default_message(self):
        err = UnsupportedProtocolVersionError()
        assert err.error.code == UNSUPPORTED_PROTOCOL_VERSION
        assert err.error.message == "Unsupported protocol version"
        assert err.error.data is None

    def test_custom_message(self):
        msg = "Server requires protocol version 2026-07-28"
        err = UnsupportedProtocolVersionError(message=msg)
        assert err.error.message == msg
        assert err.error.code == UNSUPPORTED_PROTOCOL_VERSION

    def test_with_data(self):
        detail = {"requested": "2024-11-05", "supported": ["2026-07-28"]}
        err = UnsupportedProtocolVersionError(data=detail)
        assert err.error.data == detail

    def test_extends_mcp_error(self):
        assert isinstance(UnsupportedProtocolVersionError(), McpError)

    def test_str_matches_message(self):
        err = UnsupportedProtocolVersionError(message="custom")
        assert str(err) == "custom"


class TestMethodNotSupportedError:
    """Test MethodNotSupportedError exception class (SEP-2575)."""

    def test_default_message(self):
        err = MethodNotSupportedError()
        assert err.error.code == METHOD_NOT_SUPPORTED
        assert err.error.message == "Method not supported in stateless mode"
        assert err.error.data is None

    def test_custom_message(self):
        msg = "ping is not supported"
        err = MethodNotSupportedError(message=msg)
        assert err.error.message == msg
        assert err.error.code == METHOD_NOT_SUPPORTED

    def test_extends_mcp_error(self):
        assert isinstance(MethodNotSupportedError(), McpError)

    def test_str_matches_message(self):
        err = MethodNotSupportedError(message="custom")
        assert str(err) == "custom"


class TestResourceNotFoundError:
    """Test ResourceNotFoundError exception class."""

    def test_default_message(self):
        err = ResourceNotFoundError()
        assert err.error.code == RESOURCE_NOT_FOUND
        assert err.error.message == "Resource not found"
        assert err.error.data is None

    def test_custom_message(self):
        msg = "Resource file:///config.yaml not found"
        err = ResourceNotFoundError(message=msg)
        assert err.error.message == msg
        assert err.error.code == RESOURCE_NOT_FOUND

    def test_with_data(self):
        detail = {"uri": "file:///config.yaml"}
        err = ResourceNotFoundError(data=detail)
        assert err.error.data == detail

    def test_extends_mcp_error(self):
        assert isinstance(ResourceNotFoundError(), McpError)

    def test_str_matches_message(self):
        err = ResourceNotFoundError(message="custom")
        assert str(err) == "custom"


class TestErrorDataIntegration:
    """Test that exceptions produce valid ErrorData for JSON-RPC responses."""

    def test_error_data_is_serializable(self):
        err = HeaderMismatchError(
            message="mismatch",
            data={"expected": "tools/call", "got": "tools/list"},
        )
        dumped = err.error.model_dump()
        assert dumped["code"] == HEADER_MISMATCH
        assert dumped["message"] == "mismatch"
        assert dumped["data"]["expected"] == "tools/call"

    def test_all_errors_produce_distinct_codes(self):
        errors = [
            HeaderMismatchError(),
            MissingRequiredClientCapabilityError(),
            UnsupportedProtocolVersionError(),
            MethodNotSupportedError(),
            ResourceNotFoundError(),
        ]
        codes = [e.error.code for e in errors]
        assert len(codes) == len(set(codes))

    def test_catch_as_mcp_error(self):
        with pytest.raises(McpError) as exc_info:
            raise UnsupportedProtocolVersionError(message="v1 not supported")
        assert exc_info.value.error.code == UNSUPPORTED_PROTOCOL_VERSION

    def test_error_data_code_matches_constant(self):
        pairs = [
            (HeaderMismatchError, HEADER_MISMATCH),
            (MissingRequiredClientCapabilityError, MISSING_REQUIRED_CLIENT_CAPABILITY),
            (UnsupportedProtocolVersionError, UNSUPPORTED_PROTOCOL_VERSION),
            (MethodNotSupportedError, METHOD_NOT_SUPPORTED),
            (ResourceNotFoundError, RESOURCE_NOT_FOUND),
        ]
        for cls, expected_code in pairs:
            assert cls().error.code == expected_code
