.PHONY: help install clean test lint format coverage pre-commit local container deploy undeploy deps

# OpenShift namespace (can be overridden: make deploy openshift NAMESPACE=my-project)
NAMESPACE ?= $(shell oc project -q 2>/dev/null)

.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

deps: ## Check required CLI tools (uv, podman, oc)
	@which uv > /dev/null && echo "uv: $(shell uv --version)" || (echo "Error: uv not found. Please install uv." && exit 1)
	@which podman > /dev/null && echo "podman: $(shell podman --version)" || (echo "Error: podman not found. Please install podman." && exit 1)
	@podman compose version > /dev/null 2>&1 && echo "podman compose: $(shell podman compose version)" || (echo "Error: podman compose not found. Please install podman compose." && exit 1)
	@which oc > /dev/null && echo "oc: $(shell oc version --client)" || (echo "Error: oc not found. Please install oc." && exit 1)

install: ## Install dependencies, pre-commit hooks, and activate venv
	@echo "Creating virtual environment..."
	@test -d .venv || uv venv
	@echo "Installing package with dev dependencies..."
	@. .venv/bin/activate && uv pip install -e ".[dev]"
	@echo "Installing pre-commit hooks..."
	@. .venv/bin/activate && pre-commit install
	@echo "Python dependencies installed successfully!"
	@echo "Activating virtual environment..."
	@echo '#!/bin/bash' > /tmp/activate_and_shell.sh
	@echo 'source .venv/bin/activate' >> /tmp/activate_and_shell.sh
	@echo 'echo "Virtual environment activated! Type exit to return to your original shell."' >> /tmp/activate_and_shell.sh
	@echo 'exec "$$SHELL"' >> /tmp/activate_and_shell.sh
	@chmod +x /tmp/activate_and_shell.sh
	@exec /tmp/activate_and_shell.sh

clean: ## Remove caches, venv, and build artifacts
	rm -rf .mypy_cache .ruff_cache .venv __pycache__ activate_and_shell.sh

test: ## Run test suite
	@if [ ! -d ".venv" ]; then \
		echo "Error: Virtual environment not found. Run 'make install' first to set up the environment."; \
		exit 1; \
	fi
	.venv/bin/python -m pytest

lint: ## Run ruff linter and mypy type checker
	@if [ ! -d ".venv" ]; then \
		echo "Error: Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	.venv/bin/ruff check .
	.venv/bin/mypy template_mcp_server/

format: ## Auto-fix lint issues and format code
	@if [ ! -d ".venv" ]; then \
		echo "Error: Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	.venv/bin/ruff check . --fix
	.venv/bin/ruff format .

coverage: ## Run tests with coverage report (80% minimum)
	@if [ ! -d ".venv" ]; then \
		echo "Error: Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	.venv/bin/python -m pytest --cov=template_mcp_server --cov-report=term-missing --cov-report=html --cov-fail-under=80

pre-commit: ## Run all pre-commit hooks
	@if [ ! -d ".venv" ]; then \
		echo "Error: Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	. .venv/bin/activate && pre-commit run --all-files

local: ## Start MCP server locally
	@echo "Setting up local environment..."
	@test -f .env || (echo "Creating .env from .env.example..." && cp .env.example .env)
	@echo "Starting MCP server locally on port 5001..."
	@echo "Health check available at: http://localhost:5001/health"
	@echo "Press Ctrl+C to stop the server"
	@. .venv/bin/activate && python -m template_mcp_server.src.main

container: ## Build and run with podman compose
	export PODMAN_COMPOSE_SILENT=true
	podman compose --no-ansi up --build --force-recreate --remove-orphans  --timeout=60

deploy: ## Deploy to target (usage: make deploy openshift)
	@if [ "$(filter openshift,$(MAKECMDGOALS))" = "openshift" ]; then \
		echo "Checking for oc CLI..."; \
		which oc > /dev/null || (echo "Error: oc CLI not found. Please install OpenShift CLI." && exit 1); \
		echo "Validating namespace..."; \
		if [ -z "$(NAMESPACE)" ]; then \
			echo "Error: NAMESPACE not set. Usage: make deploy openshift NAMESPACE=your-project"; \
			exit 1; \
		fi; \
		echo "Using namespace: $(NAMESPACE)"; \
		echo "Switching to namespace..."; \
		oc project $(NAMESPACE) || (echo "Error: Cannot switch to namespace '$(NAMESPACE)'. Check permissions." && exit 1); \
		echo "Updating namespace references..."; \
		sed -i.bak "s|NAMESPACE_PLACEHOLDER|$(NAMESPACE)|g" deployment/openshift/deployment.yaml; \
		sed -i.bak "s|namespace: template-mcp-server|namespace: $(NAMESPACE)|g" deployment/openshift/kustomization.yaml; \
		echo "Creating BuildConfig and ImageStream..."; \
		oc apply -f deployment/openshift/buildconfig.yaml; \
		oc apply -f deployment/openshift/imagestream.yaml; \
		echo "Building container image from source..."; \
		oc start-build template-mcp-server --from-dir=. --follow || (mv deployment/openshift/deployment.yaml.bak deployment/openshift/deployment.yaml 2>/dev/null; mv deployment/openshift/kustomization.yaml.bak deployment/openshift/kustomization.yaml 2>/dev/null; exit 1); \
		echo "Deploying resources to OpenShift..."; \
		oc apply -k deployment/openshift/ || (mv deployment/openshift/deployment.yaml.bak deployment/openshift/deployment.yaml 2>/dev/null; mv deployment/openshift/kustomization.yaml.bak deployment/openshift/kustomization.yaml 2>/dev/null; exit 1); \
		rm -f deployment/openshift/deployment.yaml.bak deployment/openshift/kustomization.yaml.bak; \
		echo "Deployment complete!"; \
		echo "Checking deployment status..."; \
		oc get pods -l app=template-mcp-server; \
		echo ""; \
		echo "Useful commands:"; \
		echo "  View logs: oc logs -l app=template-mcp-server --tail=100"; \
		echo "  Get route: oc get route template-mcp-server"; \
		echo "  Check status: oc get pods,svc,route -l app=template-mcp-server"
	else \
		echo "Usage: make deploy [openshift]"; \
		echo "Available deployment targets: openshift"; \
		exit 1; \
	fi

undeploy: ## Remove deployment (usage: make undeploy openshift)
	@if [ "$(filter openshift,$(MAKECMDGOALS))" = "openshift" ]; then \
		echo "Checking for oc CLI..."; \
		which oc > /dev/null || (echo "Error: oc CLI not found. Please install OpenShift CLI." && exit 1); \
		oc project $(NAMESPACE) || (echo "Error: Cannot switch to namespace '$(NAMESPACE)'" && exit 1); \
		echo "Removing OpenShift deployment..."; \
		oc delete deployment,service,route,configmap,secret,pvc,buildconfig,imagestream -l app=template-mcp-server 2>/dev/null || true; \
		echo "Undeployment complete!"; \
	else \
		echo "Usage: make undeploy [openshift]"; \
		echo "Available undeployment targets: openshift"; \
		exit 1; \
	fi

%:
	@:
