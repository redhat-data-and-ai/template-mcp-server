# Development Guide

## Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) (fast Python package installer and resolver)
- make (macOS: `xcode-select --install`, Linux: `sudo apt install make` or `sudo dnf install make`)
- [Podman](https://podman.io/docs/installation) and [podman-compose](https://github.com/containers/podman-compose#installation) (required for containerized deployment and local PostgreSQL)

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
4. **Install the package and development dependencies:**

   ```bash
   # Install in editable mode with dev dependencies (pytest, ruff, mypy, pre-commit, etc.)
   uv pip install -e ".[dev]"
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

| Variable                      | Default                   | Description                                                               |
| ----------------------------- | ------------------------- | ------------------------------------------------------------------------- |
| `MCP_HOST`                  | `localhost`             | Server bind address                                                       |
| `MCP_PORT`                  | `5001`                  | Server port (1024-65535)                                                  |
| `MCP_TRANSPORT_PROTOCOL`    | `http`                  | Transport protocol (`http`, `sse`, `streamable-http`)               |
| `MCP_HOST_ENDPOINT`         | `http://localhost:5001` | Public-facing host URL (used in OAuth discovery responses)                |
| `MCP_SSL_KEYFILE`           | `None`                  | SSL private key file path                                                 |
| `MCP_SSL_CERTFILE`          | `None`                  | SSL certificate file path                                                 |
| `PYTHON_LOG_LEVEL`          | `INFO`                  | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `ENVIRONMENT`               | `development`           | Deployment environment identifier                                         |
| `ENABLE_AUTH`               | `True`*                 | Enable OAuth authentication (see[Auth Guide](authentication.md))             |
| `USE_EXTERNAL_BROWSER_AUTH` | `False`                 | Browser-based OAuth for local dev                                         |
| `COMPATIBLE_WITH_CURSOR`    | `False`                 | Cursor IDE OAuth2 compatibility mode                                      |
| `MCP_TOOLS_CONFIG_PATH`     | *(bundled)*             | Directory of per-tool YAML configs                                        |
| `CORS_ENABLED`              | `False`                 | Enable CORS middleware                                                    |
| `CORS_ORIGINS`              | `["*"]`                 | Allowed CORS origins                                                      |

*\* `ENABLE_AUTH` defaults to `True` in code but `False` in `.env.example`. Always copy `.env.example` to `.env`.*

See the [Authentication Guide](authentication.md) for the full list of `SSO_*` and `POSTGRES_*` variables.

## Tools config-as-code

Tool definitions live in `template_mcp_server/config/tools/` (one YAML file per tool). Handlers live in `template_mcp_server/src/tools/`. See [Architecture](architecture.md#tools-config-as-code) for loading and invocation diagrams.

```bash
# Optional: mount an alternate config directory (OpenShift ConfigMap, local override)
export MCP_TOOLS_CONFIG_PATH=/path/to/tools
```

To add a tool: create a handler + YAML config, restart the server. No `mcp.py` changes required. See the [Tutorial](tutorial.md).

### Connect from Cursor

Add to `~/.cursor/mcp.json`:

```json
"template-mcp-server": {
  "url": "http://localhost:5001/mcp",
  "type": "streamableHttp"
}
```

**Local dev tips:**

- Keep `ENABLE_AUTH=False` in `.env` unless testing OAuth
- Server must be running before enabling the MCP in Cursor (`make local`)
- If the port is in use, set `MCP_PORT` in `.env` and update the URL in `mcp.json`
- If Cursor shows Error with no Login button, use **Logout** to reset stale auth state, then toggle off/on

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
   # Recommended: use the FastMCP client example
   python examples/fastmcp_client.py

   # Or call a tool directly (server must be running)
   python -c "
   import asyncio
   from fastmcp import Client
   async def main():
       c = Client({'mcpServers': {'t': {'url': 'http://localhost:5001/mcp'}}})
       async with c:
           print(await c.call_tool('multiply_numbers', {'a': 5, 'b': 3}))
   asyncio.run(main())
   "
   ```

## Running Tests

### Development Environment Setup

If you followed the [Setup](#setup) steps above, dev dependencies and pre-commit hooks are already installed. Otherwise:

```bash
uv pip install -e ".[dev]"
pre-commit install
```

### Test Commands

The project includes a comprehensive test suite covering unit tests, integration tests, and various edge cases. To see the current count, run `pytest --collect-only -q`.

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

| Test Category               | Count    | Description                               |
| --------------------------- | -------- | ----------------------------------------- |
| **Unit Tests**        | Majority | Individual component testing with mocking |
| **Integration Tests** | ~10%     | End-to-end workflow testing               |

**Test Files:**

- `test_tools.py` - Tool handler unit tests (multiply, code review, logo)
- `test_tools_loader.py` - YAML loader, registry, and wrapper tests
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
