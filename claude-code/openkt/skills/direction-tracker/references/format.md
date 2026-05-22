# DIRECTIONS.md Format Spec

Canonical layout for the file this skill maintains.

## Top of file

```markdown
# Directions — <project or user> active threads (living doc)

**Last updated:** YYYY-MM-DD

**Purpose:** <2-3 lines on why this file exists — usually: "step-back
view of every direction this conversation has been pulled in,
grouped into themes (pools), with status flags.">
```

The "Purpose" lines are not boilerplate — they tell future-you (and future agents) why this file is here, so it doesn't get accidentally deleted or treated as scratch.

## Pool sections

Each pool is one `## Pool N — <theme>` heading. Pools are numbered 1..N, never renumbered. If you retire a pool, mark it (see "Retiring pools") but keep the number.

```markdown
## Pool 1 — <short theme name>
*Theme: <one-line theme description, ideally quoting the user's own framing>.*

- <entry one-liner> — `LEADING`
- <entry one-liner> — `PARKED`
- <entry one-liner> — `DONE`
```

Theme description format:
- One italicized line
- Quote the user's framing if you have it ("just focus on the plugin so installation is easier")
- Otherwise summarize in concrete user-facing language (not jargon)

Entry format:
- One bullet line
- Lead with the concrete artifact or task
- Status flag at the end, in backticks
- Add detail in parens after the flag if needed: `LEADING` (PR #30 open, awaiting merge)
- Cross-link to other pools as `[[Pool N]]` if the entry depends on another thread

## Status flags

| Flag | Meaning |
|-|-|
| `LEADING` | Active focus right now. At most 1-3 entries per pool. |
| `PARKED` | Mentioned, deprioritized. Will likely return. |
| `BLOCKED` | Waiting on something external (a person, a deploy, an upstream fix). |
| `DONE` | Completed. Keep for visibility; don't delete. |
| `DRIFT` | Mentioned but no follow-up; flagged for user attention. |
| `SEED` | Idea, not yet scoped. |
| `RESEARCH` | Investigation in flight. |

## "What's drifting" section

At the end of the file, before the "Leading edge" synthesis:

```markdown
## What's drifting

(Drift = mentioned but no follow-up across recent turns)
- <thread> — last mentioned <turn ref or date>
- <thread> — last mentioned <turn ref or date>
```

This surfaces threads the user opened and never returned to. Don't auto-promote DRIFT entries — let the user decide whether to PARK them, mark DONE, or follow up.

## "What's the leading edge" section

Last section of the file:

```markdown
## What's the leading edge right now?

<User's most recent direction-setting message, quoted verbatim if
possible: "Just focus on the plugin so installation is easier">

So **Pool <N> (<theme>)** is the focus. Everything else is parked
or routine cleanup.
```

This is the most-read part of the file. Make it concrete. Quote the user.

## Sub-agent dispatch tracking

If the conversation involves dispatching sub-agents to handle pool entries, track them inline:

```markdown
**Active sub-agent dispatches (as of YYYY-MM-DD):**
- Sub-agent N (Pool X): <task one-liner>. <Running in background | PR #M>
```

This is the at-a-glance "who's cooking right now" view.

## Drift sensitivity

If the user has tuned drift-flag sensitivity for this project, persist it:

```markdown
## Drift sensitivity

Calibration: <medium | tight | loose>
Set by user: <date> — "<their explanation>"
```

Future sessions read this and apply.

## Retiring pools

When a pool is fully wrapped:

1. Mark all entries `DONE`
2. Add a `**Retired:** YYYY-MM-DD — <one-line why>` line under the theme
3. Don't renumber; the pool number stays for traceability

Don't delete retired pools from the file. They're navigation aids for future archeology.

## Project root vs OpenKT-scoped

By default, DIRECTIONS.md lives at the project root (next to `package.json` / `Cargo.toml` / `pyproject.toml` / `.git`). 

If you can detect that the project is bound to OpenKT (presence of `.openkt/manifest.json`), prefer `~/.openkt/directions/<project_id>.md` so the file can be synced across machines via the OpenKT memory layer.

If neither applies (user is in a generic shell session), put it at `~/.openkt/directions/global.md`.

Always tell the user which path you chose the first time you create the file.

## Edge cases

### Multi-leading state

It's OK for multiple pools to have `LEADING` entries simultaneously if the user is genuinely parallelizing (e.g., dispatched 2 sub-agents on different pools). Mark each LEADING and add a `**Active parallels:**` line under "What's the leading edge".

### Pool merge

If two pools turn out to be the same theme:
- Pick the lower-numbered one as the survivor
- Move all entries from the higher-numbered one
- Add a line `**Merged from Pool <higher>:** YYYY-MM-DD — <reason>`
- Don't delete the higher-numbered pool heading; mark it `**Retired (merged into Pool N):** YYYY-MM-DD`

### Pool split

If one pool grows two distinct sub-themes:
- Keep the original pool with the original number
- Open a new pool with the next available number
- Add a line `**Split from Pool <orig>:** YYYY-MM-DD — <reason>` under the new pool

## Token budget

Aim for DIRECTIONS.md to stay under ~3000 tokens (~12KB). When it grows beyond that:

1. Move DONE entries to a `## Archive` section at the bottom (one-line each, no detail)
2. Compress PARKED entries that haven't been touched in 30+ days into "see Archive"
3. Keep LEADING + BLOCKED + DRIFT + RESEARCH + recent SEED visible

The file's job is to be readable in 30 seconds.
