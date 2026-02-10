# Authentication Guide

This guide explains how authentication works in the template MCP server, how to configure it, and how to troubleshoot common issues.

## Overview

The server supports three authentication modes controlled by two environment variables:

| `ENABLE_AUTH` | `USE_EXTERNAL_BROWSER_AUTH` | Mode | Required Variables |
|---|---|---|---|
| `False` | any | **No Auth** | None |
| `True` | `True` | **Local Dev Auth** | `SSO_CLIENT_ID`, `SSO_CLIENT_SECRET`, `SSO_CALLBACK_URL`, `SSO_AUTHORIZATION_URL`, `SSO_TOKEN_URL`, `SSO_INTROSPECTION_URL`, `POSTGRES_*` |
| `True` | `False` | **Production Auth** | `SSO_CLIENT_ID`, `SSO_CLIENT_SECRET`, `SSO_CALLBACK_URL`, `SSO_AUTHORIZATION_URL`, `SSO_TOKEN_URL`, `SSO_INTROSPECTION_URL`, `SESSION_SECRET`, `POSTGRES_*` |

Both authenticated modes **require a working OIDC/OAuth 2.0 provider** (e.g., Keycloak, Red Hat SSO, Auth0, Okta) with valid client credentials and endpoint URLs configured.

## Running Without Auth (Default)

The simplest path. No SSO provider needed.

```bash
# .env
ENABLE_AUTH=False
USE_EXTERNAL_BROWSER_AUTH=False
```

With auth disabled, all endpoints are accessible without tokens. This is the recommended starting point for development and testing tool logic.

> **Note:** `.env.example` ships with `ENABLE_AUTH=False`. The code default in `settings.py` is `True`, so if you run without a `.env` file, auth will be **on** and you will get 401 errors unless an SSO provider is configured.

## Prerequisites for Authenticated Modes

Before enabling auth, you need:

1. **An OIDC/OAuth 2.0 provider** — any spec-compliant provider works:

   - [Keycloak](https://www.keycloak.org/)
   - [Auth0](https://auth0.com/)
   - [Okta](https://www.okta.com/)
   - Any provider supporting authorization code flow with token introspection
2. **A registered OAuth client** in your provider with:

   - A **client ID** and **client secret**
   - **Redirect URI** set to `http://localhost:5001/auth/callback/oidc`
   - **Grant types**: `authorization_code` (and optionally `refresh_token`)
   - **Scopes**: configured as needed by your provider
3. **Three endpoint URLs** from your provider:

   - Authorization endpoint (e.g., `https://sso.example.com/realms/myrealm/protocol/openid-connect/auth`)
   - Token endpoint (e.g., `https://sso.example.com/realms/myrealm/protocol/openid-connect/token`)
   - Introspection endpoint (e.g., `https://sso.example.com/realms/myrealm/protocol/openid-connect/token/introspect`)
4. **PostgreSQL** — the server stores OAuth tokens in PostgreSQL. Use the included `compose.yaml` to run one locally:

   ```bash
   docker compose up -d postgres
   ```

## Local Development With Auth

This mode opens your browser for OAuth login and caches the token in memory.

### Configuration

```bash
# .env
ENABLE_AUTH=True
USE_EXTERNAL_BROWSER_AUTH=True

# SSO provider credentials
SSO_CLIENT_ID=your-client-id
SSO_CLIENT_SECRET=your-client-secret
SSO_CALLBACK_URL=http://localhost:5001/auth/callback/oidc

# SSO provider endpoints (get these from your provider's OIDC discovery document)
SSO_AUTHORIZATION_URL=https://sso.example.com/realms/myrealm/protocol/openid-connect/auth
SSO_TOKEN_URL=https://sso.example.com/realms/myrealm/protocol/openid-connect/token
SSO_INTROSPECTION_URL=https://sso.example.com/realms/myrealm/protocol/openid-connect/token/introspect

# PostgreSQL (for token storage)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

### How the Browser Auth Flow Works

1. You start the server and make a request to a protected endpoint (e.g., `POST /mcp` with a `tools/call`).
2. The `LocalDevelopmentAuthorizationMiddleware` detects no valid token.
3. Your browser opens automatically to the SSO authorization URL.
4. You log in through your SSO provider.
5. The provider redirects back to `http://localhost:5001/auth/callback/oidc` with an authorization code.
6. The server exchanges the code for an access token and stores it in memory.
7. Subsequent requests use the cached token automatically.

### Finding Your Provider's Endpoint URLs

Most OIDC providers publish a discovery document at:

```
https://<your-provider>/.well-known/openid-configuration
```

Look for these fields in the JSON response:

| Discovery field            | Maps to env var           |
| -------------------------- | ------------------------- |
| `authorization_endpoint` | `SSO_AUTHORIZATION_URL` |
| `token_endpoint`         | `SSO_TOKEN_URL`         |
| `introspection_endpoint` | `SSO_INTROSPECTION_URL` |

## Production Auth

In production, clients send a bearer token in the `Authorization` header. The server validates it via the introspection endpoint.

### Configuration

```bash
# .env (or set via ConfigMap / secrets in OpenShift)
ENABLE_AUTH=True
USE_EXTERNAL_BROWSER_AUTH=False

SSO_CLIENT_ID=your-client-id
SSO_CLIENT_SECRET=your-client-secret
SSO_CALLBACK_URL=https://your-mcp-server.example.com/auth/callback/oidc
SSO_AUTHORIZATION_URL=https://sso.example.com/realms/myrealm/protocol/openid-connect/auth
SSO_TOKEN_URL=https://sso.example.com/realms/myrealm/protocol/openid-connect/token
SSO_INTROSPECTION_URL=https://sso.example.com/realms/myrealm/protocol/openid-connect/token/introspect
```

### How Production Auth Works

1. Client obtains a token from the SSO provider (outside of this server).
2. Client sends requests with `Authorization: Bearer <token>` header.
3. The `AuthorizationMiddleware` extracts the token and calls the introspection endpoint.
4. If the token is valid, the request proceeds. If not, the server returns 401.

## Environment Variables Reference

| Variable                      | Required When | Default   | Description                                     |
| ----------------------------- | ------------- | --------- | ----------------------------------------------- |
| `ENABLE_AUTH`               | Always        | `True`  | Master switch for authentication                |
| `USE_EXTERNAL_BROWSER_AUTH` | Auth enabled  | `False` | Enables browser-based OAuth for local dev       |
| `SSO_CLIENT_ID`             | Auth enabled  | `""`    | OAuth client ID from your provider              |
| `SSO_CLIENT_SECRET`         | Auth enabled  | `""`    | OAuth client secret from your provider          |
| `SSO_CALLBACK_URL`          | Auth enabled  | `""`    | OAuth redirect URI (must match provider config) |
| `SSO_AUTHORIZATION_URL`     | Auth enabled  | `""`    | Provider's authorization endpoint               |
| `SSO_TOKEN_URL`             | Auth enabled  | `""`    | Provider's token endpoint                       |
| `SSO_INTROSPECTION_URL`     | Auth enabled  | `""`    | Provider's token introspection endpoint         |
| `SESSION_SECRET`            | Production    | `None`  | Secret key for session middleware               |
| `COMPATIBLE_WITH_CURSOR`    | Cursor IDE    | `False` | Enables Cursor-compatible OAuth2 flow           |
| `POSTGRES_HOST`             | Auth enabled  | `None`  | PostgreSQL host for token storage               |
| `POSTGRES_PORT`             | Auth enabled  | `None`  | PostgreSQL port                                 |
| `POSTGRES_DB`               | Auth enabled  | `None`  | PostgreSQL database name                        |
| `POSTGRES_USER`             | Auth enabled  | `None`  | PostgreSQL username                             |
| `POSTGRES_PASSWORD`         | Auth enabled  | `None`  | PostgreSQL password                             |

## Troubleshooting

### 401 Unauthorized on tool calls

**Cause:** Auth is enabled but SSO is not configured.

**Fix:** Either disable auth or configure a provider:

```bash
# Option A: disable auth
ENABLE_AUTH=False

# Option B: configure SSO (see sections above)
```

### Empty SSO URLs cause silent failures

If `SSO_AUTHORIZATION_URL`, `SSO_TOKEN_URL`, or `SSO_INTROSPECTION_URL` are empty strings (the default), the OAuth flow will fail. Ensure all three are set when auth is enabled.

### Callback URL mismatch

The `SSO_CALLBACK_URL` must exactly match the redirect URI registered in your SSO provider. For local development, this is typically:

```
http://localhost:5001/auth/callback/oidc
```

### Browser does not open (local dev mode)

When `USE_EXTERNAL_BROWSER_AUTH=True`, the server calls `webbrowser.open()`. This may not work in headless environments (containers, SSH sessions). Use production auth mode instead.

### PostgreSQL connection errors

Auth modes require PostgreSQL for token storage. Ensure PostgreSQL is running:

```bash
docker compose up -d postgres
```

### "ENABLE_AUTH defaults to True" surprise

The code default for `ENABLE_AUTH` is `True`. If you delete or skip the `.env` file, auth activates automatically. Always copy `.env.example` to `.env`:

```bash
cp .env.example .env
```
