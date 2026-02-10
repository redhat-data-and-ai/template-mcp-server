# Development Guide

## Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) (fast Python package installer and resolver)

## Setup

1. **Install uv (if not already installed):**
   ```bash
   # On macOS/Linux:
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # On MacOS using brew
   brew install uv

   # On Windows:
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

   # Or with pip:
   pip install uv
   ```

2. **Clone the repository:**
   ```bash
   git clone https://github.com/redhat-data-and-ai/template-mcp-server
   cd template-mcp-server
   ```

3. **Create and activate a virtual environment with uv:**
   ```bash
   uv venv

   # Activate the virtual environment:
   # On macOS/Linux:
   source .venv/bin/activate

   # On Windows:
   .venv\Scripts\activate
   ```

4. **Install the package and dependencies:**
   ```bash
   # Install in editable mode with all dependencies
   uv pip install -e .
   ```

5. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

6. **Run the server:**
   ```bash
   # Using the installed console script
   template-mcp-server

   # Or directly with Python module
   python -m template_mcp_server.src.main

   # Or using uv to run directly
   uv run python -m template_mcp_server.src.main
   ```

## Configuration Options

The server configuration is managed through environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_HOST` | `localhost` | Server bind address |
| `MCP_PORT` | `5001` | Server port (1024-65535) |
| `MCP_TRANSPORT_PROTOCOL` | `http` | Transport protocol (`http`, `sse`, `streamable-http`) |
| `MCP_SSL_KEYFILE` | `None` | SSL private key file path |
| `MCP_SSL_CERTFILE` | `None` | SSL certificate file path |
| `PYTHON_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |

## Authentication

By default, `.env.example` ships with `ENABLE_AUTH=False` so you can start developing without an SSO provider. When you are ready to test the OAuth flow, see the [Authentication Guide](authentication.md) for:

- How the three auth modes work
- How to configure an OIDC provider (Keycloak, Auth0, Okta, etc.)
- Environment variable reference
- Troubleshooting 401 errors

## Verify Installation

1. **Health check:**
   ```bash
   curl http://localhost:5001/health
   ```

2. **Test MCP tools:**
   ```bash
   # Test multiply tool via MCP endpoint
   curl -X POST "http://localhost:5001/mcp" \
        -H "Content-Type: application/json" \
        -d '{"method": "tools/call", "params": {"name": "multiply_numbers", "arguments": {"a": 5, "b": 3}}}'
   ```

## Running Tests

### Development Environment Setup

1. **Install development dependencies:**
   ```bash
   uv pip install -e ".[dev]"
   ```

2. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

### Test Commands

The project includes a comprehensive test suite with 279 tests covering unit tests, integration tests, and various edge cases.

1. **Run all tests:**
   ```bash
   pytest
   ```

2. **Run tests with coverage reporting:**
   ```bash
   pytest --cov=template_mcp_server --cov-report=html --cov-report=term
   ```

3. **Run tests by category:**
   ```bash
   # Unit tests only
   pytest -m unit

   # Integration tests only
   pytest -m integration

   # Slow running tests
   pytest -m slow

   # Tests requiring network access
   pytest -m network
   ```

4. **Run specific test modules:**
   ```bash
   # Test individual components
   pytest tests/test_tools.py -v
   pytest tests/test_settings.py -v
   pytest tests/test_mcp.py -v
   pytest tests/test_api.py -v
   pytest tests/test_oauth_service.py -v

   # Run basic integration tests
   pytest tests/test_basic.py -v
   ```

5. **Run tests with different output formats:**
   ```bash
   # Verbose output with detailed test names
   pytest -v

   # Short traceback format
   pytest --tb=short

   # Quiet output (minimal)
   pytest -q
   ```

### Test Suite Overview

| Test Category | Count | Description |
|---------------|-------|-------------|
| **Unit Tests** | ~250 | Individual component testing with mocking |
| **Integration Tests** | ~29 | End-to-end workflow testing |
| **Total Tests** | 279 | Complete test coverage |

**Test Files:**
- `test_tools.py` - Tool unit tests (multiply, code review, logo)
- `test_settings.py` - Configuration and environment variable tests
- `test_mcp.py` - MCP server initialization and tool registration tests
- `test_api.py` - FastAPI endpoint and health check tests
- `test_main.py` - Application entry point tests
- `test_oauth_*.py` - OAuth controller, handler, and service tests
- `test_storage_*.py` - Storage initialization and service tests
- `test_basic.py` - Integration and package structure tests
- `test_utils.py` - Utility and logging tests

**Test Features:**
- Comprehensive error handling validation
- Async function testing support
- Mock external dependencies
- Environment isolation with fixtures
- Performance testing for large data
- Concurrent usage simulation
- Configuration validation testing

## Code Quality Checks

1. **Linting and formatting with Ruff:**
   ```bash
   # Check for issues
   ruff check .

   # Auto-fix issues
   ruff check . --fix

   # Format code
   ruff format .
   ```

2. **Type checking with MyPy:**
   ```bash
   mypy template_mcp_server/
   ```

3. **Docstring validation:**
   ```bash
   pydocstyle template_mcp_server/ --convention=google
   ```

4. **Run all pre-commit checks:**
   ```bash
   pre-commit run --all-files
   ```

## Makefile Targets

Run `make help` to see all available commands:

```bash
make help       # Show all targets
make install    # Install dependencies
make test       # Run test suite
make lint       # Run linters
make format     # Format code
make coverage   # Generate coverage report
make pre-commit # Run pre-commit hooks
make local      # Run server locally
```
