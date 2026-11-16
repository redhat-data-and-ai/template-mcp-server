# MCP Tools Config

Tool **surface** (name, description, parameters, agent metadata) lives here as YAML.
Tool **behavior** lives in `template_mcp_server/src/tools/` as Python handlers.

## Add a tool

1. Create a handler in `src/tools/your_tool.py`.
2. Copy [`tool_template.yaml.example`](tool_template.yaml.example) to `your_tool.yaml` and edit it (the `.yaml.example` suffix keeps it out of the `*.yaml` loader glob).
3. Restart the server (no changes to `mcp.py` required).

For a full walkthrough, see [docs/tutorial.md](../../../docs/tutorial.md).

## Example

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
  usecase: Generate a friendly greeting
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

## Override config path

Set `MCP_TOOLS_CONFIG_PATH` to mount an alternate directory (for example an OpenShift ConfigMap).
