# Open Field

The Deepwork Labs design module — a monochrome-warm, ASCII-forward editorial
design system. One source of truth for every surface in the Deepwork × OpenKT
family: plugins, dashboards, agent-emitted UI, and the website.

Warm cream paper, an ink ramp, one terracotta-amber accent per screen.
Newsreader serif for titles, Inter for body, JetBrains Mono for code, labels,
and all ASCII art.

## Layout

```
openfield/
├── tokens/mix.css       design tokens + base components (source of truth)
├── art/_art.js          generative ASCII art library (13 named patterns)
├── loading/loading.js   spinners, bars, streaming typer, agent faces
├── app/pg-app.css       application shell layer — sidebar, cards, tables, drawer
├── app/pg-shell.js      shell injector + Cmd-K palette
├── SKILL.md             rules for agents building in this system
└── llms.txt             machine-readable index
```

## Load order

```html
<link rel="stylesheet" href="tokens/mix.css" />
<!-- … page … -->
<script src="art/_art.js"></script>
<script src="loading/loading.js"></script>
```

App surfaces additionally load `app/pg-app.css` then `app/pg-shell.js`.

## Consumers

Never copy these files by hand. Vendor them with a pinned ref so updates flow
from one place:

- `openkt-plugins` — per-harness plugin packaging (living-pages, openkt-demos)
- OpenKT dashboard
- deepwork.art
- agent-emitted UI (generative UI library, in progress)

## Rules

Read `SKILL.md` before building anything. The short version:

- One amber moment per screen. Never more.
- Hairline borders, 4–8px radii, shadows almost never.
- Loading is always monospace characters — no SVG spinners, no emoji.
- Cards shift left, links underline amber, buttons fill. Nothing else moves.
- Editorial voice: sentence case, no exclamation marks, symbols (→ ↳ · — ✓ ×)
  used like punctuation.
