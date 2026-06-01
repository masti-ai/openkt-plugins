# openkt-demos

A Claude Code plugin that gives agents **one** design language for the
interactive HTML they produce — so every demo, report, and spec page looks like
it came from the same product instead of five different sessions.

It ships a single skill, **`interactive-demo`**, which turns any spec, report,
audit, research finding, or analysis into a polished single-page demo:

- **One design system** — warm paper + ink, a single terracotta-amber accent,
  Newsreader serif headings, Inter body, JetBrains Mono code. Distilled from the
  OpenKT product dashboard.
- **An interactive component kit** — tabbed sections, a clickable knowledge-graph
  (vis-network), drill-down detail panels, and the signature
  knowledge-base / conflict / fork / people cards.
- **A scaffolder** (`new_demo.py`) and a **static export** (`publish.py`) that
  produces one self-contained `.html` you can drop on a website or blog.

## Install

Through the OpenKT marketplace:

```
/plugin marketplace add masti-ai/openkt-plugins
/plugin install openkt-demos@openkt
```

## Use

Just ask, in any project: *"turn this report into a demo,"* *"make this
interactive,"* *"something I can put on the site."* The skill triggers, scaffolds
a demo, and walks the build → preview → publish loop. The local preview/comment
loop reuses the `make-pages-interactive` skill; `publish.py` emits the public,
self-contained version.

## What's inside

```
skills/interactive-demo/
├── SKILL.md                 # workflow + conventions
├── assets/                  # openkt-pages.css · openkt-demo.css · openkt-demo.js · template.html
├── scripts/                 # new_demo.py (scaffold) · publish.py (static export)
├── references/components.md # full component catalog with snippets
└── examples/kb-synthesis/   # flagship demo this look was distilled from
```

The design tokens here mirror the product dashboard's
`src/app/globals.css`. If the product palette changes, update
`assets/openkt-pages.css` — it's the single source of truth for this plugin.
