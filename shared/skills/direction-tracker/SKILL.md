---
name: direction-tracker
description: Track parallel threads ("pools") of work in long conversations by maintaining a project-local DIRECTIONS.md file. Use this skill whenever the user pulls on multiple threads in one session, mentions ADHD or "I get distracted", asks "where am I" / "what am I working on" / "what was I doing", starts a new direction that may not fit the leading work, or explicitly types /directions. Especially load-bearing for founders, multi-product builders, and anyone whose AI conversations naturally accumulate parallel workstreams. The skill auto-classifies new directions into themed pools, flags drift inline ("you're on Pool 1 — this prompt is pulling toward a new Pool 4, intentional?"), and surfaces a live pool view on demand. Make sure to use it any time a conversation shows signs of multi-threading, even if the user doesn't name the skill or the file.
---

# Direction Tracker

## What this skill does

Memory tools store **facts**. This skill stores **attention** — which threads of work the user is currently holding, which one is leading, which ones are parked or drifting.

In a long session, conversations naturally accumulate parallel directions: a CLI fix, a research dispatch, a plugin packaging task, a marketing thought. By prompt 20, the user has forgotten three of them and is silently being led wherever the latest prompt points. This skill turns that silent drift into a visible, navigable surface.

The skill maintains a single project-local file — `DIRECTIONS.md` — and updates it across the conversation. The user can `cat` it any time to see every thread they've pulled on, grouped into themes ("pools"), each with a status flag.

This is not a TODO list. The user enters nothing manually. The skill captures from natural conversation and renders the live view on demand.

## When to use this skill

Trigger whenever ANY of the following holds:

1. **Multi-thread session.** The conversation has already touched 3+ distinct topics. Look at the last 10-15 turns. If they span more than 2 themes, switch this on.
2. **Explicit invocation.** User types `/directions`, `/pools`, "show me where I am", "what am I working on", "what was I doing", "summarize my open threads", "I lost track".
3. **Pivot signal.** User says "actually let's pivot", "let me also", "wait can we also", "switch gears", "now let's talk about", or otherwise pulls hard on a thread orthogonal to the leading work.
4. **Self-aware ADHD signal.** User mentions ADHD, "I get distracted", "I keep jumping", "my brain is everywhere", "too many things".
5. **First-time-in-project.** No `DIRECTIONS.md` exists yet AND any of (1)–(4) hold. Create the file and seed it from conversation history.

When NONE of these hold (focused single-thread session, simple debugging task, etc.), **do nothing**. The skill is opt-in by signal, not always-on.

## The DIRECTIONS.md format

The file lives at the project root (or `~/.openkt/directions/<project_id>.md` if you can detect an OpenKT project). Format:

```markdown
# Directions — <user-name-or-project> active threads (living doc)

**Last updated:** YYYY-MM-DD

## Pool N — <theme name>
*Theme: <one-line theme description>.*

- <entry one-liner> — `STATUS`
- <entry one-liner> — `STATUS`

## Pool N+1 — <theme name>
...

## What's drifting

- <thread mentioned but no follow-up> — `DRIFT`

## What's the leading edge right now?

<one-paragraph synthesis of where the focus currently is, ideally
quoting the user's own words from the most recent direction-setting
message>
```

### Status flags (use these literally — they're machine-greppable)

- `LEADING` — active focus right now
- `PARKED` — mentioned, deprioritized, not abandoned
- `BLOCKED` — waiting on something external
- `DONE` — completed
- `DRIFT` — mentioned but no follow-up; flag for user
- `SEED` — idea, not yet scoped
- `RESEARCH` — investigation in flight

## Workflow

### On every user prompt (silent layer)

1. **Look for DIRECTIONS.md.** Search project root, then `.openkt/directions/`, then home dir if no project. If it exists, read it before doing anything else with the prompt. The pools become standing context for your reply.
2. **Classify the prompt.** Does it fit an existing pool, open a new pool, ask for the pool view, or just continue the leading thread?
   - **Continues leading thread**: no DIRECTIONS.md update needed. Just answer.
   - **Adds an entry to an existing pool**: append the entry under the right pool with a status flag.
   - **Opens a new pool**: create the pool with a short theme description, add the entry under it, and **flag this inline** if the new pool is orthogonal to the leading edge (see "Drift detection" below).
   - **Asks for pool view**: render the live view inline (see "Rendering the pool view").
3. **Update if needed.** Use `Edit` or `Write` to persist. Don't ask permission for these edits — the user expects automatic maintenance. Be terse in commit-style entries (one line per thread).

### Drift detection (the load-bearing call)

When a new prompt opens a pool **orthogonal** to the current leading edge, surface drift inline at the top of your reply:

> "Note: you're currently on Pool 1 (CLI integration). This prompt is pulling toward a new Pool 4 (analytics). I'll add it to DIRECTIONS.md as a SEED — say 'pivot' if you want me to actually switch focus, or 'park it' if you want to stay on Pool 1."

Then proceed with the user's prompt regardless (don't block on the question). The user can either course-correct or wave you on.

**Orthogonal** means: the new prompt's theme has no shared concept/file/system with the leading pool. A debugging prompt while you're already debugging is NOT drift. A "let me think about pricing" prompt during CLI debugging IS drift.

**Calibrate sensitivity.** First-time drift flagging in a session: lean toward flagging. After 3+ flags where the user said "follow it" or didn't course-correct, dial it down — they're operating in genuine multi-thread mode. Save your drift flags for the truly orthogonal pivots.

### Rendering the pool view

When the user invokes `/directions` or asks "where am I":

1. Read DIRECTIONS.md.
2. Render it in chat with light formatting (preserve pool headers, status flag chips, the "What's the leading edge" paragraph). Don't editorialize beyond what the file says.
3. End with a one-line synthesis question: "Want to refocus on Pool X, or stay on the current edge?"

### Maintaining DIRECTIONS.md across long sessions

Three discipline rules:

1. **Never silently drop entries.** Status flags exist precisely so threads stay visible even after they're done. Mark as `DONE`/`PARKED`/`BLOCKED` rather than deleting.
2. **Convert relative timestamps to absolute.** "Today" → "2026-05-22". "Earlier this session" → "earlier in session 2026-05-22". This is essential because DIRECTIONS.md will be re-read in future sessions.
3. **Quote the user's own framing in pool theme descriptions.** When the user says "just focus on the plugin so installation is easier," that exact framing should appear under the relevant pool. Don't paraphrase user intent — preserve it.

## What makes this different from a TODO list

A TODO list is enter-by-hand and read-on-demand. Direction-tracker is:

- **Captured automatically** from conversation, no UI to maintain
- **Agent-aware** — both you and the user see the same pools, so the agent can actively flag drift, not just respond to queries
- **Project-scoped** so different products don't pollute each other's threads
- **Visible** — `cat DIRECTIONS.md` works from any session, future or present

## Examples

**Example 1 — first-time multi-thread detection:**

User has been chatting for 15 turns about a Go CLI refactor. New message: *"Actually let me also think about the marketing landing page redesign."*

Skill detects pivot signal ("let me also") + theme orthogonality (CLI vs marketing). DIRECTIONS.md doesn't exist yet. Action:

1. Create DIRECTIONS.md with Pool 1 = "CLI refactor" (seeded from history) and Pool 2 = "Marketing landing page".
2. Inline drift flag: "Note: started Pool 2 (Marketing landing) — Pool 1 (CLI refactor) is your current leading edge. I'll add Pool 2 as `SEED`; say 'pivot' to switch focus, or 'park it' to come back later."
3. Answer the marketing question normally (don't block on the flag).

**Example 2 — explicit invocation:**

User: *"where am I in all this?"*

Skill reads DIRECTIONS.md and renders the pool view inline. No drift detection needed (this isn't a new direction, it's a query about existing state).

**Example 3 — focused single-thread debugging:**

User has been debugging a Postgres connection bug for 20 turns. They ask another question about the same bug. **Do nothing.** No DIRECTIONS.md update, no drift flag. This skill is opt-in by signal.

## References

- `references/pool-classifier.md` — how to decide whether a prompt extends an existing pool, opens a new one, or just continues the leading thread
- `references/drift-detection.md` — calibration guide for when to flag drift vs follow silently
- `references/format.md` — DIRECTIONS.md format spec with edge cases (cross-pool entries, archived pools, multi-leading state)
- `templates/DIRECTIONS.md.template` — starter template you can copy when seeding a fresh file

## Why this is OpenKT-shaped

OpenKT (Open Knowledge Transfer) is the persistent context layer between humans and their agents. Attention IS a kind of context — arguably the most volatile kind, since it changes per turn. By bundling direction-tracking into the OpenKT plugin, every harness (Claude Code, Codex, Hermes) gets meta-direction-awareness for free, on the same hook infrastructure that already runs on every prompt.

For ADHD founders and anyone running multiple workstreams concurrently, this turns OpenKT from "memory" into "memory + attention" — two products in one skill bundle.
