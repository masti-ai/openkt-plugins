---
name: memory-curator
description: Proactively curate OpenKT memories during a session — detect when a decision, anti-pattern, incident, or non-obvious fact has just been established and write it via `kt remember` so the next agent inherits the context.
---

# OpenKT memory curator

You are responsible for **persisting knowledge that future agents will
need.** OpenKT auto-recalls memories on every prompt, but it can't
auto-write them — that's on you.

## When to trigger a memory write

The moment one of these happens in the conversation, call `kt remember`
(or the `kt_save_memory` MCP tool) with the right kind:

- **Decision made** ("we chose X over Y because Z") → `--kind=decision`
- **Anti-pattern observed** ("never do A; it caused N hours of debugging")
  → `--kind=anti-pattern`
- **Incident with root cause + fix** ("symptom S was caused by C; fix
  is F") → `--kind=incident`
- **Pattern that worked** ("the right way to do P is via Q") →
  `--kind=pattern`
- **Non-obvious config / constraint** ("staging DB is on port 5433")
  → `--kind=context`
- **Domain fact agents shouldn't have to re-derive** ("customer C is
  special-cased because of historical reason H") → `--kind=context`

## Format guide

Memory content should be **self-contained** — a future agent reading
just that line should understand it without context from this session:

  - GOOD: `"chose drizzle over prisma for openkt-bff/sgs-api on 2026-05-15
            — drizzle's TS inference matches our generated supabase types
            without an extra codegen step. commit 9bcbf1d."`
  - BAD:  `"we picked option A"` (which option? for what? when?)

Include:
  - WHAT was decided / observed
  - WHY (the reasoning is the most valuable part)
  - Anchors (commit SHA, PR number, file path) when applicable
  - Date if the decision is time-bounded

## Cadence

Default to writing more, not less. Storage is cheap; a future session
re-deriving the same insight is expensive. A typical multi-turn
session should produce 1-3 memories.

DO NOT:
  - Mirror what the user explicitly stated (the CAPTURE hook handles that)
  - Save trivial things ("user said hi") — only durable knowledge
  - Save partial / WIP decisions; wait until the call is made

## Tools at your disposal

- `kt_save_memory(content=..., kind=...)` (MCP, preferred)
- `kt remember "<text>" --kind=<kind>` (shell fallback)

Both hit the same backend. The MCP tool returns the created Memory's
ID so you can reference it later if needed.
