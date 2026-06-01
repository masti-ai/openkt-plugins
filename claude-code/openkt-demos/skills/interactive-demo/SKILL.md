---
name: interactive-demo
description: Build polished, interactive, publishable HTML demos in the OpenKT design language. Turn any spec, report, audit, research finding, architecture doc, or analysis into a single-page demo with tabbed sections, a clickable knowledge-graph visualization, drill-down detail panels, contributor views, and warm-paper editorial styling. Use this whenever the user wants to showcase work as a shareable demo, publish a spec or report to a website or blog, create a demo example, turn a markdown doc into something interactive, or says "make this into a demo / interactive page / something I can show people." Provides the canonical OpenKT design tokens + component kit, a scaffolder, a local comment-and-iterate loop, and a static export for public hosting.
---

# OpenKT interactive-demo

Build demos that look like they came from one product, not five different
sessions. Every page uses **one** design language — warm paper + ink, a single
terracotta-amber accent, Newsreader serif headings, Inter body, JetBrains Mono
code — plus a small interactive component kit (tabs, knowledge graph, drill-down,
knowledge-base / conflict / fork cards). The reference artifact is the OpenKT
knowledge-synthesis demo; this skill reproduces that look for anything.

## When to use

- The user wants to **showcase** work — "turn this into a demo," "something I can
  put on the site," "a blog example," "make it interactive."
- A spec / report / audit / analysis would land better as a page the reader can
  navigate (tabs, a graph, click-to-expand) than as scrolling markdown.
- Anything that should be **published** for others to see — the output needs to be
  a self-contained file you can drop on a website.

For a *quick* answer or a doc only the user will skim once, don't reach for this —
plain text or a simple page is fine.

## The design language is not optional

All visual styling comes from the two bundled stylesheets. **Do not invent your
own colors, fonts, or spacing** — that is the exact problem this skill exists to
stop. Load them in this order:

1. `assets/openkt-pages.css` — tokens + base elements + general components
   (`.card`, `.callout`, `.kind` chips, `.badge`, `.stat`/`.stat-grid`, tables).
2. `assets/openkt-demo.css` — the interactive layer (`.tabs`, `.graph`/`.detail`,
   `.people`/`.person`, `.kb`, `.conf`, `.fork`).

Interactive behavior comes from `assets/openkt-demo.js` (`OpenKTDemo.tabs()` and
`OpenKTDemo.graph()`) — see `references/components.md` for the full catalog with
copy-paste snippets. Read that file before authoring a demo with a graph.

## Workflow

**1. Scaffold.** Don't hand-assemble the boilerplate — run the scaffolder:

```
python3 scripts/new_demo.py /tmp/<topic>-demo --title "Human Title"
```

This creates the directory with the three asset files copied in and a ready
`index.html` from the template. (If you'd rather build by hand, copy
`assets/template.html` and the three asset files yourself.)

**2. Author the content.** Edit `index.html`. Replace the template's sample tabs,
graph data, people, and KB cards with the real material. Keep to the components in
`references/components.md`; reach for `openkt-pages.css` pieces (cards, callouts,
stat tiles, tables) for non-graph content. Use tabs when there are parallel views
(e.g. one per team / per environment / per phase); drop the tabs block for a
single-view demo.

**3. Preview + iterate (interactive mode).** Use the **make-pages-interactive**
skill on the demo directory: it serves the page locally and lets the user leave
inline comments that you answer by editing the HTML. This skill does NOT
re-implement a server — lean on that one. (The template already tolerates the
feedback tags it injects.)

**4. Publish (static mode).** When the demo is ready to share, produce one
self-contained file with no local-server dependency:

```
python3 scripts/publish.py /tmp/<topic>-demo/index.html -o <out>/demo.html
```

This inlines the CSS/JS and strips the comment-server tags, leaving remote CDN
scripts (vis-network) intact so the page loads from any host. Add `--vendor` to
inline the CDN too for a fully offline file. Drop the result into the website
(e.g. `openkt-landing`'s static/public assets) or attach it to a blog post.

## Output modes, explicitly

- **Interactive** = the demo dir served by make-pages-interactive. Commentable,
  for iterating with the user. Depends on the local server.
- **Static** = `publish.py` output. One portable `.html`, safe to host publicly.
  This is what goes on the website / blog.

Most demos want both: iterate interactive, ship static.

## Conventions that keep demos consistent

- One `<h1>`, then `<h3>` section headers (the report style). Lead with a
  `.eyebrow` label and a `.meta` one-liner.
- Amber is the only accent and is used sparingly. **Conflict** (a resolved
  supersede) is amber `.conf`; **fork** (an open disagreement, no winner) is
  violet `.fork`. Keep that distinction — it's load-bearing in OpenKT demos.
- Graph legend: `●` memory · `▦` knowledge base · `◆` person · amber line =
  relation. The `OpenKTDemo.graph()` helper already styles nodes this way.
- Keep it cheap: transform/opacity only, no heavy animation, mobile breakpoints
  are already in the CSS.

## Bundled files

```
interactive-demo/
├── SKILL.md
├── assets/
│   ├── openkt-pages.css     # canonical tokens + base + general components
│   ├── openkt-demo.css      # interactive layer (tabs, graph, cards)
│   ├── openkt-demo.js       # OpenKTDemo.tabs() + OpenKTDemo.graph()
│   └── template.html        # starter demo
├── scripts/
│   ├── new_demo.py          # scaffold a demo dir
│   └── publish.py           # static export → one self-contained .html
├── references/
│   └── components.md        # full component catalog + snippets
└── examples/
    └── kb-synthesis/        # flagship: OpenKT knowledge synthesis across teams
```

`examples/kb-synthesis/index.html` is the published flagship — the demo this
design language was distilled from. Open it to see every component in real use.
