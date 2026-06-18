#!/bin/bash
# Test 1: Plugin loads cleanly
timeout 30 claude --print --plugin-dir /home/ubuntu/openkt-plugins/claude-code/openkt \
    --dangerously-skip-permissions \
    "say 'plugin loaded' if you're ready"
