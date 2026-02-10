# Template MCP Server

[![Python 3.12+](https://img.shields.io/badge/python-3.12,3.13-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/redhat-data-and-ai/template-mcp-server/actions/workflows/test.yml/badge.svg)](https://github.com/redhat-data-and-ai/template-mcp-server/actions/workflows/test.yml)
[![Coverage](https://codecov.io/gh/redhat-data-and-ai/template-mcp-server/branch/main/graph/badge.svg)](https://codecov.io/gh/redhat-data-and-ai/template-mcp-server)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/redhat-data-and-ai/template-mcp-server)

A production-ready template for developing Model Context Protocol (MCP) servers using Python and FastMCP. This server provides a foundation for creating MCP-compliant servers with comprehensive examples of tools, structured logging, configuration management, and containerized deployment.

The template includes three example MCP tools: a multiply calculator, a code review prompt generator, and a Red Hat logo resource handler. It demonstrates best practices for MCP server development including proper error handling, health checks, multiple transport protocols (HTTP, SSE, streamable-HTTP), SSL support, and comprehensive development tooling.

## Features

- **FastMCP + FastAPI** with multiple transport protocols (HTTP, SSE, streamable-HTTP)
- **Three example tools**: multiply calculator, code review prompt, Red Hat logo resource
- **Pydantic configuration** via environment variables
- **Structured JSON logging** with structlog
- **SSL/TLS support** for secure deployments
- **Container-ready** with Red Hat UBI base image
- **OpenShift deployment** manifests included
- **Full CI/CD** with GitHub Actions (tests, linting, security, releases)
- **OAuth integration** with PostgreSQL token storage

## Quick Start

```bash
git clone https://github.com/redhat-data-and-ai/template-mcp-server
cd template-mcp-server
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
# Create venv and install
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install

# Configure and run
cp .env.example .env
template-mcp-server

# Verify
curl http://localhost:5001/health
```

</details>

## How to Use This Template

### Option 1: GitHub Template (Recommended)

1. Click the **"Use this template"** button at the top of the repository page.
2. Name your new repository (e.g., `my-mcp-server`).
3. Clone your new repository and follow the [rename checklist](#rename-checklist) below.

### Option 2: Manual Clone

```bash
git clone https://github.com/redhat-data-and-ai/template-mcp-server.git my-mcp-server
cd my-mcp-server
rm -rf .git
git init
```

### Rename Checklist

After creating your project, replace all references to `template-mcp-server` and `template_mcp_server` with your project name. The following files require updates:

| File / Directory         | What to Change                                                                          |
| ------------------------ | --------------------------------------------------------------------------------------- |
| `template_mcp_server/` | Rename the package directory (e.g.,`my_mcp_server/`)                                  |
| `pyproject.toml`       | `name`, `project.scripts` entry, `[project.urls]`, `[tool.coverage.run] source` |
| `Makefile`             | References in `lint`, `local`, and deployment targets                               |
| `Containerfile`        | `COPY` source path and `CMD` module path                                            |
| `compose.yaml`         | `container_name`, service name, healthcheck URL                                       |
| `deployment/`          | App labels, image names, route names in all manifests                                   |
| `.github/workflows/`   | Badge URLs in `README.md`, Codecov flags                                              |
| `README.md`            | Title, badges, clone URL, description                                                   |
| `.env.example`         | Adjust defaults if your server uses a different port or protocol                        |

### Verify Rename

Run this to catch any leftover references:

```bash
grep -rn "template.mcp" --include="*.py" --include="*.yaml" --include="*.yml" --include="*.toml" --include="*.md" .
```

The output should be empty (or only match this README section itself).

## Configuration

| Variable                   | Default       | Description                                                 |
| -------------------------- | ------------- | ----------------------------------------------------------- |
| `MCP_HOST`               | `localhost` | Server bind address                                         |
| `MCP_PORT`               | `5001`      | Server port (1024-65535)                                    |
| `MCP_TRANSPORT_PROTOCOL` | `http`      | Transport protocol (`http`, `sse`, `streamable-http`) |
| `MCP_SSL_KEYFILE`        | `None`      | SSL private key file path                                   |
| `MCP_SSL_CERTFILE`       | `None`      | SSL certificate file path                                   |
| `ENABLE_AUTH`            | `False`*    | Enable OAuth authentication (see [Auth Guide](docs/authentication.md)) |
| `USE_EXTERNAL_BROWSER_AUTH` | `False`  | Browser-based OAuth for local dev                           |
| `PYTHON_LOG_LEVEL`       | `INFO`      | Logging level                                               |

*\* `ENABLE_AUTH` defaults to `False` in `.env.example` but `True` in code. Always copy `.env.example` to `.env` to start with auth disabled.*

## Documentation

| Guide                             | Description                                                |
| --------------------------------- | ---------------------------------------------------------- |
| [Architecture](docs/architecture.md) | System diagrams, code structure, key components, MCP tools |
| [Development](docs/development.md)   | Setup, running locally, testing, code quality              |
| [Deployment](docs/deployment.md)     | Podman, OpenShift, container configuration                 |
| [CI/CD](docs/ci-cd.md)               | Workflows, pipeline features, running CI locally           |
| [Contributing](CONTRIBUTING.md)      | Development workflow, commit conventions, PR process       |
| [Security](SECURITY.md)              | Vulnerability reporting policy                             |
| [Changelog](CHANGELOG.md)            | Release history                                            |
| [Authentication](docs/authentication.md)   | OAuth setup, auth modes, troubleshooting                   |
| [Tutorial](docs/tutorial.md)            | Your First Tool in 5 Minutes                               |
| [Examples](examples/)                | FastMCP and LangGraph client examples                      |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

```bash
# Fork, clone, and set up
git clone https://github.com/<your-username>/template-mcp-server.git
cd template-mcp-server
make install

# Create a branch, make changes, verify
git checkout -b feat/your-feature
make lint && make test && make pre-commit

# Commit and open a PR
git commit -m "feat: your descriptive message"
git push origin feat/your-feature
```

## License

[Apache 2.0](LICENSE)
