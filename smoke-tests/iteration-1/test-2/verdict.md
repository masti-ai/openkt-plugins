# Test 2: Local MCP server (kt mcp serve) reachable

**Verdict:** PASS

**Evidence:** `kt_doctor` returned via stdio MCP and reported 4 detected harnesses (claude_code, cursor, codex, opencode) with binary paths and config-dir signals. Auth `/me` resolved to `dev@openkt.ai`. Proves stdio MCP roundtrip works.
