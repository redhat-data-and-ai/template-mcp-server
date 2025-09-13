"""Test cases for the code review prompt tool."""

import pytest
from unittest.mock import Mock

from template_mcp_server.src.tools.code_review_prompt_tool import get_code_review_prompt


class TestCodeReviewPromptTool:
    """Test cases for the get_code_review_prompt function."""

    def test_basic_code_review_prompt(self):
        """Test basic code review prompt generation."""
        code = "def hello():\n    print('Hello, World!')"
        result = get_code_review_prompt(code)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert "python" in result[0]["content"].lower()
        assert code in result[0]["content"]
        assert "code quality" in result[0]["content"].lower()
        assert "readability" in result[0]["content"].lower()

    def test_code_review_prompt_with_language(self):
        """Test code review prompt with specified language."""
        code = "function hello() { console.log('Hello'); }"
        language = "javascript"
        result = get_code_review_prompt(code, language)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert language in result[0]["content"].lower()
        assert code in result[0]["content"]

    def test_code_review_prompt_different_languages(self):
        """Test code review prompt with different programming languages."""
        test_cases = [
            ("print('Hello')", "python"),
            ("console.log('Hello');", "javascript"),
            ("System.out.println('Hello');", "java"),
            ("fmt.Println('Hello')", "go"),
            ("puts 'Hello'", "ruby"),
            ("#include <stdio.h>", "c"),
            ("std::cout << 'Hello';", "cpp"),
        ]
        
        for code, language in test_cases:
            result = get_code_review_prompt(code, language)
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["role"] == "user"
            assert language in result[0]["content"].lower()
            assert code in result[0]["content"]

    def test_code_review_prompt_empty_code(self):
        """Test code review prompt with empty code."""
        result = get_code_review_prompt("")
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert "python" in result[0]["content"].lower()  # Default language
        assert "```python" in result[0]["content"]

    def test_code_review_prompt_multiline_code(self):
        """Test code review prompt with multiline code."""
        code = """def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

# Test the function
print(calculate_fibonacci(10))"""
        
        result = get_code_review_prompt(code)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert code in result[0]["content"]
        assert "def calculate_fibonacci" in result[0]["content"]

    def test_code_review_prompt_special_characters(self):
        """Test code review prompt with special characters in code."""
        code = "print('Hello \"World\"!\\n\\t@#$%^&*()')"
        result = get_code_review_prompt(code)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert code in result[0]["content"]

    def test_code_review_prompt_with_context(self):
        """Test code review prompt with MCP context."""
        mock_context = Mock()
        mock_context.info = Mock()
        
        code = "def test(): pass"
        language = "python"
        
        result = get_code_review_prompt(code, language, mock_context)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        
        # Verify context.info was called
        mock_context.info.assert_called_once_with(f"Generating code review prompt for {language} code")

    def test_code_review_prompt_without_context(self):
        """Test code review prompt without MCP context."""
        code = "def test(): pass"
        result = get_code_review_prompt(code, "python", None)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        # Should not raise any errors when context is None

    def test_code_review_prompt_content_structure(self):
        """Test that the prompt contains all expected sections."""
        code = "def example(): return True"
        result = get_code_review_prompt(code)
        
        content = result[0]["content"]
        
        # Check for all expected focus areas
        assert "code quality" in content.lower()
        assert "readability" in content.lower()
        assert "potential bugs" in content.lower()
        assert "best practices" in content.lower()
        assert "performance considerations" in content.lower()

    def test_code_review_prompt_markdown_formatting(self):
        """Test that the prompt uses proper markdown formatting."""
        code = "def test(): pass"
        language = "python"
        result = get_code_review_prompt(code, language)
        
        content = result[0]["content"]
        
        # Check for proper markdown code block formatting
        assert f"```{language}" in content
        assert "```" in content
        assert content.count("```") >= 2  # Opening and closing

    def test_code_review_prompt_large_code(self):
        """Test code review prompt with large code block."""
        # Generate a large code block
        code = "\n".join([f"def function_{i}():\n    return {i}" for i in range(100)])
        
        result = get_code_review_prompt(code)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert "function_0" in result[0]["content"]
        assert "function_99" in result[0]["content"]

    def test_code_review_prompt_case_insensitive_language(self):
        """Test that language parameter works with different cases."""
        code = "def test(): pass"
        
        for language in ["Python", "PYTHON", "PyThOn"]:
            result = get_code_review_prompt(code, language)
            assert isinstance(result, list)
            assert len(result) == 1
            assert language.lower() in result[0]["content"].lower()

    def test_code_review_prompt_unicode_code(self):
        """Test code review prompt with unicode characters in code."""
        code = "def greet():\n    print('Hello, 世界! 🌍')\n    return '感谢'"
        result = get_code_review_prompt(code)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert code in result[0]["content"]
        assert "世界" in result[0]["content"]
        assert "🌍" in result[0]["content"]

    def test_code_review_prompt_return_format(self):
        """Test that the return format is exactly as expected."""
        code = "test_code"
        result = get_code_review_prompt(code)
        
        # Verify exact structure
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert set(result[0].keys()) == {"role", "content"}
        assert result[0]["role"] == "user"
        assert isinstance(result[0]["content"], str)
        assert len(result[0]["content"]) > 0