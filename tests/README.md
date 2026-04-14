# Test Suite

Comprehensive testing for MCP server reliability, security, and functionality.

## 📁 **Test Structure**

- `conftest.py` - Pytest configuration and shared fixtures
- `test_tools.py` - All MCP tools testing (core functionality)
- `test_mcp.py` - MCP server registration and protocol
- `test_api.py` - FastAPI endpoints and health checks
- `test_main.py` - Server startup and integration
- `test_settings.py` - Configuration and environment variables
- `test_utils.py` - Utility functions and logging
- `test_basic.py` - Basic functionality and imports
- `test_container.py` - Container builds and deployment testing

## 🚀 **Running Tests**

### **All Tests:**
```bash
# Run complete test suite
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov=rfe_mcp_server --cov-report=html
```

### **Specific Test Categories:**
```bash
# Test tools only (most important)
pytest tests/test_tools.py -v

# Test MCP integration
pytest tests/test_mcp.py -v

# Test API endpoints
pytest tests/test_api.py -v

# Test container builds
pytest tests/test_container.py -v
```

## 🔧 **Test Development**

### **Adding Tests for New Tools:**
```python
# tests/test_tools.py - Add your tool tests here

def test_your_new_tool():
    """Test your domain-specific tool."""
    # Test successful execution
    result = your_new_tool("valid_input")
    assert result["status"] == "success"
    assert "result" in result

    # Test error handling
    result = your_new_tool("")
    assert result["status"] == "error"
    assert "error" in result
```

### **Testing Tool Registration:**
```python
# tests/test_mcp.py - Verify tools are registered

def test_your_tool_registration(mcp_server):
    """Verify your tool is properly registered."""
    tools = mcp_server.mcp.list_tools()
    tool_names = [tool.name for tool in tools]
    assert "your_new_tool" in tool_names
```

## ✅ **Test Categories**

### **🔧 Unit Tests** - Individual component testing
- Tool functions with various inputs
- Error handling and edge cases
- Configuration validation
- Utility function behavior

### **🔗 Integration Tests** - Component interaction
- MCP server tool registration
- FastAPI endpoint responses
- Client-server communication
- Database connections (if applicable)

### **🐳 Container Tests** - Deployment validation
- Container image builds
- Security context verification
- Resource limit enforcement
- Health check functionality

### **📊 Performance Tests** - Load and efficiency
- Response time benchmarks
- Memory usage monitoring
- Concurrent request handling
- Tool execution efficiency

## 🎯 **Test Quality Standards**

✅ **Coverage**: Aim for 90%+ code coverage
✅ **Speed**: Individual tests < 1 second
✅ **Isolation**: Tests don't depend on each other
✅ **Clarity**: Clear test names and assertions
✅ **Reliability**: Tests pass consistently

## 🐛 **Debugging Failed Tests**

```bash
# Run with detailed output
pytest tests/test_tools.py::test_specific_function -v -s

# Drop into debugger on failure
pytest tests/test_tools.py --pdb

# Show print statements
pytest tests/test_tools.py -s
```

## 📋 **Pre-Deployment Checklist**

- [ ] All tests pass: `pytest`
- [ ] Coverage adequate: `pytest --cov`
- [ ] Container builds: `pytest tests/test_container.py`
- [ ] No lint errors: `pre-commit run --all-files`
- [ ] Examples work: `python examples/fastmcp_client.py`
