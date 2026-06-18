#!/bin/bash
# Test 4: direction-tracker activates on multi-thread prompt
timeout 90 claude --print --plugin-dir /home/ubuntu/openkt-plugins/claude-code/openkt \
    --dangerously-skip-permissions \
    "I've been working on the CLI auth refactor for a while. Let me also start thinking about a marketing landing page redesign. Where should the hero image go?"
