# MPP (Managed Platform) Deployment

This directory contains Kubernetes manifests for deploying the Template MCP Server to Red Hat Managed Platform.

## Prerequisites

- Access to Red Hat Managed Platform cluster
- `kubectl` configured with cluster access
- Tenant name for your deployment

## Quick Start

Deploy using the Makefile from the project root:

```bash
# Deploy to MPP
make deploy mpp TENANT=ask-data

# Remove deployment
make undeploy mpp TENANT=ask-data
```

## Configuration

### Required Secrets

Update `secret.yaml` before deploying:

```yaml
stringData:
  SESSION_SECRET: "CHANGE_ME_GENERATE_SECURE_RANDOM_KEY"  # Generate a secure random key
  SSO_CLIENT_ID: ""      # Optional: SSO client ID if using external auth
  SSO_CLIENT_SECRET: ""  # Optional: SSO client secret if using external auth
```

### ConfigMap Settings

Configure `configmap.yaml` for your environment:

| Setting | Default | Description |
|---------|---------|-------------|
| `PYTHON_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `MCP_TRANSPORT_PROTOCOL` | `http` | Transport protocol (http, sse, streamable-http) |
| `CORS_ENABLED` | `true` | Enable CORS |
| `ENVIRONMENT` | `production` | Environment name |
| `ENABLE_AUTH` | `true` | Enable authentication |
| `SSO_CALLBACK_URL` | - | SSO OAuth callback URL |
| `SSO_AUTHORIZATION_URL` | - | SSO authorization endpoint |
| `SSO_TOKEN_URL` | - | SSO token endpoint |
| `SSO_INTROSPECTION_URL` | - | SSO token introspection endpoint |
| `MCP_HOST_ENDPOINT` | - | Public URL for the MCP server |

### Tenant Configuration

Update `tenant.yaml` with your tenant information:

```yaml
spec:
  tenantId: "ask-data"           # Your tenant ID
  appCode: "ASKD-001"            # Your application code
  costCenter: "12345"            # Your cost center
```

## Architecture

### Authentication Modes

**Current Mode: No Authentication**
- `ENABLE_AUTH: false`
- No PostgreSQL required
- All endpoints are public
- Suitable for internal/trusted networks only

**Future: SSO-Only Mode**
- External SSO authentication via Red Hat SSO
- No local OAuth server
- Requires code changes to support

**Future: Full OAuth Mode**
- Local OAuth authorization server
- Requires PostgreSQL for token storage
- Full client authentication and authorization

### Resources Deployed

| Resource | Name | Purpose |
|----------|------|---------|
| **BuildConfig** | template-mcp-server | Build container from source |
| **ImageStream** | template-mcp-server | Store built container images |
| **Deployment** | template-mcp-server | Run MCP server application |
| **Service** | template-mcp-server | Internal cluster service (port 8080) |
| **Route** | template-mcp-server | External HTTPS access with TLS |
| **ConfigMap** | template-mcp-server-config | Environment configuration |
| **Secret** | template-mcp-server-secrets | Sensitive credentials |
| **Tenant** | ask-data | Multi-tenant configuration |

### Network Configuration

- **Service Port**: 8080 (HTTP)
- **Route**: HTTPS with edge termination
- **TLS**: Automatic certificate from platform

## Deployment Process

### Manual Deployment

```bash
# Navigate to deployment directory
cd deployment/mpp

# Update configuration files
# - secret.yaml: Add your secrets
# - configmap.yaml: Update SSO URLs
# - tenant.yaml: Set your tenant ID

# Apply manifests
kubectl apply -k .

# Verify deployment
kubectl get pods -l app=template-mcp-server
kubectl logs -l app=template-mcp-server --tail=50
```

### Build Process

The BuildConfig will:
1. Clone source from Git repository
2. Build container using Containerfile (Red Hat UBI base)
3. Push to internal ImageStream
4. Trigger deployment rollout

### Verify Deployment

```bash
# Check pod status
kubectl get pods -l app=template-mcp-server

# Check pod logs
kubectl logs -l app=template-mcp-server -f

# Check route
kubectl get route template-mcp-server

# Test health endpoint
ROUTE_URL=$(kubectl get route template-mcp-server -o jsonpath='{.spec.host}')
curl https://${ROUTE_URL}/health
```

Expected health response:
```json
{
  "status": "healthy",
  "service": "template-mcp-server",
  "transport_protocol": "http",
  "version": "0.1.0"
}
```

## Troubleshooting

### Pod Fails to Start

Check logs for errors:
```bash
kubectl logs -l app=template-mcp-server --tail=100
```

Common issues:
- Missing required secrets
- Invalid configuration values
- Database connection failures (if auth enabled)

### Build Failures

Check build logs:
```bash
kubectl logs -f bc/template-mcp-server
```

### Route Not Accessible

Check route configuration:
```bash
kubectl describe route template-mcp-server
```

Verify TLS certificate is valid and route is admitted.

## Cleanup

Remove all resources:

```bash
# Using Makefile
make undeploy mpp TENANT=ask-data

# Or manually
kubectl delete -k deployment/mpp/
```

## Security Considerations

### Current Deployment (No Auth)

⚠️ **Security Notes:**
- No authentication enabled
- All endpoints publicly accessible
- Suitable for internal networks only
- Do not expose to internet without additional security

### Recommended for Production

1. **Enable Authentication**:
   - Set `ENABLE_AUTH: true`
   - Configure SSO integration
   - Deploy PostgreSQL for token storage

2. **Network Policies**:
   - Restrict ingress to authorized sources
   - Use network policies for pod isolation

3. **Secrets Management**:
   - Use external secrets operator
   - Rotate credentials regularly
   - Never commit secrets to git

4. **Resource Limits**:
   - Set appropriate CPU/memory limits
   - Configure horizontal pod autoscaling

5. **Monitoring**:
   - Set up log aggregation
   - Configure health check monitoring
   - Enable metrics collection

## Support

For issues or questions:
- Check application logs: `kubectl logs -l app=template-mcp-server`
- Review pod events: `kubectl describe pod -l app=template-mcp-server`
- Contact platform support team
