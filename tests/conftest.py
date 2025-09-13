"""Pytest configuration and shared fixtures for the test suite."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def clean_environment():
    """Fixture to provide a clean environment for testing."""
    # Store original environment
    original_env = dict(os.environ)
    
    # Clear MCP-related environment variables
    mcp_vars = [
        "MCP_HOST",
        "MCP_PORT", 
        "MCP_TRANSPORT_PROTOCOL",
        "MCP_SSL_KEYFILE",
        "MCP_SSL_CERTFILE",
        "PYTHON_LOG_LEVEL"
    ]
    
    for var in mcp_vars:
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_environment():
    """Fixture providing sample environment variables for testing."""
    return {
        "MCP_HOST": "localhost",
        "MCP_PORT": "8080",
        "MCP_TRANSPORT_PROTOCOL": "http",
        "MCP_SSL_KEYFILE": "/test/path/key.pem",
        "MCP_SSL_CERTFILE": "/test/path/cert.pem",
        "PYTHON_LOG_LEVEL": "DEBUG"
    }


@pytest.fixture
def mock_png_data():
    """Fixture providing mock PNG data for testing."""
    return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6'


@pytest.fixture
def sample_code():
    """Fixture providing sample code for testing."""
    return """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Calculate the 10th Fibonacci number
result = fibonacci(10)
print(f"The 10th Fibonacci number is: {result}")"""


@pytest.fixture
def temp_logo_file(tmp_path, mock_png_data):
    """Fixture creating a temporary logo file for testing."""
    logo_file = tmp_path / "test_logo.png"
    logo_file.write_bytes(mock_png_data)
    return logo_file


@pytest.fixture
def mock_fastmcp():
    """Fixture providing a mocked FastMCP instance."""
    with patch('template_mcp_server.src.mcp.FastMCP') as mock:
        mock_instance = mock.return_value
        mock_instance.tool.return_value = lambda x: x  # Identity function for tool decorator
        yield mock_instance


@pytest.fixture
def mock_logger():
    """Fixture providing a mocked logger."""
    with patch('template_mcp_server.src.mcp.logger') as mock:
        yield mock


@pytest.fixture(autouse=True)
def disable_logging():
    """Automatically disable logging for all tests to reduce noise."""
    with patch('template_mcp_server.utils.pylogger.get_python_logger'):
        yield


class TestDataProvider:
    """Test data provider class with common test data."""
    
    VALID_PORTS = [1024, 3000, 8080, 9000, 65535]
    INVALID_PORTS = [0, 1023, 65536, 99999]
    
    VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    INVALID_LOG_LEVELS = ["TRACE", "VERBOSE", "INVALID", ""]
    
    VALID_TRANSPORT_PROTOCOLS = ["http", "sse", "streamable-http"]
    INVALID_TRANSPORT_PROTOCOLS = ["websocket", "tcp", "invalid", ""]
    
    PROGRAMMING_LANGUAGES = [
        ("python", "def hello(): print('Hello')"),
        ("javascript", "function hello() { console.log('Hello'); }"),
        ("java", "public class Hello { public static void main(String[] args) { System.out.println('Hello'); } }"),
        ("go", "package main\nimport \"fmt\"\nfunc main() { fmt.Println('Hello') }"),
        ("rust", "fn main() { println!('Hello'); }"),
        ("c", "#include <stdio.h>\nint main() { printf('Hello'); return 0; }"),
        ("cpp", "#include <iostream>\nint main() { std::cout << 'Hello'; return 0; }"),
    ]
    
    NUMERIC_TEST_CASES = [
        # (a, b, expected_result)
        (0, 0, 0),
        (1, 1, 1),
        (5, 3, 15),
        (-2, -3, 6),
        (-4, 5, -20),
        (0.5, 2, 1.0),
        (1000000, 999999, 999999000000),
        (0.00001, 0.00002, 0.0000000002),
    ]
    
    INVALID_INPUTS = [
        "string",
        None,
        [],
        {},
        object(),
        "123abc",
        float('inf'),
        float('nan'),
    ]


@pytest.fixture
def test_data():
    """Fixture providing access to test data."""
    return TestDataProvider()


# Pytest markers for test categorization
pytest_plugins = []

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "network: mark test as requiring network access")


# Custom pytest collection modifications
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add automatic markers."""
    for item in items:
        # Add unit marker to all tests by default
        if not any(marker.name in ["integration", "slow", "network"] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)
        
        # Add slow marker to tests that might be slow
        if "large" in item.name or "performance" in item.name:
            item.add_marker(pytest.mark.slow)