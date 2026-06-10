# Research Memo: MCP Apps (ext-apps) as a UI Delivery Surface

**Date:** 2026-06-10
**Companion track:** internal tracker (json-render evaluation) — per owner directive, MCP Apps +
json-render + generative UI are **one track**; this memo is the joint synthesis.
**Status:** Research complete. Recommendation: **ADOPT** MCP Apps as the delivery surface,
with json-render + an Open Field catalog as the rendering layer.

---

## TL;DR

**MCP Apps (SEP-1865, extension id `io.modelcontextprotocol/ui`) is the official,
cross-vendor, write-once UI delivery surface for AI agents — and it is already live in
claude.ai web + desktop.** It is not an Anthropic- or OpenAI-proprietary effort: it was
co-authored by MCP Core Maintainers at **OpenAI and Anthropic together with the MCP-UI
community creators** (Ido Salomon, Liad Yosef) and Olivier Chafik, and it explicitly
**unifies MCP-UI and OpenAI's Apps SDK into one open standard**. Servers predeclare UI as
`ui://` resources (HTML), bind them to tools via `_meta.ui.resourceUri`, and hosts render
them in **sandboxed iframes** that talk back over **JSON-RPC 2.0 on `postMessage`**.

For the OpenKT/Deepwork generative-UI library this gives us a clean two-layer split:

| Layer | Technology | Role |
|-------|-----------|------|
| **Delivery surface** | **MCP Apps** (`ui://` + sandboxed iframe + `ui/*` bridge) | Cross-host transport, sandbox, tool binding. Write once → runs in Claude, ChatGPT, VS Code, Goose. |
| **Rendering layer** | **json-render** (Apache-2.0) + **Open Field catalog** | Agent emits JSON constrained to a Zod-schema'd component catalog → renders as HTML *inside* the MCP Apps iframe. |

Both standards are **open / Apache-2.0**, so there are **no license or governance
blockers**. **Recommendation: adopt MCP Apps as the delivery surface and build the Open
Field catalog on json-render as the renderer, bundled into the `ui://` HTML.** See caveats
(§7) — the spec is fast-moving and host conformance lags it.

---

## 1. What MCP Apps actually is

- **Formal status:** SEP-1865, **Extensions Track**, extension identifier
  `io.modelcontextprotocol/ui`. Extends MCP per SEP-1724. Proposed **2025-11-21**, stable
  spec dated **2026-01-26**, **merged into the main `modelcontextprotocol` spec repo on
  2026-01-28** (PR #1865, state MERGED), status **"Final."** Billed by the MCP blog as
  *"the first official MCP extension."* `[1][2][3][4][5][6]`
- **Authorship (cross-vendor, not proprietary):** MCP Core Maintainers at **OpenAI and
  Anthropic**, plus **MCP-UI creators Ido Salomon (@idosal) & Liad Yosef (@liadyosef)** and
  **Olivier Chafik (@olivierchafik)**. The official blog: *"We were excited to partner with
  both OpenAI and MCP-UI to create a shared open standard."* It **unifies the approaches
  pioneered by MCP-UI and the Apps SDK into a single, open standard.** `[1][3]`
- **Governance oddity (track for stability):** the SEP page shows **Status: Final** but
  **Sponsor: None ("seeking sponsor")**, and the canonical spec file still lives under
  `/specification/draft/`. "Final" + unsponsored + still-in-`/draft/` is an unusual
  governance state — normative field names and the `ui/*` method set may still shift. `[5]`

### How it works (technical)

1. **Predeclared `ui://` resources.** A server declares UI as a **resource** under the
   `ui://` URI scheme, MIME type **`text/html;profile=mcp-app`** (HTML-only in the initial
   spec). Resources are **predeclared, not embedded in tool results**, so hosts can
   **prefetch templates** before tool execution. `[2]`
2. **Tool→UI binding.** A tool references its UI resource via **`_meta.ui.resourceUri`**
   metadata (older flat `_meta['ui/resourceUri']` is deprecated). This **separates
   presentation templates from data**. `[2]`
3. **Host fetch + render.** The host fetches via standard **`resources/read`** and renders
   the HTML in a **sandboxed iframe**. `[2]`
4. **Bidirectional bridge.** The iframe **acts as an MCP client**, connecting to the host
   over a **`postMessage` transport** using **standard MCP JSON-RPC 2.0** (the **`ui/*`
   namespace** — *not* custom message types), with a **`ui/initialize` →
   `ui/notifications/initialized`** handshake (replacing MCP-UI's ad-hoc iframe-ready
   pattern). The host pushes tool data to the UI via notifications; the UI can **call tools
   back on the originating MCP server, proxied through the host** (`callServerTool`). SDK
   (v1.1.2): `PostMessageTransport` + an `App` class with `ontoolinput`/`ontoolresult`
   handlers. `[1][2][7]`
5. **Deferred to future iterations:** external URLs, remote DOM, native widgets. Today it is
   **HTML-in-sandboxed-iframe only.** `[3]`

### Security / sandboxing model

The model rests on five mechanisms `[2][5]`:

1. **Mandatory sandboxed iframes** (`allow-scripts`, `allow-same-origin`).
2. **Host-enforced CSP from server-declared domains:** `connectDomains→connect-src`,
   `resourceDomains→img/script/style/font/media-src`, `frameDomains→frame-src`,
   `baseUriDomains→base-uri`. **If `ui.csp` is omitted, the host MUST default to
   `default-src none; connect-src none`** (no external connections). **Host and Sandbox MUST
   have different origins** (separate-origin proxy iframe mediates isolation).
3. **Predeclared, host-reviewable HTML templates** (host can inspect before rendering).
4. **Auditable UI→host messaging** — all of it is loggable JSON-RPC.
5. **Optional user consent** for UI-initiated tool calls (**MAY**, i.e. not mandatory).

> ⚠️ Third-party security analysis (Backslash, *"New MCP Spec Opens New Attack Surfaces"*)
> questions the **sufficiency** of these mitigations (not their composition). And host
> conformance lags: **claude.ai reportedly ignores `frameDomains`** (claude-ai-mcp issue
> #40) and has injected a **non-JSON-RPC auth message** (issue #47). Plan defensively:
> assume the strict CSP default and don't rely on optional consent gating.

---

## 2. Host support today

**Genuinely cross-host, supported now** `[1][2][8]`:

| Host | Status / constraints |
|------|----------------------|
| **Claude (web + desktop)** | **Available today**, web *and* desktop. Requires **domain signing**; reportedly **ignores `frameDomains`** (issue #40). Our primary target. |
| **ChatGPT** | Implements the **same iframe-and-bridge** model. Requires **beta Developer Mode + paid plan**; **lacks** Tool-Calling-from-UI, `useFiles`, `useCheckout`. Exposes **proprietary `window.openai` extensions that are NOT portable**. |
| **VS Code** (Insiders / GitHub Copilot) | Shipped; **lacks fullscreen / PiP**. |
| **Goose**, **Postman**, **MCPJam**, **Archestra.AI** | Listed as supporting hosts. |

OpenAI's docs state verbatim: *"ChatGPT implements this same iframe-and-bridge model, so
you can build your UI once and run it in ChatGPT and other MCP Apps-compatible hosts."* `[7]`

> **"Write once" holds for the standard subset, not for vendor extensions.** Build to the
> standard `ui/*` bridge; treat `window.openai.*` as ChatGPT-only sugar. Capabilities vary
> per host — the catalog must **degrade gracefully**.

---

## 3. How json-render combines with MCP Apps (the two-layer thesis)

**json-render** (vercel-labs, **Apache-2.0**, launched Jan 2026, ~13k stars, active as of
Mar 2026) is a **"Generative UI framework"**: an AI generates a **JSON specification
constrained to a developer-defined component catalog** whose allowed props are **defined by
Zod schemas** — *"AI can only use components in your catalog,"* *"JSON output matches your
schema every time."* The LLM *"acts as a composer filling out a strict, pre-approved
form."* `[9]`

These are **complementary layers of one track, not competitors**:

```
  Agent emits JSON spec  ──►  json-render + Open Field catalog  ──►  HTML
  (constrained to catalog)    (Zod-validated, safe rendering)        │
                                                                     ▼
                                              MCP Apps  ui://  resource
                                              (sandboxed iframe + ui/* bridge)
                                                                     │
                                                                     ▼
                                        Claude web · ChatGPT · VS Code · Goose
```

- **MCP Apps = the delivery surface:** cross-host transport, sandbox, tool binding,
  host↔UI bridge. Answers *"how does interactive UI get into claude.ai and stay safe?"*
- **json-render + Open Field = the rendering layer:** answers *"what does the agent emit,
  and how do we keep it on-brand and safe?"* The catalog guardrails (Zod-schema'd props,
  "design language not optional") match Open Field's principles from the internal tracker eval.

This split is the **inferred architectural recommendation** of this research — no source
documents json-render-inside-an-MCP-Apps-iframe as a *shipped* pattern (see §7), but both
being open/Apache-2.0 and the iframe accepting arbitrary bundled HTML makes it a clean fit.

---

## 4. License & governance

- **MCP Apps:** open standard under the MCP project (donated to the **Agentic AI
  Foundation** per Anthropic's announcement). `[5][17]`
- **json-render:** **Apache-2.0** (permissive — commercial use OK, vendoring OK). `[9]`
- **MCP-UI** (provenance ancestor): permissive license. `[16]`

**No license or governance blockers** to adopting either as the foundation of the Deepwork
generative-UI library. The only governance caution is the **"Final but unsponsored,
still-in-`/draft/`"** state of SEP-1865 (§1, §7).

---

## 5. Recommendation for OpenKT / Deepwork generative-UI library

**ADOPT MCP Apps as the UI delivery surface for client-agent generative UI, with json-render
+ an Open Field component catalog as the rendering layer bundled into the `ui://` HTML.**

Concrete plan:

1. **Target the standard `ui/*` bridge, claude.ai-web first.** Build to the spec, not to
   `window.openai.*`. Validate against claude.ai web + desktop (our primary host) and keep a
   ChatGPT path as a portability check.
2. **Bundle the renderer into the iframe HTML.** Given claude.ai's domain-signing and the
   strict default CSP (`default-src none; connect-src none` when `ui.csp` is omitted), the
   safest first cut is to **bundle json-render + the Open Field catalog directly into the
   `ui://` HTML resource** rather than fetching the catalog at runtime. Runtime fetch would
   require `connectDomains`/`resourceDomains` the host may not honor (see open Qs §6).
3. **Reuse the Open Field catalog from internal tracker.** The catalog prototyped there
   (Card/Table/KindChip/Stat/Callout/Badge/AsciiArt/Eyebrow over vendored openfield tokens)
   becomes the json-render registry that renders inside the iframe. **One catalog, two
   consumers** (DRY): the standalone Vite demo *and* the MCP Apps resource.
4. **Design for graceful degradation.** Host capabilities differ (fullscreen/PiP, consent
   gating, `frameDomains`, Tool-Calling-from-UI). The catalog and bridge usage must detect
   and degrade per host.
5. **Pin to a spec snapshot; budget for churn.** Because the spec is fast-moving and still
   under `/draft/`, **pin to a specific commit/version** of the ext-apps spec + SDK and
   isolate the bridge behind a thin adapter so field-name changes (`_meta.ui.resourceUri`
   etc.) are a one-file fix.
6. **Don't rely on optional security.** User-consent gating is **MAY**; assume it's off.
   Keep UI-initiated tool calls minimal and auditable.

**Why now:** MCP Apps is the *only* official, cross-vendor, already-shipping path to
interactive UI inside claude.ai. Building the Deepwork genui library on it (delivery) +
json-render/Open Field (rendering) means **write-once UI across every major MCP host**, with
**zero license risk** and full alignment with the internal tracker json-render direction.

---

## 6. Open questions (carry into design / internal tracker–.6)

1. Does claude.ai web's **domain-signing / CSP enforcement** (and its `frameDomains` gap)
   force the renderer to be **fully bundled** into the `ui://` HTML, or can it fetch the
   catalog from an external origin?
2. **Concrete integration shape:** is json-render's JSON-spec output rendered by a renderer
   **bundled in the iframe HTML**, or fetched at runtime (which `connectDomains` must then
   allow)? (Recommendation §5.2 assumes bundled — validate.)
3. Given **Final-but-unsponsored, spec-in-`/draft/`**, how stable are the normative field
   names and the `ui/*` method set for a platform committing now?
4. **Which capabilities does claude.ai actually honor** today vs. ignore (`frameDomains`,
   user-consent gating, `ui/request-display-mode`), and how should the catalog degrade?

---

## 7. Caveats (research integrity)

- All six findings draw on **primary sources** (ext-apps spec repo, official MCP blog,
  SEP-1865 page, PR #1865, OpenAI Apps SDK docs, json-render repo) and carry **unanimous
  3-0 adversarial-verification votes**, except the multi-host-support finding (**2-1** — the
  dissent concerns over-optimism of "without client-specific code" and ChatGPT being
  "starting this week" vs. strictly live; the core multi-host fact is sound).
- **Time-sensitivity:** spec lives at `/specification/draft/` and is fast-moving (proposed
  Nov 2025 → stable 2026-01-26 → merged 2026-01-28). Field names and host capabilities are
  still evolving.
- **Host conformance lags the spec:** claude.ai ignores `frameDomains` (#40), injected a
  non-JSON-RPC auth message (#47); ChatGPT needs beta Developer Mode + paid plan and exposes
  non-portable `window.openai` extensions.
- The **json-render + Open Field inside an MCP Apps iframe** integration is an **inferred
  architectural recommendation**, not a source-documented shipped pattern. The json-render
  eval rests on a single primary source (its repo) + secondary coverage.

---

## Sources

| # | URL | Quality |
|---|-----|---------|
| 1 | https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/draft/apps.mdx | primary (spec) |
| 2 | https://github.com/modelcontextprotocol/ext-apps/ | primary (repo/README) |
| 3 | https://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/ | primary (blog) |
| 4 | https://blog.modelcontextprotocol.io/posts/2025-11-21-mcp-apps/ | primary (blog) |
| 5 | https://modelcontextprotocol.io/community/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp | primary (SEP) |
| 6 | https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1865 | primary (PR) |
| 7 | https://developers.openai.com/apps-sdk/mcp-apps-in-chatgpt | primary (OpenAI docs) |
| 8 | https://github.com/modelcontextprotocol/ext-apps/ (Client support table) | primary |
| 9 | https://github.com/vercel-labs/json-render | primary (repo) |
| 16 | https://github.com/idosal/mcp-ui/blob/main/LICENSE | primary (license) |
| 17 | https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation | primary |
| — | https://inkeep.com/blog/anthropic-openai-mcp-apps-extension | secondary |
| — | https://alpic.ai/blog/mcp-apps-how-it-works-and-how-it-compares-to-chatgpt-apps | blog |
| — | https://www.infoq.com/news/2026/03/vercel-json-render/ | secondary |
| — | https://blog.logrocket.com/vercel-json-render-dynamic-ui/ | secondary |
| — | https://mcp.directory/blog/mcp-apps-standard-vs-openai-apps-sdk-2026 | blog |
| — | https://community.openai.com/t/mcp-apps-in-chatgpt-are-fundamentally-broken-2-critical-bugs/1377697 | forum (host-bug evidence) |

*Research method: 5-angle web-search fan-out → 20 sources fetched → 88 claims extracted →
25 verified via 3-vote adversarial verification (25 confirmed, 0 killed) → 6 synthesized
findings. 102 agent calls.*
