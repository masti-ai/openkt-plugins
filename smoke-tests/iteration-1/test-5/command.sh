#!/bin/bash
# Test 5: Remote MCP (api.openkt.ai/mcp) works with token
timeout 60 claude --print --plugin-dir /home/ubuntu/openkt-plugins/claude-code/openkt \
    --dangerously-skip-permissions \
    "Call kt_recall on 'CLI plugin work' through the openkt MCP server. Just give me the top result content."
