# OpenShift Deployment Guide

This directory contains Kubernetes/OpenShift manifests for deploying the Template MCP Server.

## Prerequisites

- OpenShift cluster access with appropriate permissions
- `oc` CLI tool installed and configured
- External PostgreSQL database (connection details required)
- Container image built and pushed to a registry accessible by OpenShift

## Files Overview

- **deployment.yaml** - Main application deployment with health checks and resource limits
- **service.yaml** - ClusterIP service exposing the MCP server internally
- **route.yaml** - OpenShift Route for external HTTPS access
- **configmap.yaml** - Non-sensitive configuration values
- **secret.yaml** - Sensitive data (database credentials, session secrets, SSO config)

## Deployment Steps

### 1. Build and Push Container Image

Build your container image and push it to a registry:

```bash
# Build the image
podman build -f Containerfile -t template-mcp-server:latest .

# Tag for your registry
podman tag template-mcp-server:latest <registry>/template-mcp-server:latest

# Push to registry
podman push <registry>/template-mcp-server:latest
```

### 2. Update Image Reference

Edit `deployment.yaml` and update the image reference:

```yaml
image: <registry>/template-mcp-server:latest
```

### 3. Configure Secrets

Edit `secret.yaml` and update all placeholder values:

```yaml
stringData:
  POSTGRES_DB: "your_database_name"
  POSTGRES_USER: "your_database_user"
  POSTGRES_PASSWORD: "your_secure_password"
  SESSION_SECRET: "generate-a-secure-random-key-here"
  SSO_CLIENT_ID: "your_sso_client_id"
  SSO_CLIENT_SECRET: "your_sso_client_secret"
```

**Important**: Generate a secure SESSION_SECRET:

```bash
openssl rand -base64 32
```

### 4. Configure ConfigMap

Edit `configmap.yaml` and update:

- `POSTGRES_HOST` - External PostgreSQL hostname or service name
- `POSTGRES_PORT` - PostgreSQL port (default: 5432)
- `MCP_HOST_ENDPOINT` - Full URL where the service will be accessible (e.g., `https://template-mcp-server.example.com`)
- SSO URLs if using OAuth authentication
- Other configuration values as needed

### 5. Create OpenShift Project

```bash
oc new-project template-mcp-server
```

### 6. Deploy Resources

Apply all manifests in order:

```bash
# Create ConfigMap
oc apply -f configmap.yaml

# Create Secret
oc apply -f secret.yaml

# Create Deployment
oc apply -f deployment.yaml

# Create Service
oc apply -f service.yaml

# Create Route
oc apply -f route.yaml
```

Or apply all at once:

```bash
oc apply -f .
```

### 7. Verify Deployment

Check deployment status:

```bash
oc get pods -l app=template-mcp-server
oc get svc template-mcp-server
oc get route template-mcp-server
```

Check logs:

```bash
oc logs -l app=template-mcp-server --tail=100
```

Test health endpoint:

```bash
# Get route URL
ROUTE_URL=$(oc get route template-mcp-server -o jsonpath='{.spec.host}')

# Test health endpoint
curl -k https://${ROUTE_URL}/health
```

## Configuration Reference

### Environment Variables

The deployment uses environment variables from ConfigMap and Secrets. Key variables:

- **MCP_HOST** - Server bind address (default: 0.0.0.0)
- **MCP_PORT** - Server port (default: 8080)
- **POSTGRES_HOST** - External PostgreSQL hostname
- **POSTGRES_PORT** - PostgreSQL port
- **POSTGRES_DB** - Database name (from Secret)
- **POSTGRES_USER** - Database user (from Secret)
- **POSTGRES_PASSWORD** - Database password (from Secret)
- **SESSION_SECRET** - Session encryption key (from Secret)
- **ENABLE_AUTH** - Enable OAuth authentication (default: true)
- **ENVIRONMENT** - Environment name (default: production)

See `template_mcp_server/src/settings.py` for complete configuration options.

## Scaling

Scale the deployment:

```bash
oc scale deployment template-mcp-server --replicas=3
```

## Updating Configuration

After modifying ConfigMap or Secret:

```bash
# Apply changes
oc apply -f configmap.yaml
oc apply -f secret.yaml

# Restart pods to pick up changes
oc rollout restart deployment template-mcp-server
```

## Troubleshooting

### Pods Not Starting

Check pod status and events:

```bash
oc describe pod -l app=template-mcp-server
oc get events --sort-by='.lastTimestamp'
```

### Database Connection Issues

Verify PostgreSQL connectivity from within the cluster:

```bash
oc run -it --rm debug --image=registry.redhat.io/rhel9/postgresql-15:latest --restart=Never -- psql -h <POSTGRES_HOST> -U <POSTGRES_USER> -d <POSTGRES_DB>
```

### Health Check Failures

Check application logs:

```bash
oc logs -l app=template-mcp-server --tail=100
```

Verify health endpoint manually:

```bash
oc exec -it deployment/template-mcp-server -- curl -f http://localhost:8080/health
```

## Resource Limits

Default resource requests/limits:
- Memory: 256Mi request, 512Mi limit
- CPU: 100m request, 500m limit

Adjust in `deployment.yaml` as needed for your workload.

## Security Notes

- Secrets are stored as base64-encoded values in etcd
- Use OpenShift Secrets or external secret management for production
- Rotate SESSION_SECRET and database passwords regularly
- Ensure PostgreSQL connection uses TLS in production
- Review and adjust security contexts as needed
