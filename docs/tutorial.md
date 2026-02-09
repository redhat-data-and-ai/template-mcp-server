# Your First Tool in 5 Minutes

Build and register a custom MCP tool from scratch. By the end you will have a working `greet_user` tool that any MCP client can discover and call.

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
    """Greet a user by name.

    TOOL_NAME=greet_user
    DISPLAY_NAME=User Greeting
    USECASE=Generate a personalised greeting for a given user name
    INSTRUCTIONS=1. Provide a name string, 2. Call function, 3. Receive greeting
    INPUT_DESCRIPTION=One parameter: name (non-empty string). Examples: "Alice", "Bob"
    OUTPUT_DESCRIPTION=Dictionary with status, operation, name, greeting, and message
    EXAMPLES=greet_user("Alice"), greet_user("Bob")
    PREREQUISITES=None - standalone operation
    RELATED_TOOLS=None

    CPU-bound operation - uses def for computational tasks.

    Args:
        name: The name of the person to greet.

    Returns:
        Dictionary containing the greeting result.

    Raises:
        ValueError: If name is empty or not a string.
    """
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
| Docstring metadata block | `TOOL_NAME`, `USECASE`, etc. are read by agents to decide *when* to call your tool. |
| `try / except` wrapping | Tools must never raise. Return `{"status": "error", ...}` instead. |
| `logger` calls | Structured logging lets you trace tool invocations in production. |
| Input validation first | Fail fast with a clear message before doing any work. |

---

## Step 2: Register the Tool

Open `template_mcp_server/src/mcp.py` and make two edits.

**Add the import** (with the other tool imports near the top):

```python
from template_mcp_server.src.tools.greet_tool import greet_user
```

**Register in `_register_mcp_tools`** (add one line):

```python
def _register_mcp_tools(self) -> None:
    self.mcp.tool()(multiply_numbers)
    self.mcp.tool()(generate_code_review_prompt)
    self.mcp.tool()(get_redhat_logo)
    self.mcp.tool()(greet_user)          # <-- new
```

**Why `self.mcp.tool()(fn)`?** FastMCP's `tool()` returns a decorator. Calling it with the function as the argument is equivalent to `@mcp.tool()` but lets you register functions imported from other modules without modifying them.

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

1. **Tool file** -- one function per file in `template_mcp_server/src/tools/`.
2. **Registration** -- two lines in `mcp.py`: one import, one `self.mcp.tool()()` call.
3. **Testing** -- class in `test_tools.py` covering success, edge, and error paths.
4. **Convention** -- structured dict returns, metadata docstrings, input validation, logging.

## What's Next

| Topic | Link |
|---|---|
| Full architecture and tool patterns | [Architecture](architecture.md) |
| Async tools, OAuth, storage | [Development Guide](development.md) |
| Client examples (FastMCP, LangGraph) | [Examples](../examples/) |
| Tool documentation format reference | [Tools README](../template_mcp_server/src/tools/README.md) |
| Container and OpenShift deployment | [Deployment](deployment.md) |
