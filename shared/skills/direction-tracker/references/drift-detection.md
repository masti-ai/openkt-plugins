# Drift Detection — when to flag, when to follow

The single most user-impactful judgment in this skill: when a new prompt opens a pool orthogonal to the leading edge, do you flag it inline or follow silently?

## The bias

Lean toward **flagging the first orthogonal pivot in a session**. If the user shrugs it off or says "follow it," dial down sensitivity for the rest of the session.

The cost of one over-flagged drift is small (user types "follow it" or ignores the note).
The cost of one missed drift is large (user loses 30 minutes following a tangent before realizing they abandoned the leading edge).

So: lean toward flagging early, calibrate down based on user response.

## Flag template

```
> Note: you're currently on Pool <N> (<theme>). This prompt is
> pulling toward <existing Pool M | a new Pool N+1> (<theme>).
> I'll add it as `<STATUS>` — say 'pivot' if you want to switch
> focus, or 'park it' if you want to stay on Pool <N>.
```

Then proceed with the user's prompt normally. The flag is a side note, NOT a block.

## When to flag — clear yes

- New pool that touches a different product (CLI vs marketing vs server vs frontend)
- New pool that touches a different stakeholder (engineering vs sales vs design)
- "Actually let's think about X" where X is orthogonal
- "Let me also work on Y" where Y opens a new pool
- After 5+ turns on Pool 1, user introduces concept that doesn't appear anywhere in Pool 1

## When to NOT flag — clear no

- Continuing the leading thread (no new pool)
- Adding sub-thread to leading pool (same product, same surface)
- User explicitly says "switch to Pool 2" or "let's focus on X" — they've consented, no need to flag
- Asking a view query ("where am I") — not a direction, just a query
- Editing DIRECTIONS.md itself ("mark Pool 1 as done")
- User has already flagged 3+ drifts in the session and waved them all on — they're in multi-thread mode

## When it's genuinely ambiguous

If you can't tell:

1. Default to flagging IF the new theme has zero file/system/concept overlap with the leading pool.
2. Default to NOT flagging IF there's even one shared concept (same module, same external service, same workflow stage).

Erring toward over-flag is fine; the user will train you.

## Calibration over a session

Track a running sense of user response to your drift flags:

| User reaction | Calibration impact |
|-|-|
| "Yes pivot" | None — flag was correct, user wanted the prompt |
| "Park it, stay on Pool 1" | None — flag was correct, user wanted the option |
| "Just follow it, no need to flag" | Reduce sensitivity for the rest of session |
| Silence (ignored the note) | Mildly reduce sensitivity — they didn't engage with the flag |
| "Stop flagging" / "this is annoying" | Set sensitivity to TIGHT; only flag explicit "pivot" verbs |

Persist the calibration to DIRECTIONS.md's `## Drift sensitivity` section so it survives across sessions in this project.

## What NOT to do

- **Don't BLOCK the user.** The flag is a side note. Always answer the prompt regardless.
- **Don't flag the same drift twice in one session.** Once the pool exists, it's known.
- **Don't moralize.** "You should focus" / "this is a distraction" is patronizing. Just surface the choice neutrally.
- **Don't predict intent.** Let the user decide what's drift vs what's intentional. Your job is visibility, not judgment.

## Examples

### Good flag

> User has spent 20 turns on a CLI auth refactor. New message: "I want to also think about the pricing page copy."
>
> *Note: you're currently on Pool 1 (CLI auth refactor). This prompt is pulling toward a new Pool 4 (Pricing page copy). I'll add it as `SEED` — say 'pivot' to switch focus, or 'park it' to come back later.*
>
> [Then answer the pricing question normally.]

### Bad flag (over-eager)

> User has spent 20 turns on CLI auth. New message: "Should the JWT include the email claim?"
>
> ~~Note: drift toward JWT structure...~~
>
> **No flag — this is a sub-thread of the auth refactor.** Just answer.

### Bad flag (under-eager)

> User has spent 20 turns on CLI auth. New message: "Let me redesign the homepage hero."
>
> ~~Just answers the homepage question silently~~
>
> **Should have flagged** — homepage redesign has zero overlap with CLI auth. Even if the user explicitly meant to pivot, surfacing the choice is the right move.
