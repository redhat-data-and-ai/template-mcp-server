# Your First Tool in 5 Minutes

Build and register a custom MCP tool from scratch. By the end you will have a working `greet_user` tool that any MCP client can discover and call.

> **Note:** The `greet_user` tool in this tutorial is a hands-on exercise for you to build. It is **not** included in the template — the template ships with `multiply_numbers`, `generate_code_review_prompt`, and `get_redhat_logo`. Follow along to learn the pattern, then delete or keep it as you wish.

**Prerequisites** -- the server runs locally:

```bash
uv venv && source .venv/bin/activate
uv pip install -e '.[dev]'
cp .env.example .env
```

---

## Step 1: Create the Tool File

Create `template_mcp_server/src/tools/greet_tool.py`:

```python
"""Greet tool for the Template MCP Server.

Returns a personalised greeting for the given name.
"""

from typing import Any, Dict

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


def greet_user(
    name: str,
) -> Dict[str, Any]:
    """Greet a user by name. Surface metadata lives in config/tools/greet_user.yaml."""
    try:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")

        greeting = f"Hello, {name.strip()}! Welcome to the MCP server."

        logger.info(f"Greet tool called for: {name}")

        return {
            "status": "success",
            "operation": "greet_user",
            "name": name.strip(),
            "greeting": greeting,
            "message": f"Successfully greeted {name.strip()}",
        }

    except Exception as e:
        logger.error(f"Error in greet tool: {e}")
        return {
            "status": "error",
            "operation": "greet_user",
            "error": str(e),
            "message": "Failed to generate greeting",
        }
```

**What is happening here:**

| Element | Why |
|---|---|
| `Dict[str, Any]` return | Every tool returns a structured dict so clients can parse results uniformly. |
| YAML config in `config/tools/` | Name, description, params, and agent metadata live in YAML — not in the handler docstring. |
| `try / except` wrapping | Tools must never raise. Return `{"status": "error", ...}` instead. |
| `logger` calls | Structured logging lets you trace tool invocations in production. |
| Input validation first | Fail fast with a clear message before doing any work. |

---

## Step 2: Add the Tool Config

Create `template_mcp_server/config/tools/greet_user.yaml`:

```yaml
name: greet_user
enabled: true
handler: template_mcp_server.src.tools.greet_tool:greet_user
display_name: Greet User
description: Return a greeting for the given name.
params:
  - name: name
    type: string
    required: true
    description: Name to greet
agent:
  usecase: Generate a friendly greeting for a person
  instructions: |
    1. Provide a non-empty name string
    2. Call the tool
    3. Receive the greeting
  input_description: "name (string): person to greet"
  output_description: Dictionary with status, operation, name, greeting, and message
  examples:
    - greet_user("Alice")
  prerequisites: none
  related_tools: []
```

The server loads this file at startup and registers the handler automatically. **No changes to `mcp.py` are required.**

**Why explicit `handler:`?** The YAML declares the tool surface; Python implements behavior. The `handler` field wires them together with a clear, reviewable import path.

---

## Step 3: Write a Test

Add a new test class to `tests/test_tools.py`:

```python
from template_mcp_server.src.tools.greet_tool import greet_user


class TestGreetTool:
    """Test the greet_user tool."""

    def test_greet_user_success(self):
        result = greet_user("Alice")
        assert result["status"] == "success"
        assert result["name"] == "Alice"
        assert "Hello, Alice!" in result["greeting"]

    def test_greet_user_strips_whitespace(self):
        result = greet_user("  Bob  ")
        assert result["status"] == "success"
        assert result["name"] == "Bob"

    def test_greet_user_empty_string(self):
        result = greet_user("")
        assert result["status"] == "error"
        assert "non-empty string" in result["error"]

    def test_greet_user_whitespace_only(self):
        result = greet_user("   ")
        assert result["status"] == "error"

    def test_greet_user_invalid_type(self):
        result = greet_user(42)
        assert result["status"] == "error"

    def test_greet_user_return_structure(self):
        result = greet_user("Test")
        assert isinstance(result, dict)
        for key in ("status", "operation", "name", "greeting", "message"):
            assert key in result
```

**Pattern**: Every test class mirrors the tool name. Arrange/Act/Assert. Cover the happy path, edge cases (whitespace, empty), and invalid types.

---

## Step 4: Run and Verify

```bash
# Run just your new tests
python -m pytest tests/test_tools.py::TestGreetTool -v

# Run the full suite to make sure nothing else broke
make test

# Start the server
template-mcp-server

# In another terminal -- list tools (SSE transport example)
curl http://localhost:5001/health
```

If using one of the [example clients](../examples/), the `greet_user` tool will appear in the tool list automatically.

---

## What You Just Learned

1. **Tool handler** -- one function per file in `template_mcp_server/src/tools/`.
2. **Tool config** -- one YAML file per tool in `template_mcp_server/config/tools/`.
3. **Testing** -- class in `test_tools.py` covering success, edge, and error paths.
4. **Convention** -- structured dict returns, metadata in YAML, input validation, logging.

## What's Next

| Topic | Link |
|---|---|
| Full architecture and tool patterns | [Architecture](architecture.md) |
| Async tools, OAuth, storage | [Development Guide](development.md) |
| Client examples (FastMCP, LangGraph) | [Examples](../examples/) |
| Tool documentation format reference | [Tools README](../template_mcp_server/src/tools/README.md) |
| Container and OpenShift deployment | [Deployment](deployment.md) |
