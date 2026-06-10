/**
 * Demo harness for the Open Field × json-render prototype.
 *
 * Two modes, both driving the *same* agent-emitted spec through the *same*
 * Open Field registry:
 *   • Rendered     — the final spec, rendered in one pass (<Renderer/>).
 *   • Replay stream — the spec revealed element-by-element to mimic how a model
 *     streams a generative UI: partials render as they "arrive" via the real
 *     <Renderer loading/>. In production the wire format is consumed by
 *     `createSpecStreamCompiler` (see streaming-note below); the UX is identical.
 */
import { useEffect, useMemo, useState } from "react";
import { JSONUIProvider, Renderer } from "@json-render/react";
import type { Spec } from "@json-render/core";
import { registry, handlers } from "./registry";
import { catalog } from "./catalog";
import { memoryDashboard as rawSpec } from "./specs/memory-dashboard";
import { withDefaults } from "./spec-utils";

// Normalize the agent-emitted spec (fill structural defaults), exactly as a
// client would before validating streamed model output.
const memoryDashboard = withDefaults(rawSpec);

// Flatten the registry's action handlers for the provider. Our handlers don't
// read json-render state, so the getters are no-ops; this keeps the registry's
// `actions` block the single source of truth for what each action does.
const actionHandlers = handlers(
  () => undefined,
  () => ({}),
);

// Guardrail proof: the agent-emitted spec is validated against the catalog's
// Zod schemas at load. A real client runs this on the streamed model output and
// rejects / repairs anything that doesn't conform — the same check that makes
// "the design language is not optional" enforceable rather than aspirational.
const validation = catalog.validate(memoryDashboard);

/** Build a partial spec containing only the first `n` top-level children. */
function partialSpec(full: Spec, n: number): Spec {
  const rootEl = full.elements[full.root];
  const keep = (rootEl.children ?? []).slice(0, n);
  const reachable = new Set<string>([full.root]);
  const walk = (id: string) => {
    reachable.add(id);
    for (const c of full.elements[id]?.children ?? []) walk(c);
  };
  keep.forEach(walk);
  const elements: Spec["elements"] = {};
  for (const id of reachable) {
    elements[id] =
      id === full.root ? { ...rootEl, children: keep } : full.elements[id];
  }
  return { root: full.root, elements };
}

export default function App() {
  const [mode, setMode] = useState<"final" | "stream">("final");
  const [tick, setTick] = useState(0);
  const totalTop = (
    memoryDashboard.elements[memoryDashboard.root].children ?? []
  ).length;

  // Replay: reveal one more top-level child every 280ms until complete.
  useEffect(() => {
    if (mode !== "stream") return;
    setTick(0);
    const iv = setInterval(() => {
      setTick((t) => {
        if (t >= totalTop) {
          clearInterval(iv);
          return t;
        }
        return t + 1;
      });
    }, 280);
    return () => clearInterval(iv);
  }, [mode, totalTop]);

  const streaming = mode === "stream" && tick < totalTop;
  const spec = useMemo<Spec>(
    () => (mode === "final" ? memoryDashboard : partialSpec(memoryDashboard, tick)),
    [mode, tick],
  );

  // The system prompt the agent is constrained by (first lines shown).
  const prompt = useMemo(() => catalog.prompt(), []);

  return (
    <>
      <div className="of-toolbar">
        <span className="eyebrow">
          <span className="dot">●</span> JSON-RENDER × OPEN FIELD
          <span className={`badge ${validation.success ? "badge-ok" : "badge-danger"}`}>
            {validation.success ? "spec valid" : "spec invalid"}
          </span>
        </span>
        <div className="row" style={{ gap: "var(--sp-2)" }}>
          <button
            className={`btn btn-mono ${mode === "final" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setMode("final")}
          >
            Rendered
          </button>
          <button
            className={`btn btn-mono ${mode === "stream" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setMode("stream")}
          >
            ⟳ Replay stream
          </button>
          <a
            className="btn btn-mono btn-ghost"
            href="https://json-render.dev"
            target="_blank"
            rel="noreferrer"
          >
            docs ↗
          </a>
        </div>
      </div>

      <JSONUIProvider registry={registry} handlers={actionHandlers}>
        <Renderer spec={spec} registry={registry} loading={streaming} />
      </JSONUIProvider>

      <details className="of-prompt">
        <summary className="mono">
          system prompt the agent is constrained to (catalog.prompt())
        </summary>
        <pre>{prompt}</pre>
      </details>
    </>
  );
}
