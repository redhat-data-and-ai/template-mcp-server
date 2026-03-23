"""Tests for all MCP tools."""

import asyncio
from unittest.mock import Mock, mock_open, patch

import pytest

from template_mcp_server.src.tools.multiply_tool import multiply_numbers


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

    @patch("template_mcp_server.src.tools.multiply_tool.logger")
    def test_multiply_numbers_logging_success(self, mock_logger):
        """Test that successful multiplication is logged."""
        # Arrange
        a, b = 5.0, 3.0

        # Act
        multiply_numbers(a, b)

        # Assert - Check that info was called with structured logging
        assert mock_logger.info.call_count >= 1
        # Verify the function was invoked with proper logging
        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any(
            "multiply_numbers invoked" in str(call)
            or "Multiplication completed successfully" in str(call)
            for call in calls
        )

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
