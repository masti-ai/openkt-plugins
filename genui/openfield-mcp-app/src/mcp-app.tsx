/**
 * The Open Field MCP App — the `ui://` HTML resource, as seen from inside the
 * host's sandboxed iframe.
 *
 * This is the delivery surface from the research memo (docs/research/mcp-apps-ext-apps.md):
 *
 *   agent emits JSON spec ─► json-render + Open Field catalog ─► HTML
 *                                                                 │
 *                                                                 ▼
 *                                       MCP Apps  ui://  resource (this file)
 *                                       sandboxed iframe + ui/* postMessage bridge
 *
 * The *rendering layer* (catalog, registry, openfield.css, the demo spec) is
 * imported verbatim from the sibling `json-render-openfield` project — one
 * catalog, two consumers (the standalone Vite demo and this MCP App). The only
 * thing this file adds is the MCP Apps glue: connect to the host over the
 * `ui/*` bridge, receive the agent-emitted spec as the tool result, and render
 * it through the same registry.
 */
import { StrictMode, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { JSONUIProvider, Renderer } from "@json-render/react";
import type { Spec } from "@json-render/core";
import type { App } from "@modelcontextprotocol/ext-apps";
import { useApp, useHostStyleVariables } from "@modelcontextprotocol/ext-apps/react";

// ── Rendering layer, shared with the standalone demo (DRY) ──────────────────
import { catalog } from "../../json-render-openfield/src/catalog";
import { registry, handlers } from "../../json-render-openfield/src/registry";
import { withDefaults } from "../../json-render-openfield/src/spec-utils";
import { memoryDashboard } from "../../json-render-openfield/src/specs/memory-dashboard";
import "../../json-render-openfield/src/openfield.css";
import "./iframe.css";

/** The tool the host calls (and that the UI can call back) to fetch a report spec. */
const SHOW_REPORT_TOOL = "show_report";

/** Flatten the shared registry's action handlers (no-op getters — see registry.tsx). */
const actionHandlers = handlers(
  () => undefined,
  () => ({}),
);

/**
 * Pull an Open Field spec out of a tool result. The server sends it as
 * `structuredContent.spec` (preferred) and, as a fallback for hosts that only
 * surface text content, as a JSON string in a text block.
 */
function extractSpec(result: unknown): Spec | null {
  const r = result as {
    structuredContent?: { spec?: Spec };
    content?: Array<{ type: string; text?: string }>;
  } | null;
  if (!r) return null;
  if (r.structuredContent?.spec) return r.structuredContent.spec;
  const text = r.content?.find((c) => c.type === "text")?.text;
  if (text) {
    try {
      const parsed = JSON.parse(text);
      return (parsed?.spec ?? parsed) as Spec;
    } catch {
      /* not JSON — ignore */
    }
  }
  return null;
}

type Source = "host" | "fallback" | null;

function OpenFieldReport() {
  // The agent-emitted spec, once we have it (from the host tool result, a
  // proactive tool call, or — outside any host — the bundled demo fallback).
  const [spec, setSpec] = useState<Spec | null>(null);
  const [source, setSource] = useState<Source>(null);
  const gotSpec = useRef(false);

  const setFromResult = (result: unknown, src: Source) => {
    const next = extractSpec(result);
    if (next) {
      gotSpec.current = true;
      setSpec(next);
      setSource(src);
    }
  };

  // `useApp` creates the App, runs `onAppCreated` to register handlers, then
  // connects over the PostMessageTransport to window.parent (the host).
  const { app, isConnected, error } = useApp({
    appInfo: { name: "Open Field Report", version: "0.1.0" },
    capabilities: {},
    autoResize: true,
    onAppCreated: (app: App) => {
      // The host pushes the tool's output here after `ui/initialize`.
      app.ontoolresult = (result) => setFromResult(result, "host");
      app.onerror = (e) => console.error("[openfield-mcp-app]", e);
    },
  });

  // Apply the host's theme / style variables (light-dark, fonts, safe-area).
  useHostStyleVariables(app);

  // Robustness: some hosts don't auto-push the tool result to a freshly
  // connected iframe. Once connected, if nothing has arrived shortly, fetch it
  // ourselves — the UI acting as an MCP client and calling the server tool back
  // through the host (`callServerTool`), exactly the bidirectional bridge the
  // spec describes.
  useEffect(() => {
    if (!app || !isConnected) return;
    let cancelled = false;
    const t = setTimeout(async () => {
      if (cancelled || gotSpec.current) return;
      try {
        const result = await app.callServerTool({
          name: SHOW_REPORT_TOOL,
          arguments: {},
        });
        if (!cancelled) setFromResult(result, "host");
      } catch (e) {
        console.error("[openfield-mcp-app] callServerTool failed", e);
      }
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [app, isConnected]);

  // Standalone / preview fallback: when there is no host (opened directly, or
  // the bridge errored) render the bundled demo spec so the page is still a
  // faithful preview of what the host would show.
  useEffect(() => {
    if (gotSpec.current) return;
    const standalone = error || (typeof window !== "undefined" && window.parent === window);
    if (standalone) {
      setSpec(memoryDashboard);
      setSource("fallback");
    }
  }, [error]);

  // Normalize (fill structural defaults) and validate against the catalog —
  // the same guardrail the standalone demo applies to streamed model output.
  const normalized = useMemo(() => (spec ? withDefaults(spec) : null), [spec]);
  const validation = useMemo(
    () => (normalized ? catalog.validate(normalized) : null),
    [normalized],
  );

  if (!normalized) {
    return (
      <div className="of-status">
        {error ? `bridge error: ${error.message}` : "Connecting to host…"}
      </div>
    );
  }

  return (
    <>
      {source === "fallback" && (
        <div className="of-status of-status--note">
          preview mode — bundled demo spec (no MCP host attached)
        </div>
      )}
      {validation && !validation.success && (
        <div className="of-status of-status--error">
          spec failed catalog validation — rendering anyway
        </div>
      )}
      <JSONUIProvider registry={registry} handlers={actionHandlers}>
        <Renderer spec={normalized} registry={registry} />
      </JSONUIProvider>
    </>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <OpenFieldReport />
  </StrictMode>,
);
