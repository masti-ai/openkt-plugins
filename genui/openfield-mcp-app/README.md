# openfield-mcp-app

**MCP Apps prototype — the Open Field generative-UI app served by a minimal
openkt MCP server.**

This is the *delivery surface* half of the
[MCP Apps research](../../docs/research/mcp-apps-ext-apps.md) made concrete: it
wraps the [`json-render-openfield`](../json-render-openfield) rendering layer in
an [MCP Apps](https://github.com/modelcontextprotocol/ext-apps) (`ext-apps`)
server so the same Open Field UI renders **inside a host like Claude Desktop**,
not just in a standalone Vite page.

```
agent emits JSON spec ─► json-render + Open Field catalog ─► HTML
                                                              │
                                                              ▼
                                    MCP Apps  ui://  resource (this project)
                                    sandboxed iframe + ui/* postMessage bridge
                                                              │
                                                              ▼
                              Claude Desktop · MCPJam · MCP Inspector · …
```

## What it is

Two pieces tied together by one `ui://` URI:

| Piece | File | Role |
|-------|------|------|
| **MCP server** | [`server.ts`](server.ts) · [`main.ts`](main.ts) | Registers the `show_report` tool (returns a catalog-constrained Open Field spec as structured content) and the `ui://openfield/report.html` resource (the iframe bundle). Speaks **stdio** (Claude Desktop) and **Streamable HTTP** (inspectors). |
| **UI bundle** | [`report.html`](report.html) · [`src/mcp-app.tsx`](src/mcp-app.tsx) | The `ui://` resource: a single self-contained HTML file (json-render `Renderer` + the Open Field registry + tokens). Connects to the host over the `ui/*` bridge (`useApp`), receives the spec from the tool result, and renders it. |

**DRY — one catalog, two consumers.** The catalog, registry, `spec-utils`,
`openfield.css`, and the demo spec are imported *verbatim* from
`../json-render-openfield` (this repo is an npm workspace; see
[`genui/package.json`](../package.json)). The standalone Vite demo and this MCP
App render the **same** agent-emitted spec through the **same** Open Field
registry. The only thing this project adds is the MCP Apps glue.

**Trust boundary.** Catalog validation (`catalog.validate`) runs *inside the
sandboxed iframe*, not on the server — a host can't trust a server, so the "the
design language is not optional" guardrail belongs on the rendering side. The
server returns the spec; the sandbox validates and renders it.

**Self-contained by design.** When `_meta.ui.csp` is omitted the host applies
the strict default CSP (`default-src none; connect-src none`). The bundle makes
no runtime fetches, so it works under that default. (The one external reference
is the Google Fonts `@import` in `openfield.css`; under strict CSP it is blocked
and type falls back to system fonts — graceful degradation, no broken UI.)

## Pinned versions

`@modelcontextprotocol/ext-apps` is **pinned to `1.7.4`** (exact) — the spec and
SDK are fast-moving (see research memo §7), so the bridge is pinned and isolated
to this project. `@modelcontextprotocol/sdk` tracks `^1.29.0`.

## Build

```bash
# from the genui/ workspace root (installs all workspace deps once):
npm install

# from this directory:
npm run build        # build:view (vite single-file → dist/report.html) + build:server (esbuild → dist/main.js)
npm run typecheck    # tsc --noEmit
```

`dist/report.html` is one ~600 KB self-contained file (all JS + CSS inlined);
`dist/main.js` is the bundled server that reads it.

## Test (no Claude Desktop needed)

```bash
npm run build
npm run smoke        # drives dist/main.js over stdio as an MCP client and asserts the full wiring
```

The smoke test ([`scripts/smoke.mjs`](scripts/smoke.mjs)) asserts: `show_report`
is exposed with `_meta.ui.resourceUri`; the `ui://` resource is listed with MIME
`text/html;profile=mcp-app`; `resources/read` returns a self-contained HTML
document; and `show_report` returns a spec as `structuredContent`.

### With MCPJam / the MCP Inspector

```bash
npm run build
npm run serve        # Streamable HTTP on http://localhost:3001/mcp  (set PORT to override)
```

Point the inspector at `http://localhost:3001/mcp`, call `show_report`, and the
Open Field report renders in the inspector's MCP Apps view.

### Preview the UI bundle alone

```bash
npm run dev          # vite dev server; open /report.html
```

With no host attached the iframe falls back to the bundled demo spec
("preview mode" banner) so you can see exactly what a host would render — this is
the screenshot in [`docs/screenshot.png`](docs/screenshot.png).

## Use in Claude Desktop (stdio)

```json
{
  "mcpServers": {
    "openkt-openfield": {
      "command": "node",
      "args": ["/ABSOLUTE/PATH/TO/genui/openfield-mcp-app/dist/main.js", "--stdio"]
    }
  }
}
```

Run `npm run build` first, then ask Claude to "show the Open Field report".

## Layout

```
openfield-mcp-app/
├── report.html          # HTML shell → becomes the ui:// resource (vite-plugin-singlefile)
├── src/
│   ├── mcp-app.tsx       # iframe entry: useApp bridge + render shared registry
│   └── iframe.css        # iframe-only chrome (status banner); tokens come from openfield.css
├── server.ts             # createServer(): registerAppTool + registerAppResource
├── main.ts               # stdio + Streamable HTTP transports
├── scripts/smoke.mjs     # end-to-end stdio smoke test
├── vite.config.ts        # single-file view build
└── tsconfig.json
```
