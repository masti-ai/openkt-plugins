---
name: memory-recall
description: Look up memories from the OpenKT knowledge base when the user references a past decision, you suspect there's prior context, or you're about to repeat work the team has already done.
---

# OpenKT memory recall

The UserPromptSubmit hook auto-injects relevant memories on every turn,
but that's a similarity-based broad sweep. When you need a **targeted**
lookup — to verify a fact, find a specific decision, or check for an
anti-pattern before acting — use the explicit recall tool.

## When to recall explicitly

  - User says "we've talked about this before" → recall with their topic
  - You're about to make a decision the team may have already made →
    recall for similar decisions first
  - User asks "what did we decide about X" → recall with X as the query
  - Mid-task, you suspect a relevant pattern exists → recall with the
    task signature ("how to add a new MCP tool")
  - Before suggesting an approach, check for anti-patterns → recall
    with `--kind=anti-pattern`

## Tools at your disposal

- `kt_recall(query="...", kind=?, limit=?)` (MCP, preferred — same as
  the hook uses)
- `kt_search_memories(query="...")` (read-only, doesn't bump recall
  counters; for browse/preview)
- `kt recall "<query>" [--kind=K] [--limit=N]` (shell fallback)

`kt_recall` (and the MCP equivalent) is **scope-aware**: it only
returns memories for the current project. You don't need to pass a
project ID; the CLI resolves it from `.openkt/manifest.json`.

## Format guide for queries

Be specific. Generic queries return generic noise:
  - BAD:  `kt recall "config"`
  - GOOD: `kt recall "supabase env vars in dashboard build pipeline"`
  - GOOD: `kt recall "rate limiting on signin endpoint"`

If the first query is too broad, refine: pull a distinctive phrase or
identifier from the conversation (an env var name, a file path, a
commit shorthand) and re-query.

## Reading the result

Each match comes with:
  - `id` (use for `kt forget` if you need to retract)
  - `kind` (decision / pattern / etc.)
  - `content` (the memory body)
  - `importance` (0-1, server-assigned)
  - `recall_count` (how often this memory has been hit)
  - `created_at` (when it was written)

Weight high-importance + recent memories most heavily when reasoning.
