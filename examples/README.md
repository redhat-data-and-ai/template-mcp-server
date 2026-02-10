# MCP Client Examples

Ready-to-use client examples for connecting to your MCP server with different frameworks.

## 📁 **Client Examples**

- `fastmcp_client.py` - Direct FastMCP client connection
- `langgraph_client.py` - LangGraph integration with tool orchestration

## 🚀 **Quick Start**

### **1. FastMCP Client (Simple)**
```bash
# Install dependencies
uv pip install fastmcp httpx

# Run the example
python examples/fastmcp_client.py
```

**Use case**: Direct tool testing, simple integrations, debugging

### **2. LangGraph Client (Advanced)**
```bash
# Install dependencies
uv pip install langgraph httpx

# Run the example
python examples/langgraph_client.py
```

**Use case**: Complex workflows, agent orchestration, production systems

## 🔧 **Configuration**

**Update connection settings for your deployment:**

```python
# Both files - update these URLs
server_url = "http://localhost:5001"           # Local development
# server_url = "http://0.0.0.0:4001"          # Custom port
# server_url = "https://your-mcp.apps.cluster.com"  # Production OpenShift
```

## 📋 **What Each Example Shows**

### **FastMCP Client:**
- ✅ Basic server connection
- ✅ Tool discovery and listing
- ✅ Direct tool execution
- ✅ Error handling
- ✅ Response parsing

### **LangGraph Client:**
- ✅ Agent workflow orchestration
- ✅ Multi-tool coordination
- ✅ State management
- ✅ Complex business logic
- ✅ Production-ready patterns

## 🎯 **Customization for Your Domain**

**Update the examples with your tools:**

```python
# Replace template tool calls with your domain tools
# Instead of:
result = await client.call_tool("multiply_numbers", {"a": 5, "b": 3})

# Use your domain tools:
result = await client.call_tool("execute_domain_query", {
    "query_type": "performance_analysis",
    "parameters": {"quarter": "Q3", "region": "EMEA"}
})
```

## 🔍 **Testing Your Server**

```bash
# Test server health first
curl http://localhost:5001/health

# Run client examples to verify tool integration
python examples/fastmcp_client.py
python examples/langgraph_client.py
```

## 📚 **Learn More**

- **FastMCP**: Simple, direct MCP connections
- **LangGraph**: Advanced agent workflows and orchestration
- **MCP Protocol**: https://modelcontextprotocol.io/
