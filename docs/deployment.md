# Deployment Guide

## Using Podman / Docker Compose

1. **Build and run with Podman Compose:**
   ```bash
   podman compose up --build
   ```

2. **Or build manually:**
   ```bash
   podman build -t template-mcp-server .
   podman run -p 5001:5001 --env-file .env template-mcp-server
   ```

## Deploying to OpenShift

The OpenShift manifests live in `deployment/openshift/` (Deployment, Service, Route, ConfigMap, Secret, BuildConfig, ImageStream, Kustomization).

Quick start:

```bash
# Deploy to OpenShift namespace
make deploy openshift NAMESPACE=your-project-name

# Remove deployment
make undeploy openshift
```

## Container Configuration

The container is built using a Red Hat UBI (Universal Base Image) base. Key details:

- **Base Image**: Red Hat UBI 9 / Python 3.12
- **Exposed Port**: 5001 (matching `.env.example`, mapped via `compose.yaml`)
- **Health Check**: `curl -f http://localhost:5001/health`

The `compose.yaml` maps container port 5001 to host port 5001. It also overrides `MCP_HOST=0.0.0.0` so the server binds to all interfaces inside the container (required for port forwarding to work).

## Manual Testing

1. **Container testing:**
   ```bash
   podman compose up -d
   curl -f http://localhost:5001/health
   podman compose down
   ```

2. **SSL testing (if configured):**
   ```bash
   curl -k https://localhost:5001/health
   ```

3. **Import validation:**
   ```bash
   podman run --rm template-mcp-server python -c "import template_mcp_server; print('OK')"
   ```
