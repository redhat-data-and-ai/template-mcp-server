# RFE MCP Server

[![Python 3.12+](https://img.shields.io/badge/python-3.12,3.13-blue.svg)](https://www.python.org/downloads/)
<!-- [![Tests](https://github.com/redhat-data-and-ai/rfe-mcp-server/actions/workflows/test.yml/badge.svg)](https://github.com/redhat-data-and-ai/rfe-mcp-server/actions/workflows/test.yml) -->
<!-- [![Coverage](https://codecov.io/gh/redhat-data-and-ai/rfe-mcp-server/branch/main/graph/badge.svg)](https://codecov.io/gh/redhat-data-and-ai/rfe-mcp-server) -->
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A unified RFE (Request for Enhancement) aggregation and query service for the RHEL ecosystem, built as a [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server. It integrates data from internal issue tracking systems (e.g., Jira) with customer and asset context, enabling Sales and Support teams to retrieve and analyse customer-specific or system-relevant RFEs efficiently.

This project is built on top of the [Template MCP Server](https://github.com/redhat-data-and-ai/template-mcp-server), a production-ready Python/FastMCP starter maintained by Red Hat Data & AI.

## Goal

Establish a centralized service that:

- **Aggregates RFE data** from internal issue tracking systems and associates it with customer/account and asset context.
- **Exposes MCP tools** for querying RFEs by customer/account, by system/asset relevance, and for retrieving RFE status and metadata.
- **Improves customer communication** by giving Sales and Support teams fast, structured access to RFE information (open, planned, implemented, etc.).
- **Lays the foundation** for future end-user self-service, where customers can directly track the status and progress of their submitted RFEs.

## MCP Tools

| Tool | Description |
| ---- | ----------- |
| Query RFEs by customer/account | Retrieve all RFEs associated with a given customer or account |
| Query RFEs by system/asset relevance | Find RFEs relevant to specific systems or assets |
| Retrieve RFE status & metadata | Get structured status (open, planned, implemented) and details for individual RFEs |

Retrieved data is structured, consistent, and suitable for consumption by downstream tools (e.g., LLMs, internal tooling).

## Features

- **FastMCP + FastAPI** with multiple transport protocols (HTTP, SSE, streamable-HTTP)
- **Pydantic configuration** via environment variables
- **Structured JSON logging** with structlog
- **SSL/TLS support** for secure deployments
- **OAuth2 integration** with PostgreSQL token storage and RBAC-ready access control
- **Container-ready** with Red Hat UBI base image
- **OpenShift deployment** manifests included
- **Full CI/CD** with GitHub Actions (tests, linting, security, releases)
- **Extensible design** for additional data sources (inventory, product metadata) and future self-service access

## Dependencies

| Dependency | Purpose |
| ---------- | ------- |
| Internal issue tracking APIs (e.g., Jira) | Source of RFE data |
| Customer/account data services | Map RFEs to organizations |
| Inventory/asset data services (optional) | Relevance-based querying |
| OAuth2 / RBAC | Authentication and authorization |
| PostgreSQL | Token and session storage |

## Quick Start

```bash
git clone https://github.com/redhat-data-and-ai/rfe-mcp-server
cd rfe-mcp-server
make install        # creates venv, installs deps + pre-commit hooks
make local          # starts server on localhost:5001
```

Verify in another terminal:

```bash
curl http://localhost:5001/health
```

<details>
<summary>Manual setup (without Make)</summary>

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install

cp .env.example .env
rfe-mcp-server

curl http://localhost:5001/health
```

</details>

## Configuration

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `MCP_HOST` | `localhost` | Server bind address |
| `MCP_PORT` | `5001` | Server port (1024-65535) |
| `MCP_TRANSPORT_PROTOCOL` | `http` | Transport protocol (`http`, `sse`, `streamable-http`) |
| `MCP_SSL_KEYFILE` | `None` | SSL private key file path |
| `MCP_SSL_CERTFILE` | `None` | SSL certificate file path |
| `ENABLE_AUTH` | `False`* | Enable OAuth authentication (see [Auth Guide](docs/authentication.md)) |
| `USE_EXTERNAL_BROWSER_AUTH` | `False` | Browser-based OAuth for local dev |
| `PYTHON_LOG_LEVEL` | `INFO` | Logging level |

*\* `ENABLE_AUTH` defaults to `False` in `.env.example` but `True` in code. Always copy `.env.example` to `.env` to start with auth disabled.*

## Development

| Command | Description |
| ------- | ----------- |
| `make install` | Create venv, install deps, set up pre-commit |
| `make local` | Start server on localhost:5001 |
| `make test` | Run test suite (pytest) |
| `make coverage` | Tests with coverage report (80% minimum) |
| `make lint` | Ruff linter + mypy type checker |
| `make format` | Auto-fix lint issues + format code |
| `make pre-commit` | Run all pre-commit hooks |
| `make container` | Build and run with podman compose |
| `make clean` | Remove caches, venv, build artifacts |

## Access Control

The system design supports two tiers of access:

- **Internal users** (Sales, Support) can access cross-customer RFE data where permitted.
- **External users** (future) are restricted to their own RFE data or publicly visible RFEs.

See [Authentication](docs/authentication.md) for OAuth setup and configuration.

## Documentation

| Guide | Description |
| ----- | ----------- |
| [Architecture](docs/architecture.md) | System diagrams, code structure, key components |
| [Development](docs/development.md) | Setup, running locally, testing, code quality |
| [Deployment](docs/deployment.md) | Podman, OpenShift, container configuration |
| [CI/CD](docs/ci-cd.md) | Workflows, pipeline features, running CI locally |
| [Authentication](docs/authentication.md) | OAuth setup, auth modes, troubleshooting |
| [Contributing](CONTRIBUTING.md) | Development workflow, commit conventions, PR process |
| [Security](SECURITY.md) | Vulnerability reporting policy |
| [Changelog](CHANGELOG.md) | Release history |
| [Examples](examples/) | FastMCP and LangGraph client examples |


## License

[Apache 2.0](LICENSE)
