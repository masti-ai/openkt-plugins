# OpenKT demo component catalog

Copy-paste snippets for every component. Two stylesheets, loaded in order:
`openkt-pages.css` (base + general) then `openkt-demo.css` (interactive). All
colors/fonts/spacing come from these — never inline your own palette.

## Table of contents
- [Page skeleton](#page-skeleton)
- [General components (openkt-pages.css)](#general-components)
- [Tabs](#tabs)
- [Knowledge graph + drill-down](#knowledge-graph--drill-down)
- [People / contributors](#people--contributors)
- [Knowledge-base, conflict, fork cards](#knowledge-base-conflict-fork-cards)
- [Tokens you can reference](#tokens)

---

## Page skeleton

```html
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>… — OpenKT</title>
  <link rel="stylesheet" href="openkt-pages.css">
  <link rel="stylesheet" href="openkt-demo.css">
  <script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
</head>
<body><main>
  <div class="eyebrow">SECTION LABEL</div>
  <h1>Title</h1>
  <p class="meta">one-line context · 2026-06-01</p>
  …
</main>
<script src="openkt-demo.js"></script></body>
```

## General components
(from `openkt-pages.css` — use for any non-graph content)

| Component | Class | Notes |
|---|---|---|
| Card | `.card`, `.card-soft` | bordered container; `.card-soft` is paper-1 |
| Panel | `.panel` > `.panel-head` + `.panel-body` | titled container |
| Callout | `.callout` + `-note`/`-success`/`-warn`/`-danger`/`-accent` | left-border note |
| Hint | `.hint` | dashed "do this" box |
| Memory-kind chip | `.kind` + `-context`/`-decision`/`-pattern`/`-anti-pattern`/`-question` | lowercase mono, product hues |
| Badge | `.badge` + `-ok`/`-warn`/`-danger`/`-info`/`-accent` | status pill |
| Tag / pill | `.tag`, `.pill` | |
| KPI tiles | `.stat-grid` > `.stat` > `.stat-value` + `.stat-label` | add `.stat-accent` for amber value |
| Layout | `.grid-2`, `.grid-3`, `.row`, `.stack` | responsive; collapse on mobile |

```html
<div class="stat-grid">
  <div class="stat stat-accent"><div class="stat-value">7</div><div class="stat-label">knowledge bases</div></div>
  <div class="stat"><div class="stat-value">183</div><div class="stat-label">memories</div></div>
</div>
<div class="callout callout-accent"><strong>Note:</strong> on-brand emphasis.</div>
```

## Tabs

Buttons carry `data-tab="<key>"`; panels carry `data-panel="<key>"`. Call
`OpenKTDemo.tabs()` once — it activates the first tab and wires clicks.

```html
<div class="tabs">
  <button class="tab" data-tab="sales">Sales</button>
  <button class="tab" data-tab="legal">Legal</button>
</div>
<section data-panel="sales"> … </section>
<section data-panel="legal"> … </section>
<script>OpenKTDemo.tabs();</script>
```

## Knowledge graph + drill-down

A two-column grid: graph canvas on the left, detail panel on the right. Click a
node → its text renders in the panel. Needs vis-network loaded.

```html
<div class="graphwrap">
  <div class="graph" id="graph0"></div>
  <div class="detail" id="detail0"><div class="dmuted">Click a node to inspect it.</div></div>
</div>
<script>
OpenKTDemo.graph('graph0', 'detail0', {
  nodes: [
    { id:'k1', type:'kb',     label:'Pricing Strategy', body:'Current-state summary…' },
    { id:'p1', type:'person', label:'Dana',             body:'8 memories' },
    { id:'m1', type:'memory', label:'Raw memory text…', body:'Full raw memory.', kb:'Pricing Strategy' }
  ],
  edges: [ { from:'m1', to:'k1' }, { from:'p1', to:'m1' }, { from:'k1', to:'k2', dashes:true } ]
});
</script>
```

Node `type` controls shape/color: `memory` = small dot, `kb` = amber square,
`person` = blue diamond. Optional per-node `color` overrides. Edge `dashes:true`
marks a KB-to-KB relation. Detail panel fields: `type`, `label` (title), `body`
(text), `kb` (optional footer link).

## Knowledge-base, conflict, fork cards

The signature OpenKT cards. A KB card has a colored `.dot`, a title, the
contributors (`.by`), the synthesized summary, then any conflicts/forks.

```html
<div class="kb">
  <h4><span class="dot" style="background:#c0612e"></span>Knowledge base title <span class="by">Alice, Bob</span></h4>
  <p>The synthesized current-state summary, conflicts resolved in prose.</p>

  <!-- CONFLICT = a later fact superseded an earlier one (resolved). Amber. -->
  <div class="conf">⟳ <b>What changed</b> → now <b>current</b> (was <b>old</b>)</div>

  <!-- FORK = an OPEN disagreement, no winner. Violet. Always attribute sides. -->
  <div class="fork">⑂ FORK — <b>the open question</b><br>
    <span class="side"><b>Alice:</b> position one</span><br>
    <span class="side"><b>Bob:</b> position two</span></div>
</div>
```

Keep conflict vs fork distinct: **conflict** is resolved history (amber);
**fork** is a live disagreement with named sides and no winner (violet).

## People / contributors

```html
<div class="people">
  <div class="person"><b>Dana (VP Sales)</b><span class="pm">8 memories</span>
    <div class="ptopics">
      <span class="chip" style="background:#c0612e">Pricing Strategy</span>
      <span class="chip" style="background:#2e6fc0">Forecast Accuracy</span>
    </div>
  </div>
</div>
```

Topic chips are colored per topic — reuse the same hex for a topic across the
graph dot, the KB dot, and the chip so a reader can track one topic by color.

## Tokens

Reference these vars instead of hardcoding (full list in `openkt-pages.css` /
`openkt-demo.css`): `--paper-0..3`, `--ink-0..4`, `--line`, `--amber`,
`--amber-strong`, `--amber-soft`, `--fork`, `--fork-soft`, `--success`,
`--warn`, `--danger`, `--info`, `--font-sans|mono|serif`, plus `--kind-*`.
