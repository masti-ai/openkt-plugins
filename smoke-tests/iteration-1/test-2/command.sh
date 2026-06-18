#!/bin/bash
# Test 2: Local MCP server reachable
cat > /tmp/smoke-mcp-config.json <<'EOF'
{
  "mcpServers": {
    "openkt-local": {
      "command": "/home/ubuntu/openkt-cli/openkt",
      "args": ["mcp", "serve"]
    }
  }
}
EOF
timeout 60 claude --print --strict-mcp-config --mcp-config /tmp/smoke-mcp-config.json \
    --dangerously-skip-permissions \
    "Call the kt_doctor tool from the openkt-local MCP server and tell me what harnesses it detected. Just paste the doctor output."
