# Open Field — skill manifest

A monochrome-warm, ASCII-forward editorial design system. Use it whenever you
build a page, app surface, or artifact for the Open Field / Deepwork × OpenKT
family.

## Load

```html
<link rel="stylesheet" href="mix.css" />
<!-- … page … -->
<script src="_art.js"></script>
<script src="loading.js"></script>
```

## Always

- Page bg `var(--paper-0)`, text `var(--ink-0)`, ONE `var(--amber)` accent per screen.
- Titles in `var(--font-display)` (Newsreader serif). Body/UI in Inter. Code, slugs, labels, eyebrows, and ALL ASCII in `var(--font-mono)` (JetBrains Mono).
- Hairline 1px borders; radii 4–8px; shadows almost never.
- Category = one of five earths (`clay` research · `ochre` demos · `sand` video · `moss` product · `slate` essays). One per item.
- Classified memory = a `.kind` chip (`context` · `decision` · `anti-pattern` · `pattern` · `question`).

## Art

`<pre class="art" data-art="NAME" data-color="#HEX"></pre>` inside any sized box.
Names: breath, tunnel, flow, rain, spiral, wave, orbits, typeswarm, typespiral,
typefield, glyphrain, tree, phyllo. Opacity ≤ 0.5 unless it's a card thumbnail.

## Loading

- Spinner: `<span data-spin="braille"></span>`
- Timer: `<span data-timer></span>`
- Bar: `<div data-bar="block" data-width="30"><span class="bar-fill"></span><span class="bar-pct"></span></div>`
- Stream: `<span data-type="…" data-type-speed="34"></span>`
- Agent: `.agent-face` with `.eye` / `.mouth` spans + `data-mouth`.

## Voice (from OpenKT)

Editorial, second person, calm. Name a page by what it lets you understand
("What you know", "What's happening"). Sentence case headings, lowercase mono
for slugs/scopes, CAPS only for tiny eyebrow labels. No emoji. Text symbols
(→ ↳ · — ✓ ×) used like punctuation. No exclamation marks.

## Never

- Invent colors, fonts, or radii outside the tokens in `mix.css`.
- Use more than one amber moment per screen.
- Add a second micro-interaction. Cards shift left; links underline amber; buttons fill. Nothing else moves.
- Use emoji or SVG spinners — loading is always monospace characters.
