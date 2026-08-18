# Session status (local recovery)

> **Durable wiki:** `~/.local/share/second-brain/wiki/work/template-mcp-server.md`
> Say **"read second brain template-mcp-server"** in a new Cursor chat to reload context.

Last updated: 2026-08-18

## Open work

| Item | Action |
|------|--------|
| [PR #81](https://github.com/redhat-data-and-ai/template-mcp-server/pull/81) | DCO fixed on `deep-agent`; await CI/review |
| [PR #80](https://github.com/redhat-data-and-ai/template-mcp-server/pull/80) | Awaiting merge to `main` (CI green) |
| MCP 2026-07-28 migration | Post-merge spike — see wiki; **not** a blocker for #80/#81 |

## Branch map

- `refactor/tools-config-as-code` → `main` (template demo tools)
- `deep-agent` → `upstream/deep-agent` (BMI, email, web search + OAuth + Makefile fix)

## Quick verify

```bash
cd ~/github/template-mcp-server
git checkout deep-agent && git log --oneline -5
pre-commit run --all-files && make test
```

## Local MCP

- Server: `http://localhost:5010/mcp` (`~/.cursor/mcp.json` → `template-mcp-server`)
- Port 5001 is often Presidio, not this server

## MCP 2026 spec

Spec migration (stateless core, header routing) is tracked in second brain [intel/mcp.md](file:///Users/whenry/.local/share/second-brain/wiki/intel/mcp.md). Protocol layer is FastMCP; config-as-code PRs do not need redesign.
