"""Tests for all MCP tools."""

import asyncio

# Import httpx at module level to capture the real module BEFORE the autouse
# mock_imports fixture in conftest.py replaces sys.modules['httpx'] with a Mock.
import httpx as _real_httpx
from unittest.mock import Mock, mock_open, patch

import pytest

from rfe_mcp_server.src.tools.code_review_tool import generate_code_review_prompt
from rfe_mcp_server.src.tools.multiply_tool import multiply_numbers
from rfe_mcp_server.src.tools.redhat_logo_tool import get_redhat_logo


class TestMultiplyTool:
    """Test the multiply_numbers tool."""

    def test_multiply_numbers_success(self):
        """Test successful multiplication of two numbers."""
        # Arrange
        a, b = 5.0, 3.0

        # Act
        result = multiply_numbers(a, b)

        # Assert
        assert result["status"] == "success"
        assert result["operation"] == "multiplication"
        assert result["a"] == 5.0
        assert result["b"] == 3.0
        assert result["result"] == 15.0
        assert result["message"] == "Successfully multiplied 5.0 and 3.0"

    def test_multiply_numbers_integers(self):
        """Test multiplication with integer inputs."""
        # Arrange
        a, b = 10, 7

        # Act
        result = multiply_numbers(a, b)

        # Assert
        assert result["status"] == "success"
        assert result["result"] == 70
        assert result["a"] == 10
        assert result["b"] == 7

    def test_multiply_numbers_negative_values(self):
        """Test multiplication with negative values."""
        # Arrange
        a, b = -5.0, 3.0

        # Act
        result = multiply_numbers(a, b)

        # Assert
        assert result["status"] == "success"
        assert result["result"] == -15.0

    def test_multiply_numbers_zero(self):
        """Test multiplication with zero."""
        # Arrange
        a, b = 10.0, 0.0

        # Act
        result = multiply_numbers(a, b)

        # Assert
        assert result["status"] == "success"
        assert result["result"] == 0.0

    def test_multiply_numbers_float_precision(self):
        """Test multiplication with floating point precision."""
        # Arrange
        a, b = 0.1, 0.2

        # Act
        result = multiply_numbers(a, b)

        # Assert
        assert result["status"] == "success"
        assert result["result"] == pytest.approx(0.02, rel=1e-10)

    def test_multiply_numbers_invalid_input_string(self):
        """Test multiplication with invalid string input."""
        # Arrange
        a, b = "5", 3.0

        # Act
        result = multiply_numbers(a, b)

        # Assert
        assert result["status"] == "error"
        assert "error" in result
        assert "Failed to perform multiplication" in result["message"]

    def test_multiply_numbers_invalid_input_none(self):
        """Test multiplication with None input."""
        # Arrange
        a, b = None, 3.0

        # Act
        result = multiply_numbers(a, b)

        # Assert
        assert result["status"] == "error"
        assert "error" in result
        assert "Failed to perform multiplication" in result["message"]

    def test_multiply_numbers_invalid_input_list(self):
        """Test multiplication with list input."""
        # Arrange
        a, b = [1, 2], 3.0

        # Act
        result = multiply_numbers(a, b)

        # Assert
        assert result["status"] == "error"
        assert "error" in result
        assert "Failed to perform multiplication" in result["message"]

    def test_multiply_numbers_both_invalid_inputs(self):
        """Test multiplication with both inputs invalid."""
        # Arrange
        a, b = "invalid", "also_invalid"

        # Act
        result = multiply_numbers(a, b)

        # Assert
        assert result["status"] == "error"
        assert "error" in result
        assert "Failed to perform multiplication" in result["message"]

    @patch("rfe_mcp_server.src.tools.multiply_tool.logger")
    def test_multiply_numbers_logging_success(self, mock_logger):
        """Test that successful multiplication is logged."""
        # Arrange
        a, b = 5.0, 3.0

        # Act
        multiply_numbers(a, b)

        # Assert
        mock_logger.info.assert_called_with("Multiply tool called: 5.0 * 3.0 = 15.0")

    @patch("rfe_mcp_server.src.tools.multiply_tool.logger")
    def test_multiply_numbers_logging_error(self, mock_logger):
        """Test that errors are logged."""
        # Arrange
        a, b = "invalid", 3.0

        # Act
        multiply_numbers(a, b)

        # Assert
        mock_logger.error.assert_called()

    def test_multiply_numbers_return_type(self):
        """Test that the function returns a dictionary."""
        # Arrange
        a, b = 5.0, 3.0

        # Act
        result = multiply_numbers(a, b)

        # Assert
        assert isinstance(result, dict)
        assert "status" in result
        assert "operation" in result
        assert "a" in result
        assert "b" in result
        assert "result" in result
        assert "message" in result

    def test_multiply_numbers_error_return_structure(self):
        """Test that error responses have the correct structure."""
        # Arrange
        a, b = "invalid", 3.0

        # Act
        result = multiply_numbers(a, b)

        # Assert
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "error" in result
        assert "message" in result
        assert "Failed to perform multiplication" in result["message"]

    def test_multiply_numbers_commutative_property(self):
        """Test that multiplication is commutative."""
        # Arrange
        a, b = 5.0, 3.0

        # Act
        result1 = multiply_numbers(a, b)
        result2 = multiply_numbers(b, a)

        # Assert
        assert result1["result"] == result2["result"]
        assert result1["status"] == "success"
        assert result2["status"] == "success"


class TestCodeReviewTool:
    """Test the code review tool functionality."""

    def test_generate_code_review_prompt_basic(self):
        """Test basic code review prompt generation."""
        # Arrange
        code = "def add(a, b): return a + b"
        language = "python"

        # Act
        result = asyncio.run(generate_code_review_prompt(code, language))

        # Assert
        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert result["operation"] == "code_review_prompt"
        assert result["language"] == language
        assert code in result["prompt"]
        assert language in result["prompt"]

    def test_generate_code_review_prompt_default_language(self):
        """Test code review prompt with default language."""
        # Arrange
        code = "function add(a, b) { return a + b; }"

        # Act
        result = asyncio.run(generate_code_review_prompt(code))

        # Assert
        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert result["language"] == "python"  # Default language
        assert code in result["prompt"]

    def test_generate_code_review_prompt_empty_code(self):
        """Test code review prompt with empty code."""
        # Arrange
        code = ""
        language = "python"

        # Act
        result = asyncio.run(generate_code_review_prompt(code, language))

        # Assert
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "Code must be a non-empty string" in result["error"]

    def test_generate_code_review_prompt_invalid_language(self):
        """Test code review prompt with invalid language."""
        # Arrange
        code = "def test(): pass"
        language = ""

        # Act
        result = asyncio.run(generate_code_review_prompt(code, language))

        # Assert
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "Language must be a non-empty string" in result["error"]

    def test_generate_code_review_prompt_content_structure(self):
        """Test that the prompt content has the expected structure."""
        # Arrange
        code = "def test_function(): pass"
        language = "python"

        # Act
        result = asyncio.run(generate_code_review_prompt(code, language))
        content = result["prompt"]

        # Assert
        assert result["status"] == "success"
        assert "Please review the following" in content
        assert f"```{language}" in content
        assert code in content
        assert "Focus on:" in content
        assert "Code quality and readability" in content
        assert "Potential bugs or issues" in content
        assert "Best practices" in content
        assert "Performance considerations" in content


class TestRedHatLogoTool:
    """Test the Red Hat logo tool functionality."""

    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_png_data")
    @patch("rfe_mcp_server.src.tools.redhat_logo_tool.Path")
    def test_get_redhat_logo_success(self, mock_path, mock_file):
        """Test successful reading of Red Hat logo."""
        # Arrange
        mock_path_instance = Mock()
        mock_path_instance.parent = Mock()
        mock_path_instance.parent.parent = Mock()  # Go up from tools to src
        assets_dir = Mock()
        assets_dir.__truediv__ = Mock(return_value=Mock())
        mock_path_instance.parent.parent.__truediv__ = Mock(return_value=assets_dir)
        mock_path.return_value = mock_path_instance

        # Act
        result = asyncio.run(get_redhat_logo())

        # Assert
        assert result["status"] == "success"
        assert result["operation"] == "get_redhat_logo"
        assert result["name"] == "Red Hat Logo"
        assert result["description"] == "Red Hat logo as base64 encoded PNG"
        assert result["mimeType"] == "image/png"
        assert isinstance(result["data"], str)
        assert len(result["data"]) > 0
        assert result["size_bytes"] == 13  # Length of b"fake_png_data"

    @patch("rfe_mcp_server.src.tools.redhat_logo_tool.Path")
    def test_get_redhat_logo_file_not_found(self, mock_path):
        """Test handling when logo file is not found."""
        # Arrange
        mock_path_instance = Mock()
        mock_path_instance.parent = Mock()
        mock_path_instance.parent.parent = Mock()
        assets_dir = Mock()
        logo_path = Mock()
        logo_path.__str__ = Mock(return_value="/path/to/logo.png")
        assets_dir.__truediv__ = Mock(return_value=logo_path)
        mock_path_instance.parent.parent.__truediv__ = Mock(return_value=assets_dir)
        mock_path.return_value = mock_path_instance

        # Configure open to raise FileNotFoundError
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            # Act
            result = asyncio.run(get_redhat_logo())

        # Assert
        assert result["status"] == "error"
        assert result["operation"] == "get_redhat_logo"
        assert result["error"] == "file_not_found"
        assert "Could not find logo file" in result["message"]

    @patch("rfe_mcp_server.src.tools.redhat_logo_tool.Path")
    def test_get_redhat_logo_permission_error(self, mock_path):
        """Test handling when logo file has permission issues."""
        # Arrange
        mock_path_instance = Mock()
        mock_path_instance.parent = Mock()
        mock_path_instance.parent.parent = Mock()
        assets_dir = Mock()
        logo_path = Mock()
        logo_path.__str__ = Mock(return_value="/path/to/logo.png")
        assets_dir.__truediv__ = Mock(return_value=logo_path)
        mock_path_instance.parent.parent.__truediv__ = Mock(return_value=assets_dir)
        mock_path.return_value = mock_path_instance

        # Configure open to raise PermissionError
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            # Act
            result = asyncio.run(get_redhat_logo())

        # Assert
        assert result["status"] == "error"
        assert result["operation"] == "get_redhat_logo"
        assert result["error"] == "permission_denied"
        assert "Permission denied reading logo file" in result["message"]


class TestRfeOpenRfesTool:
    """Tests for rfe_get_open_rfes_with_cases tool."""

    # ---------------------------------------------------------------------------
    # Helpers / fixtures
    # ---------------------------------------------------------------------------

    def _make_jira_page(self, issues, is_last=True, next_page_token=None):
        """Return a mock Jira search/jql response body.

        The /rest/api/3/search/jql endpoint uses cursor-based pagination
        (nextPageToken / isLast) rather than offset-based (startAt / total).
        """
        body: dict = {"issues": issues, "isLast": is_last}
        if next_page_token is not None:
            body["nextPageToken"] = next_page_token
        return body

    def _make_issue(
        self,
        key="RHEL-1",
        summary="Test RFE",
        status_name="In Progress",
        priority_name="Major",
        cf_value="abc123==",
    ):
        """Return a raw Jira issue dict with customfield_10978.

        customfield_10978 is returned as a plain string by this Jira instance,
        not as a {"value": ...} dict.
        """
        return {
            "key": key,
            "fields": {
                "summary": summary,
                "status": {"name": status_name},
                "priority": {"name": priority_name} if priority_name else None,
                "customfield_10978": cf_value,
            },
        }

    def _mock_client(self, responses):
        """
        Build a mock httpx.AsyncClient context manager that returns
        *responses* (list of MagicMock) in order for successive post() calls.
        """
        from unittest.mock import AsyncMock, MagicMock

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=responses)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        return ctx

    def _make_response(self, body, status_code=200):
        """Return a MagicMock response with the given JSON body and status code."""
        from unittest.mock import MagicMock

        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = body
        return resp

    def _patch_settings(self, monkeypatch, **kwargs):
        """Apply settings overrides via monkeypatch.

        Patch the settings object that the tool module itself holds a reference
        to. Importing via the tool module avoids a stale-reference problem that
        arises when test_basic.py's autouse fixture reloads
        rfe_mcp_server.src.settings, creating a new settings instance while the
        tool module retains a reference to the old one.
        """
        import rfe_mcp_server.src.tools.rfe_open_rfes_tool as _tool_mod

        defaults = {
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_USER_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_MAX_RESULTS": 500,
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            monkeypatch.setattr(_tool_mod.settings, k, v)

    # ---------------------------------------------------------------------------
    # Success paths
    # ---------------------------------------------------------------------------

    async def test_success_single_page(self, monkeypatch):
        """Single page of results returned correctly."""
        from unittest.mock import patch

        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch)
        issue = self._make_issue()
        page = self._make_jira_page([issue])
        ctx = self._mock_client([self._make_response(page)])

        with patch(
            "rfe_mcp_server.src.tools.rfe_open_rfes_tool.httpx.AsyncClient",
            return_value=ctx,
        ):
            result = await rfe_get_open_rfes_with_cases()

        assert result["status"] == "success"
        assert result["operation"] == "rfe_get_open_rfes_with_cases"
        assert result["total"] == 1
        assert len(result["issues"]) == 1
        issue_out = result["issues"][0]
        assert issue_out["id"] == "RHEL-1"
        assert issue_out["summary"] == "Test RFE"
        assert issue_out["status"] == "In Progress"
        assert issue_out["priority"] == "Major"
        assert issue_out["linked_cases_value"] == "abc123=="

    async def test_success_empty_result_set(self, monkeypatch):
        """Empty result set returns success with empty issues list."""
        from unittest.mock import patch

        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch)
        page = self._make_jira_page([])
        ctx = self._mock_client([self._make_response(page)])

        with patch(
            "rfe_mcp_server.src.tools.rfe_open_rfes_tool.httpx.AsyncClient",
            return_value=ctx,
        ):
            result = await rfe_get_open_rfes_with_cases()

        assert result["status"] == "success"
        assert result["total"] == 0
        assert result["issues"] == []
        assert "No open RHEL RFEs" in result["message"]

    async def test_priority_null(self, monkeypatch):
        """Issue with null priority returns priority=None in result."""
        from unittest.mock import patch

        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch)
        issue = self._make_issue(priority_name=None)
        page = self._make_jira_page([issue])
        ctx = self._mock_client([self._make_response(page)])

        with patch(
            "rfe_mcp_server.src.tools.rfe_open_rfes_tool.httpx.AsyncClient",
            return_value=ctx,
        ):
            result = await rfe_get_open_rfes_with_cases()

        assert result["status"] == "success"
        assert result["issues"][0]["priority"] is None

    async def test_pagination_multiple_pages(self, monkeypatch):
        """Tool fetches multiple pages when total exceeds page size."""
        from unittest.mock import patch

        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch)
        issues_p1 = [self._make_issue(key=f"RHEL-{i}") for i in range(50)]
        issues_p2 = [self._make_issue(key=f"RHEL-{i}") for i in range(50, 75)]
        page1 = self._make_jira_page(
            issues_p1, is_last=False, next_page_token="cursor-page2"
        )
        page2 = self._make_jira_page(issues_p2, is_last=True)
        ctx = self._mock_client(
            [self._make_response(page1), self._make_response(page2)]
        )

        with patch(
            "rfe_mcp_server.src.tools.rfe_open_rfes_tool.httpx.AsyncClient",
            return_value=ctx,
        ):
            result = await rfe_get_open_rfes_with_cases()

        assert result["status"] == "success"
        assert result["total"] == 75
        assert "Successfully retrieved 75" in result["message"]

    async def test_pagination_cap_applied(self, monkeypatch):
        """Results are capped at JIRA_MAX_RESULTS and a warning is included."""
        from unittest.mock import patch

        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch, JIRA_MAX_RESULTS=3)
        # Jira has more pages (isLast=False), but we cap at JIRA_MAX_RESULTS=3
        issues = [self._make_issue(key=f"RHEL-{i}") for i in range(50)]
        page = self._make_jira_page(
            issues[:50], is_last=False, next_page_token="cursor-p2"
        )
        ctx = self._mock_client([self._make_response(page)])

        with patch(
            "rfe_mcp_server.src.tools.rfe_open_rfes_tool.httpx.AsyncClient",
            return_value=ctx,
        ):
            result = await rfe_get_open_rfes_with_cases()

        assert result["status"] == "success"
        assert result["total"] == 3
        assert "capped" in result["message"].lower()
        assert "JIRA_MAX_RESULTS" in result["message"]

    # ---------------------------------------------------------------------------
    # Credential validation
    # ---------------------------------------------------------------------------

    async def test_missing_jira_base_url(self, monkeypatch):
        """Missing JIRA_BASE_URL returns structured error."""
        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch, JIRA_BASE_URL="")

        result = await rfe_get_open_rfes_with_cases()

        assert result["status"] == "error"
        assert result["total"] == 0
        assert result["issues"] == []
        assert "credentials not configured" in result["message"].lower()

    async def test_missing_jira_api_token(self, monkeypatch):
        """Missing JIRA_API_TOKEN returns structured error."""
        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch, JIRA_API_TOKEN="")

        result = await rfe_get_open_rfes_with_cases()

        assert result["status"] == "error"
        assert result["total"] == 0
        assert result["issues"] == []
        assert "credentials not configured" in result["message"].lower()

    # ---------------------------------------------------------------------------
    # HTTP error responses
    # ---------------------------------------------------------------------------

    async def test_http_401(self, monkeypatch):
        """HTTP 401 returns structured auth error."""
        from unittest.mock import patch

        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch)
        ctx = self._mock_client([self._make_response({}, status_code=401)])

        with patch(
            "rfe_mcp_server.src.tools.rfe_open_rfes_tool.httpx.AsyncClient",
            return_value=ctx,
        ):
            result = await rfe_get_open_rfes_with_cases()

        assert result["status"] == "error"
        assert result["total"] == 0
        assert result["issues"] == []
        assert "authentication failed" in result["message"].lower()
        assert "401" in result["message"]

    async def test_http_403(self, monkeypatch):
        """HTTP 403 returns structured auth error."""
        from unittest.mock import patch

        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch)
        ctx = self._mock_client([self._make_response({}, status_code=403)])

        with patch(
            "rfe_mcp_server.src.tools.rfe_open_rfes_tool.httpx.AsyncClient",
            return_value=ctx,
        ):
            result = await rfe_get_open_rfes_with_cases()

        assert result["status"] == "error"
        assert "authentication failed" in result["message"].lower()
        assert "403" in result["message"]

    async def test_http_500(self, monkeypatch):
        """HTTP 500 returns structured server error."""
        from unittest.mock import patch

        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch)
        ctx = self._mock_client([self._make_response({}, status_code=500)])

        with patch(
            "rfe_mcp_server.src.tools.rfe_open_rfes_tool.httpx.AsyncClient",
            return_value=ctx,
        ):
            result = await rfe_get_open_rfes_with_cases()

        assert result["status"] == "error"
        assert "server error" in result["message"].lower()
        assert "500" in result["message"]

    async def test_http_404(self, monkeypatch):
        """HTTP 4xx (non-401/403) returns structured request error."""
        from unittest.mock import patch

        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch)
        ctx = self._mock_client([self._make_response({}, status_code=404)])

        with patch(
            "rfe_mcp_server.src.tools.rfe_open_rfes_tool.httpx.AsyncClient",
            return_value=ctx,
        ):
            result = await rfe_get_open_rfes_with_cases()

        assert result["status"] == "error"
        assert "request failed" in result["message"].lower()
        assert "404" in result["message"]

    # ---------------------------------------------------------------------------
    # Network errors
    # ---------------------------------------------------------------------------

    async def test_network_error_no_exception_propagated(self, monkeypatch):
        """Network error is caught and returned as structured error.

        conftest.py has an autouse fixture that replaces sys.modules['httpx'] with
        a Mock() for every test. This means 'import httpx' inside a test returns a
        Mock, and rfe_open_rfes_tool.httpx is also the Mock (it was imported during
        test execution, after mock_imports activated). To work around this we:

        1. Use _real_httpx captured at module load time (before mock_imports fires).
        2. Use monkeypatch to temporarily restore _real_httpx as the tool module's
           httpx binding so that 'except httpx.RequestError' in the tool evaluates
           to a real exception class.
        3. Patch _real_httpx.AsyncClient via patch.object so the tool's HTTP call
           hits our mock instead of a real server.
        """
        from unittest.mock import AsyncMock, MagicMock

        import rfe_mcp_server.src.tools.rfe_open_rfes_tool as _tool_mod
        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch)

        # Restore real httpx in the tool module so except httpx.RequestError works.
        monkeypatch.setattr(_tool_mod, "httpx", _real_httpx)

        # Build a real httpx exception instance.
        connect_error = _real_httpx.ConnectError("Connection refused")

        async def raising_post(*args, **kwargs):
            raise connect_error

        mock_client = MagicMock()
        mock_client.post = raising_post

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        # Patch AsyncClient on the real httpx module so the call returns our mock.
        monkeypatch.setattr(_real_httpx, "AsyncClient", MagicMock(return_value=mock_cm))

        result = await rfe_get_open_rfes_with_cases()

        assert result["status"] == "error"
        assert result["total"] == 0
        assert result["issues"] == []
        assert "Failed to reach Jira" in result["message"]

    # ---------------------------------------------------------------------------
    # Invariants
    # ---------------------------------------------------------------------------

    async def test_return_type_and_required_keys_on_success(self, monkeypatch):
        """Success response always contains all required top-level keys."""
        from unittest.mock import patch

        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch)
        page = self._make_jira_page([self._make_issue()])
        ctx = self._mock_client([self._make_response(page)])

        with patch(
            "rfe_mcp_server.src.tools.rfe_open_rfes_tool.httpx.AsyncClient",
            return_value=ctx,
        ):
            result = await rfe_get_open_rfes_with_cases()

        assert isinstance(result, dict)
        for key in ("status", "operation", "total", "issues", "message"):
            assert key in result, f"Missing key: {key}"

    async def test_operation_field_invariant_on_error(self, monkeypatch):
        """operation field is always 'rfe_get_open_rfes_with_cases' on error paths."""
        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch, JIRA_BASE_URL="")
        result = await rfe_get_open_rfes_with_cases()

        assert result["operation"] == "rfe_get_open_rfes_with_cases"

    async def test_jql_sent_to_jira(self, monkeypatch):
        """The correct JQL string is included in the request payload."""
        from unittest.mock import patch

        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            _JQL,
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch)
        page = self._make_jira_page([])
        ctx = self._mock_client([self._make_response(page)])

        with patch(
            "rfe_mcp_server.src.tools.rfe_open_rfes_tool.httpx.AsyncClient",
            return_value=ctx,
        ) as MockClient:
            await rfe_get_open_rfes_with_cases()

        mock_client_instance = MockClient.return_value.__aenter__.return_value
        call_args = mock_client_instance.post.call_args
        payload = call_args.kwargs.get("json") or call_args.args[1]
        assert payload["jql"] == _JQL

    async def test_fields_list_sent_to_jira(self, monkeypatch):
        """The correct fields list is included in the request payload."""
        from unittest.mock import patch

        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            _FIELDS,
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch)
        page = self._make_jira_page([])
        ctx = self._mock_client([self._make_response(page)])

        with patch(
            "rfe_mcp_server.src.tools.rfe_open_rfes_tool.httpx.AsyncClient",
            return_value=ctx,
        ) as MockClient:
            await rfe_get_open_rfes_with_cases()

        mock_client_instance = MockClient.return_value.__aenter__.return_value
        call_args = mock_client_instance.post.call_args
        payload = call_args.kwargs.get("json") or call_args.args[1]
        assert payload["fields"] == _FIELDS

    async def test_linked_cases_value_passed_through_as_raw_string(self, monkeypatch):
        """linked_cases_value is the raw string from customfield_10978.value."""
        from unittest.mock import patch

        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch)
        raw_value = "FjFI4vRDXIGtYHewzEzZdb3f2WURpW1+"
        issue = self._make_issue(cf_value=raw_value)
        page = self._make_jira_page([issue])
        ctx = self._mock_client([self._make_response(page)])

        with patch(
            "rfe_mcp_server.src.tools.rfe_open_rfes_tool.httpx.AsyncClient",
            return_value=ctx,
        ):
            result = await rfe_get_open_rfes_with_cases()

        assert result["issues"][0]["linked_cases_value"] == raw_value

    # ---------------------------------------------------------------------------
    # Bearer auth fallback (no JIRA_USER_EMAIL)
    # ---------------------------------------------------------------------------

    async def test_bearer_auth_used_when_no_email(self, monkeypatch):
        """Bearer token header is used when JIRA_USER_EMAIL is empty."""
        from unittest.mock import patch

        from rfe_mcp_server.src.tools.rfe_open_rfes_tool import (
            rfe_get_open_rfes_with_cases,
        )

        self._patch_settings(monkeypatch, JIRA_USER_EMAIL="")
        page = self._make_jira_page([])
        ctx = self._mock_client([self._make_response(page)])

        with patch(
            "rfe_mcp_server.src.tools.rfe_open_rfes_tool.httpx.AsyncClient",
            return_value=ctx,
        ) as MockClient:
            result = await rfe_get_open_rfes_with_cases()

        assert result["status"] == "success"
        # Client should have been constructed with Bearer Authorization header
        init_kwargs = MockClient.call_args.kwargs
        assert "Authorization" in init_kwargs.get("headers", {})
        assert init_kwargs["headers"]["Authorization"].startswith("Bearer ")
