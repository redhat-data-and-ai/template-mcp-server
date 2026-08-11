"""Tests for the validate_email MCP tool and email sending tool."""

from unittest.mock import patch

from template_mcp_server.src.tools.validate_email_tool import validate_email


class TestValidateEmail:
    """Test the validate_email tool."""

    def test_valid_email_simple(self):
        """Valid simple email returns success."""
        result = validate_email("user@example.com")
        assert result["status"] == "success"
        assert result["valid"] is True
        assert result["email"] == "user@example.com"

    def test_valid_email_with_dots(self):
        """Valid email with dots in local part returns success."""
        result = validate_email("first.last@example.com")
        assert result["status"] == "success"
        assert result["valid"] is True

    def test_valid_email_with_subdomain(self):
        """Valid email with subdomain returns success."""
        result = validate_email("user@mail.example.com")
        assert result["status"] == "success"
        assert result["valid"] is True

    def test_valid_email_with_numbers(self):
        """Valid email with numbers returns success."""
        result = validate_email("user123@example456.com")
        assert result["status"] == "success"
        assert result["valid"] is True

    def test_valid_email_with_special_chars(self):
        """Valid email with allowed special characters returns success."""
        result = validate_email("user+tag@example.com")
        assert result["status"] == "success"
        assert result["valid"] is True

    def test_valid_email_with_hyphen(self):
        """Valid email with hyphen in domain returns success."""
        result = validate_email("user@my-domain.com")
        assert result["status"] == "success"
        assert result["valid"] is True

    def test_empty_email_returns_error(self):
        """Empty email returns error."""
        result = validate_email("")
        assert result["status"] == "error"

    def test_whitespace_only_email_returns_error(self):
        """Whitespace-only email returns error."""
        result = validate_email("   ")
        assert result["status"] == "error"

    def test_email_without_at_symbol(self):
        """Email without @ symbol returns invalid."""
        result = validate_email("userexample.com")
        assert result["status"] == "success"
        assert result["valid"] is False
        assert "@ symbol" in result["reason"]

    def test_email_with_multiple_at_symbols(self):
        """Email with multiple @ symbols returns invalid."""
        result = validate_email("user@@example.com")
        assert result["status"] == "success"
        assert result["valid"] is False
        assert "@ symbol" in result["reason"]

    def test_email_without_domain_extension(self):
        """Email without domain extension returns invalid."""
        result = validate_email("user@example")
        assert result["status"] == "success"
        assert result["valid"] is False
        assert "extension" in result["reason"]

    def test_email_too_long(self):
        """Email exceeding 254 characters returns invalid."""
        long_email = "a" * 250 + "@example.com"
        result = validate_email(long_email)
        assert result["status"] == "success"
        assert result["valid"] is False
        assert "length" in result["reason"]

    def test_email_local_part_too_long(self):
        """Email with local part exceeding 64 characters returns invalid."""
        long_local = "a" * 65 + "@example.com"
        result = validate_email(long_local)
        assert result["status"] == "success"
        assert result["valid"] is False
        assert "Local part" in result["reason"]

    def test_email_domain_too_long(self):
        """Email with domain exceeding 253 characters returns invalid."""
        long_domain = "user@" + "a" * 250 + ".com"
        result = validate_email(long_domain)
        assert result["status"] == "success"
        assert result["valid"] is False
        assert "length" in result["reason"]

    def test_email_with_spaces(self):
        """Email with spaces returns invalid."""
        result = validate_email("user name@example.com")
        assert result["status"] == "success"
        assert result["valid"] is False
        assert "invalid characters" in result["reason"]

    def test_email_starting_with_dot(self):
        """Email starting with dot - allowed by simplified regex."""
        result = validate_email(".user@example.com")
        assert result["status"] == "success"
        # Note: Simplified RFC 5322 regex allows this edge case
        assert result["valid"] is True

    def test_email_ending_with_dot(self):
        """Email ending with dot before @ - allowed by simplified regex."""
        result = validate_email("user.@example.com")
        assert result["status"] == "success"
        # Note: Simplified RFC 5322 regex allows this edge case
        assert result["valid"] is True

    def test_email_with_consecutive_dots(self):
        """Email with consecutive dots - allowed by simplified regex."""
        result = validate_email("user..name@example.com")
        assert result["status"] == "success"
        # Note: Simplified RFC 5322 regex allows this edge case
        assert result["valid"] is True

    def test_email_trims_whitespace(self):
        """Email with leading/trailing whitespace is trimmed and validated."""
        result = validate_email("  user@example.com  ")
        assert result["status"] == "success"
        assert result["valid"] is True
        assert result["email"] == "user@example.com"

    def test_non_string_input_returns_error(self):
        """Non-string input returns error."""
        result = validate_email(12345)
        assert result["status"] == "error"

    def test_none_input_returns_error(self):
        """None input returns error."""
        result = validate_email(None)
        assert result["status"] == "error"

    def test_email_missing_local_part(self):
        """Email missing local part returns invalid."""
        result = validate_email("@example.com")
        assert result["status"] == "success"
        assert result["valid"] is False
        assert "Local part" in result["reason"]

    def test_email_missing_domain(self):
        """Email missing domain returns invalid."""
        result = validate_email("user@")
        assert result["status"] == "success"
        assert result["valid"] is False
        assert "Domain" in result["reason"]

    def test_result_structure(self):
        """Verify the structure of successful validation result."""
        result = validate_email("test@example.com")
        assert "status" in result
        assert "operation" in result
        assert "email" in result
        assert "valid" in result
        assert "reason" in result
        assert "message" in result
        assert result["operation"] == "email_validation"


class TestEmailToolFromEmailValidation:
    """Test that RESEND_FROM_EMAIL is required (no hardcoded fallback)."""

    @patch("template_mcp_server.src.tools.email_tool.settings")
    def test_missing_from_email_returns_error(self, mock_settings):
        """Test that missing RESEND_FROM_EMAIL returns an error instead of using hardcoded fallback."""
        from template_mcp_server.src.tools.email_tool import invoke_email_agent

        mock_settings.RESEND_API_KEY = "test_api_key"
        mock_settings.RESEND_FROM_EMAIL = ""
        mock_settings.RESEND_TO_EMAIL = ""

        result = invoke_email_agent("user@example.com", "Test", "<p>Hello</p>")

        assert "Error" in result
        assert "RESEND_FROM_EMAIL" in result

    @patch("template_mcp_server.src.tools.email_tool.settings")
    def test_configured_from_email_is_used(self, mock_settings):
        """Test that configured RESEND_FROM_EMAIL is used when set."""
        from template_mcp_server.src.tools.email_tool import invoke_email_agent

        mock_settings.RESEND_API_KEY = "test_api_key"
        mock_settings.RESEND_FROM_EMAIL = "noreply@mycompany.com"
        mock_settings.RESEND_TO_EMAIL = ""

        with patch("template_mcp_server.src.tools.email_tool.resend") as mock_resend:
            mock_resend.Emails.send.return_value = {"id": "123"}
            result = invoke_email_agent("user@example.com", "Test", "<p>Hello</p>")

            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["from"] == "noreply@mycompany.com"
            assert "successfully" in result
