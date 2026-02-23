"""Tests for all MCP tools."""

import asyncio
from unittest.mock import Mock, mock_open, patch

import pytest

from template_mcp_server.src.settings import settings
from template_mcp_server.src.tools.code_review_tool import generate_code_review_prompt
from template_mcp_server.src.tools.multiply_tool import multiply_numbers
from template_mcp_server.src.tools.redhat_logo_tool import get_redhat_logo
from template_mcp_server.utils.toon_utils import from_toon


def normalize_result(result):
    """Convert TOON format string to dict if needed for testing.

    This helper first verifies that the result type matches the ENABLE_TOON_FORMAT setting,
    then normalizes it to a dict for content assertions.

    Args:
        result: Either a TOON-formatted string or a dict

    Returns:
        dict: The normalized result as a dictionary

    Raises:
        AssertionError: If result type doesn't match ENABLE_TOON_FORMAT setting
    """
    if settings.ENABLE_TOON_FORMAT:
        # When flag is True, result should be a TOON string
        assert isinstance(result, str), (
            f"Expected TOON string when ENABLE_TOON_FORMAT=True, got {type(result).__name__}"
        )
        return from_toon(result)
    else:
        # When flag is False, result should be a dict
        assert isinstance(result, dict), (
            f"Expected dict when ENABLE_TOON_FORMAT=False, got {type(result).__name__}"
        )
        return result


class TestMultiplyTool:
    """Test the multiply_numbers tool."""

    def test_multiply_numbers_success(self):
        """Test successful multiplication of two numbers."""
        # Arrange
        a, b = 5.0, 3.0

        # Act
        result = normalize_result(multiply_numbers(a, b))

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
        result = normalize_result(multiply_numbers(a, b))

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
        result = normalize_result(multiply_numbers(a, b))

        # Assert
        assert result["status"] == "success"
        assert result["result"] == -15.0

    def test_multiply_numbers_zero(self):
        """Test multiplication with zero."""
        # Arrange
        a, b = 10.0, 0.0

        # Act
        result = normalize_result(multiply_numbers(a, b))

        # Assert
        assert result["status"] == "success"
        assert result["result"] == 0.0

    def test_multiply_numbers_float_precision(self):
        """Test multiplication with floating point precision."""
        # Arrange
        a, b = 0.1, 0.2

        # Act
        result = normalize_result(multiply_numbers(a, b))

        # Assert
        assert result["status"] == "success"
        assert result["result"] == pytest.approx(0.02, rel=1e-10)

    def test_multiply_numbers_invalid_input_string(self):
        """Test multiplication with invalid string input."""
        # Arrange
        a, b = "5", 3.0

        # Act
        result = normalize_result(multiply_numbers(a, b))

        # Assert
        assert result["status"] == "error"
        assert "error" in result
        assert "Failed to perform multiplication" in result["message"]

    def test_multiply_numbers_invalid_input_none(self):
        """Test multiplication with None input."""
        # Arrange
        a, b = None, 3.0

        # Act
        result = normalize_result(multiply_numbers(a, b))

        # Assert
        assert result["status"] == "error"
        assert "error" in result
        assert "Failed to perform multiplication" in result["message"]

    def test_multiply_numbers_invalid_input_list(self):
        """Test multiplication with list input."""
        # Arrange
        a, b = [1, 2], 3.0

        # Act
        result = normalize_result(multiply_numbers(a, b))

        # Assert
        assert result["status"] == "error"
        assert "error" in result
        assert "Failed to perform multiplication" in result["message"]

    def test_multiply_numbers_both_invalid_inputs(self):
        """Test multiplication with both inputs invalid."""
        # Arrange
        a, b = "invalid", "also_invalid"

        # Act
        result = normalize_result(multiply_numbers(a, b))

        # Assert
        assert result["status"] == "error"
        assert "error" in result
        assert "Failed to perform multiplication" in result["message"]

    @patch("template_mcp_server.src.tools.multiply_tool.logger")
    def test_multiply_numbers_logging_success(self, mock_logger):
        """Test that successful multiplication is logged."""
        # Arrange
        a, b = 5.0, 3.0

        # Act
        multiply_numbers(a, b)

        # Assert
        mock_logger.info.assert_called_with("Multiply tool called: 5.0 * 3.0 = 15.0")

    @patch("template_mcp_server.src.tools.multiply_tool.logger")
    def test_multiply_numbers_logging_error(self, mock_logger):
        """Test that errors are logged."""
        # Arrange
        a, b = "invalid", 3.0

        # Act
        multiply_numbers(a, b)

        # Assert
        mock_logger.error.assert_called()

    def test_multiply_numbers_return_type(self):
        """Test that the function returns a dictionary (or TOON string that converts to dict)."""
        # Arrange
        a, b = 5.0, 3.0

        # Act
        result = normalize_result(multiply_numbers(a, b))

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
        result = normalize_result(multiply_numbers(a, b))

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
        result1 = normalize_result(multiply_numbers(a, b))
        result2 = normalize_result(multiply_numbers(b, a))

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
        result = normalize_result(
            asyncio.run(generate_code_review_prompt(code, language))
        )

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
        result = normalize_result(asyncio.run(generate_code_review_prompt(code)))

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
        result = normalize_result(
            asyncio.run(generate_code_review_prompt(code, language))
        )

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
        result = normalize_result(
            asyncio.run(generate_code_review_prompt(code, language))
        )

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
        result = normalize_result(
            asyncio.run(generate_code_review_prompt(code, language))
        )
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
    @patch("template_mcp_server.src.tools.redhat_logo_tool.Path")
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
        result = normalize_result(asyncio.run(get_redhat_logo()))

        # Assert
        assert result["status"] == "success"
        assert result["operation"] == "get_redhat_logo"
        assert result["name"] == "Red Hat Logo"
        assert result["description"] == "Red Hat logo as base64 encoded PNG"
        assert result["mimeType"] == "image/png"
        assert isinstance(result["data"], str)
        assert len(result["data"]) > 0
        assert result["size_bytes"] == 13  # Length of b"fake_png_data"

    @patch("template_mcp_server.src.tools.redhat_logo_tool.Path")
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
            result = normalize_result(asyncio.run(get_redhat_logo()))

        # Assert
        assert result["status"] == "error"
        assert result["operation"] == "get_redhat_logo"
        assert result["error"] == "file_not_found"
        assert "Could not find logo file" in result["message"]

    @patch("template_mcp_server.src.tools.redhat_logo_tool.Path")
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
            result = normalize_result(asyncio.run(get_redhat_logo()))

        # Assert
        assert result["status"] == "error"
        assert result["operation"] == "get_redhat_logo"
        assert result["error"] == "permission_denied"
        assert "Permission denied reading logo file" in result["message"]
