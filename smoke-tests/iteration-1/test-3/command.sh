#!/bin/bash
# Test 3: Skill discoverability
timeout 30 claude --print --plugin-dir /home/ubuntu/openkt-plugins/claude-code/openkt \
    --dangerously-skip-permissions \
    "List the skills available to you under the openkt plugin namespace. Just the names."
