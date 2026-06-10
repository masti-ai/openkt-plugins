# Recommendation: json-render as the foundation of the Deepwork generative UI library

**Bead:** op-7x9.10 · **Author:** polecat obsidian · **Date:** 2026-06-10
**Subject:** `vercel-labs/json-render` (json-render.dev, ~15K stars) evaluated as
the base layer for the Deepwork generative UI library for client agents, with a
working Open Field prototype.

---

## Verdict — ADOPT (with two managed caveats)

**Build the Deepwork generative UI library on json-render.** It is a near-exact
structural match for what we need: an agent emits JSON that is *constrained at
the data layer* to a developer-defined component catalog, and that JSON streams
into real UI. That constraint mechanism is precisely how we make "the Open Field
design language is not optional" enforceable instead of aspirational — the model
*cannot* emit an off-brand component or an invalid prop, because the catalog's
Zod schemas reject it.

The two caveats (both manageable, detailed below): (1) it is **young / pre-1.0**
(v0.19.0) and API churn is likely — we should pin and vendor-pressure-test; and
(2) a **schema quirk** in this version requires a one-line normalize step before
validation. Neither is a blocker.

The prototype in this directory **builds clean (`tsc --noEmit` + `vite build`),
renders the full Open Field design language, validates the agent-emitted spec
against the catalog (`spec valid`), and streams element-by-element with zero
console errors.**

---

## What json-render is

A "generative UI" framework. The developer defines a **catalog** (`defineCatalog`)
— component names, each with a Zod prop schema + description, plus named actions.
`catalog.prompt()` compiles that into the system prompt the model is given
(15.8 KB for our 18-component catalog). The model streams back **JSONL of
RFC-6902 JSON-Patch operations** that build a flat element tree
(`{root, elements: {id: {type, props, children, visible, on}}}`). A **registry**
(`defineRegistry`) maps each catalog component to a concrete implementation;
`<Renderer spec registry/>` renders it. `createSpecStreamCompiler` consumes the
patch stream so the UI fills in progressively.

```
catalog.ts ──prompt()──▶ system prompt ──▶ [agent] ──▶ JSONL patches
                                                            │
                                  catalog.validate() ◀──────┤ guardrail
                                                            ▼
                          <Renderer registry={Open Field}/> ─▶ branded UI
```

## Why it fits Deepwork (the case for adopt)

1. **Catalog guardrails == Open Field policy, enforced.** Our whole design-system
   thesis (`openfield`, the openkt-demos skill) is "don't let agents invent
   colors/components." json-render makes that a *type-checked contract*: emit only
   catalog components, props must pass Zod. This is the single biggest reason to
   adopt — it solves our stated problem mechanically.

2. **One catalog, many surfaces.** The same catalog + same agent output renders
   through swappable registries: React, **React Native**, Vue, Svelte, Solid,
   Next.js, **Ink (terminal TUI)**, React PDF, React Email, Satori (SVG/PNG),
   Remotion (video), React Three Fiber. Our agents span harnesses and surfaces
   (Claude Code, web chat, terminal, docs) — write the Open Field catalog once,
   bind it per surface. This directly de-risks op-7x9.11 (MCP Apps) and the
   multi-harness plugin vision.

3. **Streaming is native.** Agent output is a stream; json-render's patch protocol
   renders partials as they arrive. The UX we want (UI materializing as the agent
   "thinks") is the default path, not a bolt-on.

4. **Code export exists.** `@json-render/codegen` generates source from a tree —
   useful for op-7x9.12 (json-render demos → ops tooling) and for "eject to a
   static page" flows.

5. **Permissive license.** Apache-2.0 (see below) — we can vendor, fork, and ship
   commercially with no copyleft exposure.

## The prototype (what was built)

A real Vite + React 19 + TypeScript app under `genui/json-render-openfield/`:

- **`catalog.ts`** — an 18-component Open Field catalog: `Page`, `Section`,
  `Eyebrow`, `Heading`, `Text`, `Divider`, `Card`, `Callout`, `StatGrid`, `Stat`,
  `Table`, `KindChip` (the 5 OpenKT memory kinds), `Badge`, `Tag` (the 5 Deepwork
  earth categories), **`AsciiArt`** (the generative-ASCII slot, dark-panel +
  palette-tinted), `Button`, plus `export_report` / `refresh` / `open_memory`
  actions.
- **`registry.tsx`** — maps each to Open Field markup using **only** `openfield.css`
  classes (no inline palette), + action handlers.
- **`openfield.css`** — the Open Field tokens vendored from openkt-demos, *plus* a
  completed component layer (callout/badge/stat/table/layout) that was documented
  but missing from the source (bead op-xie).
- **`specs/memory-dashboard.ts`** — an agent-style spec: an OpenKT "Pricing
  knowledge base" synthesis page (ASCII header, KPI stats, kind chips, a resolved
  conflict callout, a contributor table, action buttons).
- **`App.tsx`** — renders it, validates against the catalog, and replays it as a
  stream.

Verified: `npm run build` passes; the page renders the full design language
(screenshot in `docs/`); `catalog.validate()` returns success; stream replay
produces no errors.

## License + constraints report

### License
**Apache-2.0** — permissive. Commercial use, modification, distribution, and
private use all granted; includes an explicit patent grant. Obligations are only
license/notice retention and stating changes. **No copyleft.** Safe to vendor
into `openkt-plugins` and to fork. (Confirm the NOTICE file is carried if we
redistribute source.)

### Constraints / things to know
1. **Pre-1.0 (v0.19.0).** Expect breaking changes. *Mitigation:* pin exact
   versions; vendor the `core` + `react` packages or wrap them behind our own thin
   `@deepwork/genui` facade so an upstream rename doesn't ripple through every
   consumer (DRY, per workspace rules).
2. **`visible` is required by `catalog.validate()` in this version.** The React
   schema marks each element's `visible` field non-optional, even though
   `<Renderer>` tolerates its absence. *Mitigation:* `spec-utils.withDefaults()`
   (a 12-line normalize) — the same repair pass a real client runs on streamed
   model output anyway. Re-check whether this is fixed in later releases.
3. **Actions wiring has two shapes.** `defineRegistry().handlers` is a
   getter-function form; `JSONUIProvider.handlers` wants a flat map. We bridged
   with `handlers(() => undefined, () => ({}))` since our handlers don't read
   json-render state. Document this in the facade so consumers don't re-discover
   it.
4. **Bundle size.** ~333 KB JS (101 KB gzip) for core+react+React. Fine for an
   app/MCP App; for a tiny inline widget, lean on tree-shaking and per-surface
   builds.
5. **Streaming wire format is opinionated** (JSONL RFC-6902 patches). The server
   must emit exactly that; `createJsonRenderTransform` / `pipeJsonRender` are
   provided for it. Couples our agent output format to json-render's protocol —
   acceptable, but a reason to keep the facade.
6. **Prompt weight.** `catalog.prompt()` is ~15.8 KB for 18 components — it grows
   with the catalog. Budget tokens; consider per-task catalog subsets.

## Risks & open questions

- **Maturity vs. our timeline.** 15K stars but young. The facade + pinning makes
  this tolerable; revisit at their 1.0.
- **MCP Apps fit (op-7x9.11).** Does `<Renderer>` run cleanly inside an MCP App
  sandbox / claude.ai web? Needs the quartz prototype to confirm — but the
  multi-target story (incl. plain React + Satori) is encouraging.
- **openfield as source of truth (op-7x9.5).** This prototype vendored a *copy* of
  the tokens. The completed component layer here should be upstreamed into
  `masti-ai/openfield` and re-vendored, not maintained in two places.

## Recommended next steps

1. **Upstream the completed Open Field component layer** (`openfield.css` here →
   `masti-ai/openfield`), fixing bead **op-xie**, then have this prototype and
   openkt-demos both vendor it (op-7x9.5).
2. **Stand up a thin `@deepwork/genui` facade** wrapping `@json-render/core` +
   `@json-render/react`, exporting the Open Field catalog + registry, so every
   consumer (living-pages op-7x9.6, ops tooling op-7x9.12, MCP Apps op-7x9.11)
   reads one source.
3. **Wire a live agent** (MiniMax M2.5 via DI, or Claude) to `catalog.prompt()`
   and stream real output through `createSpecStreamCompiler` — replace the
   hand-authored spec with a generated one.
4. **Test the React renderer inside an MCP App** (hand to op-7x9.11 / quartz) to
   confirm the claude.ai-web delivery path.
