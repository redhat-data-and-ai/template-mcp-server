.PHONY: install clean dev test local deploy undeploy

# OpenShift namespace
NAMESPACE := template-mcp-server

# Detect OS
UNAME_S := $(shell uname -s)

# Detect Linux distribution from /etc/os-release
DISTRO_ID := $(shell if [ -f /etc/os-release ]; then . /etc/os-release && echo $$ID; fi)

# Install all prerequisites and dependencies
install:
	@echo "Detecting operating system..."
	@if [ "$(UNAME_S)" = "Darwin" ]; then \
		echo "macOS detected - using Homebrew"; \
		$(MAKE) install-macos; \
	elif [ "$(UNAME_S)" = "Linux" ] && [ "$(DISTRO_ID)" = "fedora" ]; then \
		echo "Fedora Linux detected - using DNF"; \
		$(MAKE) install-fedora; \
	elif [ "$(UNAME_S)" = "Linux" ] && [ "$(DISTRO_ID)" = "ubuntu" ]; then \
		echo "Ubuntu Linux detected - using APT (UNTESTED)"; \
		$(MAKE) install-ubuntu; \
	elif [ "$(UNAME_S)" = "Linux" ]; then \
		echo "Linux detected but unsupported distribution: $(DISTRO_ID)"; \
		echo "Please install uv and podman-compose manually."; \
		echo "See: https://docs.astral.sh/uv/getting-started/installation/"; \
		exit 1; \
	else \
		echo "Unsupported OS: $(UNAME_S). Please install prerequisites manually."; \
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

# Ubuntu installation using APT (UNTESTED)
install-ubuntu:
	@echo "Installing uv..."
	@which uv > /dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "Installing podman-compose..."
	@which podman-compose > /dev/null || sudo apt-get update && sudo apt-get install -y podman-compose

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

# Deployment targets
deploy:
	@if [ "$(filter openshift,$(MAKECMDGOALS))" != "openshift" ]; then \
		echo "Usage: make deploy openshift"; \
		echo "Available deployment targets: openshift"; \
		exit 1; \
	fi

openshift:
	@echo "Checking for oc CLI..."
	@which oc > /dev/null || (echo "Error: oc CLI not found. Please install OpenShift CLI." && exit 1)
	@echo "Creating OpenShift project '$(NAMESPACE)'..."
	@oc get project $(NAMESPACE) > /dev/null 2>&1 && \
		(echo "Project already exists, switching to it..." && oc project $(NAMESPACE)) || \
		(echo "Creating new project..." && oc new-project $(NAMESPACE) --display-name="Template MCP Server" --description="Template MCP Server deployment")
	@echo "Waiting for project to be available..."
	@remaining=60; \
		while [ $$remaining -gt 0 ]; do \
			if oc get project $(NAMESPACE) > /dev/null 2>&1 && oc project $(NAMESPACE) > /dev/null 2>&1; then \
				echo "Project is ready!"; \
				break; \
			fi; \
			echo "Waiting for project... ($$remaining seconds remaining)"; \
			sleep 2; \
			remaining=$$((remaining - 2)); \
		done; \
		if [ $$remaining -le 0 ]; then \
			echo "Error: Project did not become available in time"; \
			exit 1; \
		fi
	@echo "Deploying to OpenShift..."
	@oc apply -k deployment/openshift/
	@echo "Deployment complete!"
	@echo "Checking deployment status..."
	@oc get pods -l app=template-mcp-server
	@echo ""
	@echo "To view logs: oc logs -l app=template-mcp-server --tail=100"
	@echo "To get route URL: oc get route template-mcp-server"

undeploy:
	@if [ "$(filter openshift,$(MAKECMDGOALS))" = "openshift" ]; then \
		echo "Checking for oc CLI..."; \
		which oc > /dev/null || (echo "Error: oc CLI not found. Please install OpenShift CLI." && exit 1); \
		echo "Removing OpenShift deployment..."; \
		oc delete -k deployment/openshift/; \
		echo "Undeployment complete!"; \
	else \
		echo "Usage: make undeploy openshift"; \
		echo "Available undeployment targets: openshift"; \
		exit 1; \
	fi

%:
	@:
