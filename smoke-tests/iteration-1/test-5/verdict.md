# Test 5: Remote MCP works with OPENKT_TOKEN

**Verdict:** PASS (with a minor observation)

**Evidence:** `kt_recall` via the remote openkt MCP returned real memory content: "E2E verification 2026-05-15: MCP at api.openkt.ai/mcp works end-to-end from opencode, codex, claude-code" (kind `incident`, similarity 0.31). No 401, no "no token" error.

**Observation:** Claude noted "the recall card itself rendered as '0 memories matched', but the JSON payload returned 1 result." Worth flagging — the user-facing recall card may have a counter bug when results have low similarity. Minor cosmetic issue, not a smoke-test failure.
