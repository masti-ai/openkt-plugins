/**
 * The openkt MCP server (prototype) — serves the Open Field app as an MCP App.
 *
 * Two-part registration tied together by a `ui://` URI:
 *   • tool  `show_report` — its `_meta.ui.resourceUri` points at the UI resource;
 *     it returns a *catalog-constrained Open Field spec* as structured content.
 *   • resource `ui://openfield/report.html` — the self-contained iframe bundle
 *     (json-render Renderer + Open Field registry + tokens), MIME
 *     `text/html;profile=mcp-app`.
 *
 * The host calls `show_report`, reads `_meta.ui.resourceUri`, fetches the HTML
 * resource, renders it in a sandboxed iframe, then pushes the tool result to
 * the iframe over the `ui/*` postMessage bridge. The iframe (src/mcp-app.tsx)
 * renders the spec.
 *
 * The returned spec is the agent-emitted demo spec shared with the standalone
 * Vite demo (DRY — one catalog, one sample). Catalog validation deliberately
 * runs *in the sandboxed iframe*, which is the correct trust boundary: a host
 * cannot trust the server, so the guardrail belongs on the rendering side.
 */
import fs from "node:fs/promises";
import path from "node:path";
import {
  registerAppResource,
  registerAppTool,
  RESOURCE_MIME_TYPE,
} from "@modelcontextprotocol/ext-apps/server";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type {
  CallToolResult,
  ReadResourceResult,
} from "@modelcontextprotocol/sdk/types.js";

// Shared rendering-layer sample data (type-only dep — bundles to plain JSON).
import { memoryDashboard } from "../json-render-openfield/src/specs/memory-dashboard";

/** Logical id linking the tool to its UI resource. */
const RESOURCE_URI = "ui://openfield/report.html";

/** On-disk name of the single-file iframe bundle (produced by `vite build`). */
const BUNDLE_FILE = "report.html";

// esbuild bundles this to `dist/main.js`, so `import.meta.dirname` is `dist/`,
// alongside the `report.html` the view build emits.
const BUNDLE_DIR = import.meta.dirname;

export function createServer(): McpServer {
  const server = new McpServer({
    name: "openkt-openfield",
    version: "0.1.0",
  });

  registerAppTool(
    server,
    "show_report",
    {
      title: "Show Open Field report",
      description:
        "Render an Open Field knowledge report (memory synthesis dashboard) as an interactive view.",
      inputSchema: {},
      _meta: { ui: { resourceUri: RESOURCE_URI } },
    },
    async (): Promise<CallToolResult> => {
      // The catalog-constrained spec the iframe renders. Exposed two ways:
      // structuredContent (preferred) + a JSON text block (fallback for hosts
      // that only surface text content to the UI).
      return {
        structuredContent: { spec: memoryDashboard },
        content: [
          { type: "text", text: JSON.stringify({ spec: memoryDashboard }) },
        ],
      };
    },
  );

  registerAppResource(
    server,
    "Open Field report view",
    RESOURCE_URI,
    { mimeType: RESOURCE_MIME_TYPE },
    async (): Promise<ReadResourceResult> => {
      const html = await fs.readFile(
        path.join(BUNDLE_DIR, BUNDLE_FILE),
        "utf-8",
      );
      // No `_meta.ui.csp` → host applies the strict default
      // (`default-src none; connect-src none`). Safe because the bundle is
      // fully self-contained (no runtime fetches).
      return {
        contents: [
          { uri: RESOURCE_URI, mimeType: RESOURCE_MIME_TYPE, text: html },
        ],
      };
    },
  );

  return server;
}
