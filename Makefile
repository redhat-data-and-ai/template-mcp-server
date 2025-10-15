.PHONY: install clean dev test local

# Detect OS
UNAME_S := $(shell uname -s)

# Install all prerequisites and dependencies
install:
	@echo "Detecting operating system..."
	@if [ "$(UNAME_S)" = "Darwin" ]; then \
		echo "macOS detected - using Homebrew"; \
		$(MAKE) install-macos; \
	elif [ -f /etc/fedora-release ]; then \
		echo "Fedora detected - using DNF"; \
		$(MAKE) install-fedora; \
	else \
		echo "Unsupported OS. Please install prerequisites manually."; \
		exit 1; \
	fi
	@echo "Installing Python dependencies..."
	$(MAKE) install-python-deps
	@echo "Installation complete!"

# macOS installation using Homebrew
install-macos:
	@echo "Checking for Homebrew..."
	@which brew > /dev/null || (echo "Homebrew not found. Installing..." && \
		/bin/bash -c "$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)")
	@echo "Installing uv..."
	@which uv > /dev/null || brew install uv
	@echo "Installing podman-compose..."
	@which podman-compose > /dev/null || brew install podman-compose

# Fedora installation using DNF
install-fedora:
	@echo "Installing uv..."
	@which uv > /dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "Installing podman-compose..."
	@which podman-compose > /dev/null || sudo dnf install -y podman-compose

# Install Python dependencies
install-python-deps:
	@echo "Creating virtual environment..."
	@test -d .venv || uv venv
	@echo "Installing package with dev dependencies..."
	@. .venv/bin/activate && uv pip install -e ".[dev]"
	@echo "Installing pre-commit hooks..."
	@. .venv/bin/activate && pre-commit install
	@echo "Python dependencies installed successfully!"

clean:
	rm -rf .mypy_cache .ruff_cache .venv __pycache__

dev:
	export PODMAN_COMPOSE_SILENT=true
	podman-compose --no-ansi up --build --force-recreate --remove-orphans  --timeout=60

test:
	@if [ ! -d ".venv" ]; then \
		echo "Error: Virtual environment not found. Run 'make install' first to set up the environment."; \
		exit 1; \
	fi
	.venv/bin/python -m pytest

local:
	@echo "Setting up local environment..."
	@test -f .env || (echo "Creating .env from .env.example..." && cp .env.example .env)
	@echo "Starting MCP server locally on port 5001..."
	@echo "Health check available at: http://localhost:5001/health"
	@echo "Press Ctrl+C to stop the server"
	@. .venv/bin/activate && python -m template_mcp_server.src.main
