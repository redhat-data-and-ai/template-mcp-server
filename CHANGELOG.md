# Changelog

All notable changes to this project will be documented in this file.

This project uses [GitHub Releases](https://github.com/redhat-data-and-ai/template-mcp-server/releases) for detailed changelogs. Release notes are auto-generated from merged pull request titles and labels.

## [0.1.0] - 2026-02-09

### Added

- Initial release of Template MCP Server.
- MCP server implementation with FastMCP and FastAPI.
- Example tools: multiply numbers, code review prompt generator, Red Hat logo resource.
- OAuth integration with PostgreSQL-backed token storage.
- Multiple transport protocols: HTTP, SSE, streamable-HTTP.
- SSL/TLS support.
- Structured JSON logging with structlog.
- Pydantic-based configuration management.
- Containerized deployment with Red Hat UBI9 base image.
- OpenShift deployment support.
- Comprehensive test suite with 80%+ coverage.
- Pre-commit hooks: Ruff, MyPy, pydocstyle, Bandit.
- GitHub Actions CI workflows for tests and pre-commit.
