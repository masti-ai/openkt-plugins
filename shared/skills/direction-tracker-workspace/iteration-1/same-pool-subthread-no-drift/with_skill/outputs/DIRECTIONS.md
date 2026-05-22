# Directions — test project

**Last updated:** 2026-05-22

## Pool 1 — CLI auth refactor
*Theme: make the kt CLI agent-callable with JSON output and stable exit codes.*

- Non-interactive flags on every command — `DONE`
- kt mcp serve with 11 tools — `LEADING`
- PR #30 awaiting merge — `LEADING`
- JWT refresh edge case: token rotated mid-request — `LEADING`

## What's the leading edge right now?

User's framing: "Now let me also fix the JWT refresh edge case where the token is rotated mid-request. We're already in the auth refactor, this should slot in."

So **Pool 1 (CLI auth refactor)** is still the focus — the JWT refresh fix slots in as a sub-thread of the same pool.
