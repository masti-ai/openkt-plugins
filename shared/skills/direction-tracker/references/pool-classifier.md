# Pool Classifier

How to decide what to do with a new user prompt: extend an existing pool, open a new pool, render the view, or do nothing.

## The classification flow

For every user prompt, ask in this order:

1. **Is this a view query?** ("/directions", "where am I", "what was I doing", "show me my pools")
   → Render the live pool view from DIRECTIONS.md. Don't append, don't classify further.

2. **Is the user asking a meta-question about DIRECTIONS.md?** ("park Pool 2", "mark Pool 1 as DONE", "merge Pool 3 into Pool 1", "what's drifting")
   → Edit DIRECTIONS.md accordingly. Don't trigger drift detection on this prompt.

3. **Does the prompt continue the leading thread?** Read the "What's the leading edge" paragraph + the LEADING entries in the active pool. If the prompt is naturally inside that scope:
   → Do nothing. Answer normally.

4. **Does the prompt add to a non-leading pool?** E.g., the leading edge is CLI work but the user mentions one of the PARKED items in Pool 4:
   → Add the entry under Pool 4 with the right status flag. Don't flag drift (this is the user catching up on a known thread, not pivoting).

5. **Does the prompt open a new pool?** Theme has no shared concept with any existing pool:
   → Create the pool with a one-line theme description. Add the entry under it. **Flag drift inline** if orthogonal to the leading edge (see `drift-detection.md`).

## What counts as "shared concept"

Two themes share a concept when they touch:
- The same file or system (e.g., `wire.go`, the auth module, the dashboard)
- The same user-facing surface (CLI, web app, mobile)
- The same external service (Supabase, AWS, GitHub)
- The same workflow stage (planning, building, debugging, shipping)

Themes do NOT share a concept when they touch:
- Different products (CLI vs marketing landing)
- Different layers (frontend pixel work vs backend job processing)
- Different stakeholder types (engineering vs sales vs design)

## Edge cases

### The "let me also" pattern

User has been on Pool 1 for 10 turns, then says "let me also work on X". The "also" is the signal: the user is consciously adding a parallel thread, not pivoting. Action:

- Create Pool N (new) with X as the theme.
- Mark Pool 1 as `LEADING` still (the user didn't say "drop Pool 1").
- Mark Pool N entries as `SEED` or `PARKED` until the user signals attention shift.
- Flag drift only if X is genuinely orthogonal to Pool 1.

### The "actually let's switch" pattern

User explicitly pivots: "actually let's focus on X now". Action:

- Move Pool 1's LEADING entries to PARKED (preserve them).
- Open Pool N for X (if new) or surface Pool M (if X matches an existing parked pool) and mark it LEADING.
- Don't flag drift — the user gave explicit consent to pivot.

### Sub-thread of a leading pool

User is on Pool 1 (CLI work). They ask: "while we're at it, can we also fix the auth bug?" If the auth bug is part of CLI (it is), this is a sub-thread, not a new pool. Add the auth-bug entry under Pool 1 with `LEADING` status alongside the existing CLI entries.

### One prompt, multiple directions

User: "Let me also start on analytics, and we should sync with the design team about the new colors, and oh I also want to fix the deployment pipeline." Three new threads in one message.

Action: open three pools (or merge into existing). Don't flag drift on each individually — just note at the top of your reply: "Added 3 new pools (Pool 4 Analytics, Pool 5 Design sync, Pool 6 Deploy pipeline). Pool 1 (current LEADING) is still active. Which is the new leading edge?"

## Sensitivity tuning

If the user has corrected you (e.g., "no, that's the same pool", or "stop flagging drift"), update DIRECTIONS.md's drift-detector calibration. Specifically:

- Add a small `## Drift sensitivity` section to the bottom of DIRECTIONS.md with a 1-3 calibration note from the user. Future prompts read this.
- Default sensitivity: medium (flag the obvious orthogonal pivots, ignore sub-threads).
- User overrides: "loose" (flag everything), "tight" (flag only when explicitly asked), "medium" (default).

## Anti-patterns to avoid

- **Flagging drift on every prompt.** Annoying, useless. Save it for the genuinely orthogonal pivots.
- **Renaming pools mid-session.** Pool numbers are stable; only the theme description can be refined.
- **Deleting entries.** Use status flags (`DONE`, `PARKED`, `DRIFT`) instead. Visibility is the point.
- **Editorializing user intent.** Quote the user's framing in pool theme descriptions verbatim where possible.
