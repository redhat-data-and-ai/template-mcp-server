# Contributing to Template MCP Server

Thank you for your interest in contributing! This guide explains the process for contributing to this project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Coding Standards](#coding-standards)
- [Adding New MCP Tools](#adding-new-mcp-tools)
- [Testing Requirements](#testing-requirements)
- [Getting Help](#getting-help)

## Getting Started

1. **Fork the repository** on GitHub.

2. **Clone your fork:**
   ```bash
   git clone https://github.com/<your-username>/template-mcp-server.git
   cd template-mcp-server
   ```

3. **Set up the development environment:**
   ```bash
   make install
   ```
   This creates a virtual environment, installs all dependencies (including dev), and sets up pre-commit hooks.

4. **Verify everything works:**
   ```bash
   make test
   make pre-commit
   ```

## Development Workflow

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** following the [Coding Standards](#coding-standards).

3. **Run quality checks locally:**
   ```bash
   make lint        # Check linting issues
   make format      # Auto-format code
   make test        # Run test suite
   make coverage    # Run tests with coverage report
   make pre-commit  # Run all pre-commit hooks
   ```

4. **Commit your changes** using [Conventional Commits](#commit-conventions).

5. **Push and open a Pull Request** against `main`.

## Commit Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for clear history and automated release notes.

### Format

```
<type>(<optional scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only changes |
| `style` | Code style (formatting, semicolons, etc.) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `build` | Changes to build system or dependencies |
| `ci` | Changes to CI configuration |
| `chore` | Other changes that don't modify src or test files |

### Examples

```
feat(tools): add weather forecast tool
fix(oauth): handle expired token refresh correctly
docs: update deployment instructions for OpenShift
test(tools): add edge case tests for multiply tool
ci: add dependabot configuration
```

## Pull Request Process

1. **Fill out the PR template completely.** The template includes a checklist; all items must be addressed.

2. **Ensure all CI checks pass:**
   - Pre-commit hooks (linting, formatting, type checking)
   - Test suite with coverage >= 80%
   - Security scanning (Bandit)

3. **Link related issues** using keywords: `Closes #123`, `Fixes #456`.

4. **Keep PRs focused.** One logical change per PR. If you find unrelated issues, open separate PRs.

5. **Respond to review feedback** promptly. Push fixes as new commits (don't force-push during review).

6. **Squash and merge** is the default merge strategy. Your PR title becomes the changelog entry, so make it clear and descriptive.

## Issue Guidelines

### Before Opening an Issue

- Search existing issues to avoid duplicates.
- Check the README and documentation for answers.

### Bug Reports

Use the **Bug Report** template. Include:
- Steps to reproduce
- Expected vs. actual behavior
- Environment details (OS, Python version, etc.)
- Logs or error messages

### Feature Requests

Use the **Feature Request** template. Include:
- Problem statement (what you're trying to solve)
- Proposed solution
- Alternatives considered

### Labels

Issues are automatically labeled by type. You can also add:
- `good first issue` - suitable for newcomers
- `help wanted` - looking for contributors
- `priority/high` - needs attention soon

## Coding Standards

### Python Style

- **PEP 8** compliance (enforced by Ruff)
- **Line length**: 88 characters (Ruff default)
- **Imports**: sorted by isort (via Ruff)
- **Quotes**: double quotes

### Type Annotations

Required for all public functions and methods:
```python
async def my_tool(param: str, count: int = 1) -> Dict[str, Any]:
    ...
```

### Documentation

Google-style docstrings for all public APIs:
```python
async def my_tool(param: str) -> Dict[str, Any]:
    """Short description of the tool.

    Args:
        param: Description of the parameter.

    Returns:
        Dict[str, Any]: Description of the return value.

    Raises:
        ValueError: When param is invalid.
    """
```

### Error Handling

- Use structured logging (`structlog`) for all log messages.
- Return error dictionaries with `status`, `error`, and `message` keys.
- Never expose internal errors to clients.

## Adding New MCP Tools

1. **Create the tool module** in `template_mcp_server/src/tools/`:
   ```python
   # template_mcp_server/src/tools/your_tool.py
   from typing import Any, Dict
   from template_mcp_server.utils.pylogger import get_python_logger

   logger = get_python_logger()

   async def your_tool_function(param: str) -> Dict[str, Any]:
       """Your tool description."""
       try:
           # Implementation
           return {"status": "success", "result": "value"}
       except Exception as e:
           logger.error(f"Error in your tool: {e}")
           return {"status": "error", "error": str(e)}
   ```

2. **Register in MCP server** (`template_mcp_server/src/mcp.py`):
   ```python
   from template_mcp_server.src.tools.your_tool import your_tool_function

   def _register_mcp_tools(self) -> None:
       # ... existing registrations ...
       self.mcp.tool()(your_tool_function)
   ```

3. **Add tests** in `tests/`:
   ```python
   # tests/test_your_tool.py
   import pytest
   from template_mcp_server.src.tools.your_tool import your_tool_function

   @pytest.mark.asyncio
   async def test_your_tool_success():
       result = await your_tool_function("test")
       assert result["status"] == "success"
   ```

4. **Update documentation** in `README.md` and `template_mcp_server/src/tools/README.md`.

## Testing Requirements

- All new code must have corresponding tests.
- Minimum **80% code coverage** is required.
- Tests must pass on Python 3.12 and 3.13.
- Use `pytest` with `pytest-asyncio` for async tests.
- Mock external dependencies; do not make real network calls in tests.

### Running Tests

```bash
make test              # Run all tests
make coverage          # Run with coverage report
pytest tests/ -v       # Verbose output
pytest tests/ -k name  # Run specific test by name
```

## Getting Help

- **Issues**: Open an issue for bugs or feature requests.
- **Discussions**: Use GitHub Discussions for questions and ideas.
- **Documentation**: Check the README and in-code documentation.

Thank you for contributing!
