"""Tests for the email tool — 100% coverage."""

import asyncio
import importlib
import sys
from unittest.mock import Mock, patch

from template_mcp_server.src.settings import settings
from template_mcp_server.src.tools.email_tool import invoke_email_agent, send_email


class TestResendImportGuard:
    """Cover lines 15-16: resend ImportError fallback."""

    def test_resend_set_to_none_when_not_installed(self):
        saved = sys.modules.pop("resend", None)
        saved_tool = sys.modules.pop("template_mcp_server.src.tools.email_tool", None)
        try:
            with patch.dict("sys.modules", {"resend": None}):
                mod = importlib.import_module(
                    "template_mcp_server.src.tools.email_tool"
                )
                assert mod.resend is None
        finally:
            if saved is not None:
                sys.modules["resend"] = saved
            if saved_tool is not None:
                sys.modules["template_mcp_server.src.tools.email_tool"] = saved_tool


class TestInvokeEmailAgent:
    """Test the synchronous invoke_email_agent function."""

    @patch.object(settings, "RESEND_API_KEY", "")
    def test_missing_api_key(self):
        result = invoke_email_agent("test@example.com", "Subject", "<p>Body</p>")
        assert "Error" in result
        assert "RESEND_API_KEY" in result

    @patch("template_mcp_server.src.tools.email_tool.resend", None)
    @patch.object(settings, "RESEND_API_KEY", "test-key")
    def test_resend_not_installed(self):
        result = invoke_email_agent("test@example.com", "Subject", "<p>Body</p>")
        assert "Error" in result
        assert "not installed" in result

    @patch.object(settings, "RESEND_FROM_EMAIL", "")
    @patch.object(settings, "RESEND_TO_EMAIL", "")
    @patch.object(settings, "RESEND_API_KEY", "test-key")
    def test_missing_from_email(self):
        mock_resend = Mock()
        with patch("template_mcp_server.src.tools.email_tool.resend", mock_resend):
            result = invoke_email_agent("test@example.com", "Subject", "<p>Body</p>")
            assert "Error" in result
            assert "RESEND_FROM_EMAIL" in result

    @patch.object(settings, "RESEND_FROM_EMAIL", "sender@example.com")
    @patch.object(settings, "RESEND_TO_EMAIL", "")
    @patch.object(settings, "RESEND_API_KEY", "test-key")
    def test_success(self):
        mock_resend = Mock()
        mock_resend.Emails.send.return_value = {"id": "abc123"}
        with patch("template_mcp_server.src.tools.email_tool.resend", mock_resend):
            result = invoke_email_agent("test@example.com", "Subject", "<p>Body</p>")
            assert result == "Email sent successfully."
            mock_resend.Emails.send.assert_called_once()

    @patch.object(settings, "RESEND_FROM_EMAIL", "sender@example.com")
    @patch.object(settings, "RESEND_TO_EMAIL", "override@example.com")
    @patch.object(settings, "RESEND_API_KEY", "test-key")
    def test_uses_to_email_setting_override(self):
        mock_resend = Mock()
        mock_resend.Emails.send.return_value = {"id": "abc123"}
        with patch("template_mcp_server.src.tools.email_tool.resend", mock_resend):
            invoke_email_agent("test@example.com", "Subject", "<p>Body</p>")
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["to"] == ["override@example.com"]

    @patch.object(settings, "RESEND_FROM_EMAIL", "sender@example.com")
    @patch.object(settings, "RESEND_TO_EMAIL", "")
    @patch.object(settings, "RESEND_API_KEY", "test-key")
    def test_api_exception(self):
        mock_resend = Mock()
        mock_resend.Emails.send.side_effect = Exception("API rate limit")
        with patch("template_mcp_server.src.tools.email_tool.resend", mock_resend):
            result = invoke_email_agent("test@example.com", "Subject", "<p>Body</p>")
            assert "Error" in result
            assert "API rate limit" in result


class TestSendEmail:
    """Test the async send_email wrapper."""

    @patch.object(settings, "RESEND_API_KEY", "")
    def test_send_email_delegates_to_invoke(self):
        result = asyncio.run(send_email("test@example.com", "Subject", "<p>Body</p>"))
        assert "Error" in result

    @patch.object(settings, "RESEND_FROM_EMAIL", "sender@example.com")
    @patch.object(settings, "RESEND_TO_EMAIL", "")
    @patch.object(settings, "RESEND_API_KEY", "test-key")
    def test_send_email_success(self):
        mock_resend = Mock()
        mock_resend.Emails.send.return_value = {"id": "ok"}
        with patch("template_mcp_server.src.tools.email_tool.resend", mock_resend):
            result = asyncio.run(send_email("to@example.com", "Hi", "<p>Hi</p>"))
            assert result == "Email sent successfully."
