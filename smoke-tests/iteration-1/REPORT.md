# OpenKT plugin bundle — smoke-test iteration 1

**Date:** 2026-05-22
**Bundle:** `/home/ubuntu/openkt-plugins/claude-code/openkt/` at commit `517127c` (main)
**Goal:** Verify the bundle works end-to-end against real Claude Code after the `direction-tracker` skill was added.

## Environment

| | |
|---|---|
| `claude` binary | `/home/ubuntu/.local/bin/claude` |
| `claude` version | `2.1.149 (Claude Code)` |
| `kt` binary | `/home/ubuntu/openkt-cli/openkt` |
| `kt` version | `v0.0.0-dev (a2f9ad9)` (built from `feat/agent-callable-cli`) |
| `OPENKT_TOKEN` | present (`~/.openkt/token` non-empty, 790 bytes) |
| User (from auth `/me`) | `dev@openkt.ai` |

## Results

| # | Test | Verdict | One-line evidence |
|---|------|---------|---|
| 1 | Plugin loads cleanly | PASS | Exit 0, stdout `plugin loaded`, stderr empty |
| 2 | Local MCP (`kt mcp serve`) reachable | PASS | `kt_doctor` returned 4 detected harnesses (claude_code, cursor, codex, opencode) via stdio MCP |
| 3 | Skill discoverability | PASS | All 4 skills surfaced under `openkt:` namespace (memory-doctor, memory-recall, direction-tracker, memory-curator) + 4 slash commands |
| 4 | direction-tracker activates on multi-thread prompt | PASS | Response opened with `> **Drift flag:** You're currently on Pool 1…added as SEED…say "park it"…` AND answered the hero image question |
| 5 | Remote MCP works with OPENKT_TOKEN | PASS | `kt_recall` returned real memory content (E2E verification entry, similarity 0.31, kind `incident`) — no 401, no auth error |

**Overall: 5/5 PASSED**

## Flakiness / transient errors

None observed. Every run completed inside its timeout budget. No retries needed. No network errors.

## Plugin-load warnings

None. All five `claude --print` invocations produced empty stderr. `grep -iE 'warning|deprecat|error'` across all stdout+stderr returned zero matches. The bundle loads cleanly with no manifest, schema, or migration noise.

## Observations worth flagging (non-blocking)

1. **Recall card counter bug (Test 5):** Claude noted that the rendered recall card showed `"0 memories matched"` while the JSON payload returned 1 result. The smoke test still passes because the actual content was returned, but the user-facing card counter looks broken for low-similarity matches (0.31). Likely a threshold-mismatch between the card renderer and the underlying recall API. Worth a follow-up ticket, not a smoke-test failure.

## Recommendation

**Ship as-is.** All five capability layers — plugin manifest, stdio MCP server, skill discovery, the new direction-tracker skill, and the remote authenticated MCP path — work end-to-end. The only observation is a minor cosmetic issue in the recall card renderer, which is downstream of the bundle and doesn't affect installability or core function.

The `direction-tracker` skill addition (commit 517127c) integrates cleanly: it surfaces in the skill list and activates on the canonical multi-thread prompt without disrupting any existing behavior.
