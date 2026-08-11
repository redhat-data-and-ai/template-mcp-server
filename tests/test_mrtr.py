"""Tests for SEP-2322 MRTR module — 100% coverage."""

from template_mcp_server.src.mrtr import (
    InputRequest,
    complete_result,
    get_response_value,
    input_required_result,
    make_input_request,
)


class TestInputRequest:
    """Test InputRequest dataclass."""

    def test_fields(self):
        req = InputRequest(
            request_id="r1",
            title="Confirm",
            description="Confirm action?",
            schema={"type": "object"},
        )
        assert req.request_id == "r1"
        assert req.title == "Confirm"
        assert req.description == "Confirm action?"
        assert req.schema == {"type": "object"}

    def test_to_dict(self):
        req = InputRequest(
            request_id="r1",
            title="Confirm",
            description="Confirm action?",
            schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        )
        d = req.to_dict()
        assert d["requestId"] == "r1"
        assert d["title"] == "Confirm"
        assert d["description"] == "Confirm action?"
        assert d["schema"]["type"] == "object"
        assert "properties" in d["schema"]


class TestMakeInputRequest:
    """Test make_input_request factory."""

    def test_with_explicit_id(self):
        req = make_input_request(
            title="T",
            description="D",
            schema={"type": "string"},
            request_id="custom-id",
        )
        assert req.request_id == "custom-id"
        assert req.title == "T"

    def test_auto_generated_id(self):
        req = make_input_request(
            title="T",
            description="D",
            schema={"type": "string"},
        )
        assert len(req.request_id) == 12
        assert isinstance(req.request_id, str)

    def test_two_auto_ids_are_unique(self):
        r1 = make_input_request("T", "D", {"type": "string"})
        r2 = make_input_request("T", "D", {"type": "string"})
        assert r1.request_id != r2.request_id


class TestGetResponseValue:
    """Test get_response_value lookup."""

    def test_found(self):
        responses = [
            {"requestId": "a", "value": {"confirmed": True}},
            {"requestId": "b", "value": 42},
        ]
        assert get_response_value(responses, "a") == {"confirmed": True}
        assert get_response_value(responses, "b") == 42

    def test_not_found(self):
        responses = [{"requestId": "a", "value": 1}]
        assert get_response_value(responses, "missing") is None

    def test_empty_list(self):
        assert get_response_value([], "any") is None

    def test_missing_value_key(self):
        responses = [{"requestId": "a"}]
        assert get_response_value(responses, "a") is None


class TestInputRequiredResult:
    """Test input_required_result builder."""

    def test_basic(self):
        req = InputRequest("r1", "Title", "Desc", {"type": "object"})
        result = input_required_result([req])
        assert result["resultType"] == "input_required"
        assert len(result["inputRequests"]) == 1
        assert result["inputRequests"][0]["requestId"] == "r1"
        assert result["content"][0]["type"] == "text"
        assert result["content"][0]["text"] == "Additional input required to proceed."

    def test_custom_message(self):
        req = InputRequest("r1", "Title", "Desc", {"type": "object"})
        result = input_required_result([req], message="Please confirm.")
        assert result["content"][0]["text"] == "Please confirm."

    def test_multiple_requests(self):
        reqs = [
            InputRequest("r1", "T1", "D1", {"type": "string"}),
            InputRequest("r2", "T2", "D2", {"type": "boolean"}),
        ]
        result = input_required_result(reqs)
        assert len(result["inputRequests"]) == 2
        assert result["inputRequests"][0]["requestId"] == "r1"
        assert result["inputRequests"][1]["requestId"] == "r2"


class TestCompleteResult:
    """Test complete_result builder."""

    def test_with_message(self):
        result = complete_result(
            {"status": "ok", "data": 42},
            message="Done.",
        )
        assert result["resultType"] == "complete"
        assert result["content"][0]["text"] == "Done."
        assert result["structuredContent"]["status"] == "ok"
        assert result["structuredContent"]["data"] == 42

    def test_without_message_uses_structured_message(self):
        result = complete_result({"status": "ok", "message": "All good"})
        assert result["content"][0]["text"] == "All good"

    def test_without_message_or_structured_message(self):
        result = complete_result({"status": "ok"})
        assert result["content"][0]["text"] == "Tool call completed."
