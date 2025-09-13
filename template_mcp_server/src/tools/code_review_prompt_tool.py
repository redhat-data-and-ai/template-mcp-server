"""Code review prompt module for the Template MCP Server.

This module provides functionality to generate code review prompts
for various programming languages using the MCP prompt system.
"""

from typing import Any, Dict, List

from fastmcp import Context


def get_code_review_prompt(
    code: str, language: str = "python", context: Context = None
) -> List[Dict[str, Any]]:
    """Generate a code review prompt.

    Creates a structured prompt for code review that can be used with
    language models to analyze code quality, identify issues, and suggest
    improvements.

    Args:
        code: The source code to be reviewed.
        language: Programming language of the code (default: "python").
        context: MCP context for logging and capabilities (optional).

    Returns:
        List[Dict[str, Any]]: A list containing a single message dictionary
            with role "user" and content containing the formatted code review
            prompt.
    """
    if context:
        context.info(f"Generating code review prompt for {language} code")

    prompt_content = f"""Please review the following {language} code:

    ```{language}
    {code}
    ```

    Focus on:
    - Code quality and readability
    - Potential bugs or issues
    - Best practices
    - Performance considerations
    """

    return [{"role": "user", "content": prompt_content}]
