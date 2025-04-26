# Setup Environment
```bash
uv init <project_name>
cd <project_name>
uv add "mcp[cli]" httpx
```

# Run MCP Inspector
npx @modelcontextprotocol/inspector
uv run mcp dev <mcp_sse_server.py>

# Start SSE MCP Server
uv run <mcp_sse_server.py>

# Config SSE MCP Server for Cursor, Trae, Claude Desktop
```json
{
  "mcpServers": {
    "<mcp_sse_server>": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8080/sse"
      ]
    }
  }
}
```