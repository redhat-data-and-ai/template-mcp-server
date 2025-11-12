.PHONY: install clean test local container deploy undeploy

# OpenShift namespace (can be overridden: make deploy openshift NAMESPACE=my-project)
NAMESPACE ?= $(shell oc project -q 2>/dev/null)

# Dependency checks
deps:
	@which uv > /dev/null && echo "uv: $(shell uv --version)" || (echo "Error: uv not found. Please install uv." && exit 1)
	@which podman > /dev/null && echo "podman: $(shell podman --version)" || (echo "Error: podman not found. Please install podman." && exit 1)
	@which podman-compose > /dev/null && echo "podman-compose: $(shell podman-compose --version)" || (echo "Error: podman-compose not found. Please install podman-compose." && exit 1)
	@which oc > /dev/null && echo "oc: $(shell oc version --client)" || (echo "Error: oc not found. Please install oc." && exit 1)

# Install Python dependencies
install:
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

clean:
	rm -rf .mypy_cache .ruff_cache .venv __pycache__ activate_and_shell.sh

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

container:
	export PODMAN_COMPOSE_SILENT=true
	podman-compose --no-ansi up --build --force-recreate --remove-orphans  --timeout=60

# Deployment targets
deploy:
	@if [ "$(filter openshift,$(MAKECMDGOALS))" != "openshift" ] && [ "$(filter mpp,$(MAKECMDGOALS))" != "mpp" ]; then \
		echo "Usage: make deploy [openshift|mpp]"; \
		echo "Available deployment targets: openshift, mpp"; \
		exit 1; \
	fi

openshift:
	@echo "Checking for oc CLI..."
	@which oc > /dev/null || (echo "Error: oc CLI not found. Please install OpenShift CLI." && exit 1)
	@echo "Validating namespace..."
	@if [ -z "$(NAMESPACE)" ]; then \
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

mpp:
	@echo "Checking for oc CLI..."
	@which oc > /dev/null || (echo "Error: oc CLI not found. Please install OpenShift CLI." && exit 1)
	@echo "Validating TENANT parameter..."
	@if [ -z "$(TENANT)" ]; then \
		echo "Error: TENANT not set. Usage: make deploy mpp TENANT=your-tenant"; \
		exit 1; \
	fi; \
	CONFIG_NAMESPACE="$(TENANT)--config"; \
	RUNTIME_NAMESPACE="$(TENANT)--template"; \
	echo "Config namespace: $$CONFIG_NAMESPACE"; \
	echo "Runtime namespace: $$RUNTIME_NAMESPACE"; \
	echo "Updating tenant.yaml with config namespace..."; \
	sed -i.bak "s|TENANT_PLACEHOLDER|$$CONFIG_NAMESPACE|g" deployment/mpp/tenant.yaml; \
	echo "Creating/switching to config namespace..."; \
	oc project $$CONFIG_NAMESPACE 2>/dev/null || oc new-project $$CONFIG_NAMESPACE || (echo "Error: Cannot create/switch to namespace '$$CONFIG_NAMESPACE'." && mv deployment/mpp/tenant.yaml.bak deployment/mpp/tenant.yaml 2>/dev/null && exit 1); \
	echo "Applying TenantNamespace CR to create runtime namespace..."; \
	oc apply -f deployment/mpp/tenant.yaml || (mv deployment/mpp/tenant.yaml.bak deployment/mpp/tenant.yaml 2>/dev/null && exit 1); \
	echo "Waiting for runtime namespace '$$RUNTIME_NAMESPACE' to be created..."; \
	COUNTER=1; \
	until oc get project $$RUNTIME_NAMESPACE 2>/dev/null || [ $$COUNTER -gt 30 ]; do \
		echo "Waiting for namespace... ($$COUNTER/30)"; \
		sleep 2; \
		COUNTER=$$((COUNTER + 1)); \
	done; \
	if [ $$COUNTER -le 30 ]; then \
		echo "Runtime namespace '$$RUNTIME_NAMESPACE' is ready"; \
	fi; \
	oc project "$(TENANT)--$(RUNTIME_NAMESPACE)" > /dev/null 2>&1 || (echo "Error: Runtime namespace '$$RUNTIME_NAMESPACE' was not created" && mv deployment/mpp/tenant.yaml.bak deployment/mpp/tenant.yaml 2>/dev/null && exit 1); \
	echo "Switching to runtime namespace..."; \
	oc project $$RUNTIME_NAMESPACE || (echo "Error: Cannot switch to runtime namespace '$$RUNTIME_NAMESPACE'" && mv deployment/mpp/tenant.yaml.bak deployment/mpp/tenant.yaml 2>/dev/null && exit 1); \
	echo "Creating BuildConfig and ImageStream..."; \
	oc apply -f deployment/mpp/buildconfig.yaml; \
	oc apply -f deployment/mpp/imagestream.yaml; \
	echo "Building container image from source..."; \
	oc start-build template-mcp-server --from-dir=. --follow || (mv deployment/mpp/tenant.yaml.bak deployment/mpp/tenant.yaml 2>/dev/null; exit 1); \
	echo "Deploying resources to MPP..."; \
	oc apply -k deployment/mpp/ || (mv deployment/mpp/tenant.yaml.bak deployment/mpp/tenant.yaml 2>/dev/null; exit 1); \
	rm -f deployment/mpp/tenant.yaml.bak; \
	echo "Deployment complete!"; \
	echo "Checking deployment status..."; \
	oc get pods -l app=template-mcp-server; \
	echo ""; \
	echo "Useful commands:"; \
	echo "  View logs: oc logs -l app=template-mcp-server --tail=100"; \
	echo "  Get route: oc get route template-mcp-server"; \
	echo "  Check status: oc get pods,svc,route -l app=template-mcp-server"

undeploy:
	@if [ "$(filter openshift,$(MAKECMDGOALS))" = "openshift" ]; then \
		echo "Checking for oc CLI..."; \
		which oc > /dev/null || (echo "Error: oc CLI not found. Please install OpenShift CLI." && exit 1); \
		oc project $(NAMESPACE) || (echo "Error: Cannot switch to namespace '$(NAMESPACE)'" && exit 1); \
		echo "Removing OpenShift deployment..."; \
		oc delete deployment,service,route,configmap,secret,pvc,buildconfig,imagestream -l app=template-mcp-server 2>/dev/null || true; \
		echo "Undeployment complete!"; \
		exit 1; \
	elif [ "$(filter mpp,$(MAKECMDGOALS))" = "mpp" ]; then \
		echo "Checking for oc CLI..."; \
		RUNTIME_NAMESPACE="$(TENANT)--template"; \
		which oc > /dev/null || (echo "Error: oc CLI not found. Please install OpenShift CLI." && exit 1); \
		oc project $$RUNTIME_NAMESPACE || (echo "Error: Cannot switch to runtime namespace '$$RUNTIME_NAMESPACE'" && exit 1); \
		echo "Removing MPP deployment..."; \
		oc delete deployment,service,route,configmap,secret,pvc,buildconfig,imagestream -l app=template-mcp-server 2>/dev/null || true; \
		echo "Undeployment complete!"; \
		exit 1; \
	else \
		echo "Usage: make undeploy [openshift|mpp]"; \
		echo "Available undeployment targets: openshift, mpp"; \
		exit 1; \
	fi

%:
	@:
