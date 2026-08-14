# MCP Tools Directory

Handlers implement tool **behavior**. Tool **surface** (name, description, params, agent metadata) lives in [`../../config/tools/`](../../config/tools/).

## Add a tool

1. Create a handler module in this directory (one function per file).
2. Add a YAML file in `template_mcp_server/config/tools/` with an explicit `handler:` reference.
3. Add tests in `tests/test_tools.py`.
4. Restart the server — **no changes to `mcp.py` required**.

## Handler guidelines

```python
def your_tool_function(
    input_param: str,
    optional_param: str = "default",
) -> Dict[str, Any]:
    """Short developer note. Agent metadata lives in config/tools/your_tool.yaml."""
    try:
        if not input_param:
            raise ValueError("input_param is required")

        result = process_input(input_param, optional_param)

        return {
            "status": "success",
            "operation": "your_operation",
            "result": result,
            "message": "Operation completed successfully",
        }

    except Exception as e:
        return {
            "status": "error",
            "operation": "your_operation",
            "error": str(e),
            "message": "Operation failed",
        }
```

## YAML config example

```yaml
name: your_tool_function
enabled: true
handler: template_mcp_server.src.tools.your_tool:your_tool_function
display_name: Human-Readable Tool Name
description: What the tool does.
params:
  - name: input_param
    type: string
    required: true
    description: Primary input
  - name: optional_param
    type: string
    required: false
    default: default
    description: Optional input
agent:
  usecase: When/why to use this tool
  instructions: |
    1. Provide input
    2. Call the tool
    3. Read the structured response
  input_description: Expected data format with examples
  output_description: What format you'll receive back
  examples:
    - your_tool_function("example_input")
  prerequisites: none
  related_tools: []
```

## Current tools

| Config | Handler |
|--------|---------|
| `multiply_numbers.yaml` | `multiply_tool.py` |
| `generate_code_review_prompt.yaml` | `code_review_tool.py` |
| `get_redhat_logo.yaml` | `redhat_logo_tool.py` |

## Best practices

1. **Consistent returns**: Always return `Dict[str, Any]` with a `status` field.
2. **Error handling**: Wrap in try/except; return structured errors (do not raise to clients).
3. **Input validation**: Validate inputs before processing.
4. **Logging**: Use `from template_mcp_server.utils.pylogger import get_python_logger`.
5. **Testing**: Add tests to `tests/test_tools.py` and loader tests to `tests/test_tools_loader.py`.

## Agent-friendly tips

- Use **clear, action-oriented names** (`generate_report` not `report_generator`).
- Put **concrete examples** in YAML `agent.examples`.
- Specify **prerequisites** and **related_tools** in YAML for workflow guidance.
- Keep **error messages** descriptive but concise.
