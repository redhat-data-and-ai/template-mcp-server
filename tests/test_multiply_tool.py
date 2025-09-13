"""Test cases for the multiply tool."""

import pytest

from template_mcp_server.src.tools.multiply_tool import multiply_numbers


class TestMultiplyTool:
    """Test cases for the multiply_numbers function."""

    def test_multiply_positive_numbers(self):
        """Test multiplication of positive numbers."""
        result = multiply_numbers(5, 3)
        
        assert result["status"] == "success"
        assert result["operation"] == "multiplication"
        assert result["a"] == 5
        assert result["b"] == 3
        assert result["result"] == 15
        assert "Successfully multiplied" in result["message"]

    def test_multiply_negative_numbers(self):
        """Test multiplication of negative numbers."""
        result = multiply_numbers(-4, -2)
        
        assert result["status"] == "success"
        assert result["result"] == 8
        assert result["a"] == -4
        assert result["b"] == -2

    def test_multiply_by_zero(self):
        """Test multiplication by zero."""
        result = multiply_numbers(10, 0)
        
        assert result["status"] == "success"
        assert result["result"] == 0
        assert result["a"] == 10
        assert result["b"] == 0

    def test_multiply_decimal_numbers(self):
        """Test multiplication of decimal numbers."""
        result = multiply_numbers(2.5, 4.0)
        
        assert result["status"] == "success"
        assert result["result"] == 10.0
        assert result["a"] == 2.5
        assert result["b"] == 4.0

    def test_multiply_large_numbers(self):
        """Test multiplication of large numbers."""
        result = multiply_numbers(1000000, 999999)
        
        assert result["status"] == "success"
        assert result["result"] == 999999000000
        assert result["a"] == 1000000
        assert result["b"] == 999999

    def test_multiply_invalid_input_string(self):
        """Test multiplication with string input."""
        result = multiply_numbers("invalid", 5)
        
        assert result["status"] == "error"
        assert "error" in result
        assert "Failed to perform multiplication" in result["message"]

    def test_multiply_invalid_input_none(self):
        """Test multiplication with None input."""
        result = multiply_numbers(None, 5)
        
        assert result["status"] == "error"
        assert "error" in result
        assert "Failed to perform multiplication" in result["message"]

    def test_multiply_invalid_input_list(self):
        """Test multiplication with list input."""
        result = multiply_numbers([1, 2, 3], 5)
        
        assert result["status"] == "error"
        assert "error" in result
        assert "Failed to perform multiplication" in result["message"]

    def test_multiply_both_invalid_inputs(self):
        """Test multiplication with both invalid inputs."""
        result = multiply_numbers("invalid", "also_invalid")
        
        assert result["status"] == "error"
        assert "error" in result
        assert "Failed to perform multiplication" in result["message"]

    def test_multiply_edge_case_very_small_numbers(self):
        """Test multiplication of very small numbers."""
        result = multiply_numbers(0.00001, 0.00002)
        
        assert result["status"] == "success"
        assert abs(result["result"] - 0.0000000002) < 1e-15  # Use floating point tolerance
        assert result["a"] == 0.00001
        assert result["b"] == 0.00002

    def test_multiply_mixed_positive_negative(self):
        """Test multiplication of mixed positive and negative numbers."""
        result = multiply_numbers(-7, 3)
        
        assert result["status"] == "success"
        assert result["result"] == -21
        assert result["a"] == -7
        assert result["b"] == 3

    def test_multiply_integers_as_floats(self):
        """Test multiplication treating integers as floats."""
        result = multiply_numbers(int(6), int(7))
        
        assert result["status"] == "success"
        assert result["result"] == 42
        assert result["a"] == 6
        assert result["b"] == 7
        assert isinstance(result["result"], (int, float))