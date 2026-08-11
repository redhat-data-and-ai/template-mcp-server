# MCP 2026-07-28 Specification — SEP Implementation Changelog

Tracks which SEPs from the MCP 2026-07-28 specification have been implemented
and what was deprecated or removed.

> Detailed code changes are documented in [`MCP_SEP_AUDIT_REPORT.docx`](MCP_SEP_AUDIT_REPORT.docx).

---

## SEP Implementation Status

All 19 SEPs from the 2026-07-28 sprint roadmap are **fully implemented**.

| # | SEP | Description | Status |
|---|-----|-------------|--------|
| 1 | SEP-414 | W3C Trace Context — `traceparent`, `tracestate`, `baggage` propagation through HTTP headers and MCP `_meta` fields | **Done** |
| 2 | SEP-837 | `application_type` in Dynamic Client Registration — infers `native` vs `web` from redirect URIs | **Done** |
| 3 | SEP-991 / PR-2858 | CIMD endpoint (`GET /auth/client-metadata/{id}`) + DCR `Deprecation: true` header | **Done** |
| 4 | SEP-2106 | JSON Schema 2020-12 — `inputSchema` root must be `type: object`, `outputSchema` validated, `$ref` resolution within `$defs` | **Done** |
| 5 | SEP-2133 | Extensions framework — reverse-DNS identifiers in `capabilities.extensions` via `ExtensionRegistry` | **Done** |
| 6 | SEP-2207 | OIDC `offline_access` exclusion — not in `scopes_supported`, refresh tokens via `grant_types_supported` | **Done** |
| 7 | SEP-2243 | `Mcp-Method` / `Mcp-Name` header validation — rejects mismatches with `-32020 HEADER_MISMATCH` | **Done** |
| 8 | SEP-2260 | Server request association — no standalone pushes; verified structurally (tools-only architecture) | **Done** |
| 9 | SEP-2322 | Multi Round-Trip Requests — `resultType: "complete"` injected into every `tools/call` response | **Done** |
| 10 | SEP-2352 | Client Credential Binding — tokens tagged with issuer, grants verify issuer match | **Done** |
| 11 | SEP-2468 | `iss` in Authorization Responses — RFC 9207 `iss` parameter in redirect, `authorization_response_iss_parameter_supported: true` | **Done** |
| 12 | SEP-2549 | Deterministic `tools/list` ordering + TTL/Cache Scope metadata on each tool | **Done** |
| 13 | SEP-2567 | Session removal — `stateless_http=True`, no `Mcp-Session-Id`, no `Last-Event-ID` resumability | **Done** |
| 14 | SEP-2575 | Stateless MCP — `server/discover` replaces initialize, removed methods return `-32023`, per-request `_meta.logLevel` | **Done** |
| 15 | SEP-2577 | Deprecate Roots, Sampling, Logging — registered in `deprecation_registry` with migration guidance | **Done** |
| 16 | SEP-2596 | Feature lifecycle / deprecation policy — `DeprecationRegistry` with active/deprecated/removed states | **Done** |
| 17 | SEP-1865 | MCP Apps extension — `AppRegistry` with `apps/list` and `apps/get` RPC handlers under `io.modelcontextprotocol/ui` | **Done** |
| 18 | SEP-2663 | Tasks extension — `TaskStore` with full lifecycle (`pending`→`running`→`completed`/`failed`/`cancelled`), `tasks/get`/`update`/`cancel` RPC handlers under `io.modelcontextprotocol/tasks` | **Done** |
| 19 | Error codes | Allocation policy + renumbering — implementation-defined (`-32000` to `-32099`), MCP-reserved (`-32600` to `-32699`) | **Done** |

### Additional Spec Features (not separate roadmap SEPs)

| Feature | How It's Covered | Status |
|---------|------------------|--------|
| Streamable HTTP transport | Default transport via `MCP_TRANSPORT_PROTOCOL=streamable-http`; `FastMCP.http_app()` | **Done** |
| STDIO transport | Alternative transport via `MCP_TRANSPORT_PROTOCOL=stdio`; `FastMCP.run_stdio_async()` | **Done** |
| OAuth metadata discovery (RFC 8414) | `/.well-known/oauth-protected-resource` + `/.well-known/oauth-authorization-server` | **Done** |
| Tool output schemas (SEP-2210) | Covered by SEP-2106: `output_schema` kwarg on all 4 tools | **Done** |
| Structured JSON content (SEP-2221) | Covered by SEP-2106: FastMCP auto-wraps dict returns as `structuredContent` | **Done** |

**Progress: 19/19 Done**

---

## Deprecations & Removals

Features deprecated or removed in the 2026-07-28 specification, and how they are handled in this codebase.

### Removed Features

| Feature | Replacement | How It's Handled |
|---------|-------------|-----------------|
| Sessions (`Mcp-Session-Id`) | Stateless HTTP | `stateless_http=True` disables session tracking (SEP-2567) |
| Initialize handshake | `server/discover` + `_meta` fields | `server/discover` RPC returns capabilities directly (SEP-2575) |
| `ping` | N/A | Rejected with `-32023 METHOD_NOT_SUPPORTED` (SEP-2575) |
| `logging/setLevel` | `logLevel` in `_meta` per-request | Rejected at middleware; per-request `_meta.logLevel` implemented (SEP-2575) |
| `notifications/roots/list_changed` | N/A | Rejected with `-32023 METHOD_NOT_SUPPORTED` (SEP-2575) |
| SSE stream resumability | Client re-issues request | `stateless_http=True` disables `Last-Event-ID` handling (SEP-2567) |
| `elicitation/create` | MRTR (SEP-2322) | Registered as removed in `deprecation_registry`; MRTR replaces it |
| `elicitation` notification | MRTR retry pattern | Registered as removed in `deprecation_registry` |
| `tasks/list` | `tasks/get` (SEP-2663) | Rejected with `-32023` via `_REMOVED_METHODS` |

### Deprecated Features

| Feature | Replacement | How It's Handled |
|---------|-------------|-----------------|
| DCR (`POST /auth/register`) | CIMD (`GET /auth/client-metadata/{id}`) | CIMD endpoint implemented; `/auth/register` returns `Deprecation: true` header (SEP-991) |
| HTTP+SSE transport | Streamable HTTP | N/A — server already uses Streamable HTTP; never had HTTP+SSE |
| Roots | Tool params, resource URIs | Registered in `deprecation_registry` with migration guidance; server never registered roots |
| Sampling | Direct LLM provider APIs | Registered in `deprecation_registry` with migration guidance; server never registered sampling handlers |
| Logging | stderr / OpenTelemetry | Registered in `deprecation_registry` with migration guidance; uses stderr via `pylogger` |
| `includeContext` values | Omit or use `"none"` | N/A — server never used `includeContext`; registered in registry for completeness |

**Totals:** `deprecation_registry` has 15 entries (9 removed + 6 deprecated). `_REMOVED_METHODS` frozenset blocks 4 methods at the middleware level.
