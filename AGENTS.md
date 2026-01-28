# AI Agent Instructions

## 🤖 AI IDE Instructions (ex. Cursor, Copilot)

**Context for AI:** This project uses `uv` for dependency management and runs a FastMCP server on port 5001. AI agents often fail to restart this server correctly by leaving the old process running.

**⚠️ CRITICAL PROTOCOL: Restarting the Server**
When asked to "restart the server" or "test my changes", you **MUST** follow this exact sequence to avoid `Address already in use` errors:

1.  **Detect Port (Shell Method)**:
    * Do not try to read `.env` directly (it is hidden).
    * Run this command to find the configured port:
      `grep MCP_PORT .env`
    * Extract the number (e.g., 5001) from the output.
1.  **Identify Zombie Processes**:
    * Check for any process holding port 5001.
    * *Command*: `lsof -ti:5001` (macOS/Linux) or `netstat -ano | findstr :5001` (Windows).
2.  **Force Kill**:
    * Do not rely on standard `SIGINT` (Ctrl+C).
    * If a PID is found in step 1, kill it immediately.
    * *Command*: `kill -9 <PID>` (macOS/Linux) or `taskkill /PID <PID> /F` (Windows).
3.  **Verify Cleanup**:
    * Run the check command from Step 1 again to confirm the port is free.
4.  **Start Fresh**:
    * Use `uv` to run the server.
    * *Command*: `uv run python -m template_mcp_server.src.main`

**Verification**
After starting, verify the server is active by querying the health endpoint:
* *Command*: `curl http://localhost:5001/health`

