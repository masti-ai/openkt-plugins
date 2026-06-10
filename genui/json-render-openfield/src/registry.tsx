/**
 * Open Field registry — maps each catalog component to its Open Field markup.
 *
 * Every renderer emits only Open Field classes (from openfield.css). No inline
 * colors, fonts, or spacing — the design language lives entirely in the tokens.
 * Swap this registry for a React Native / shadcn / terminal one and the same
 * agent-emitted spec renders on a different surface; that is the json-render
 * promise this prototype is validating.
 */
import { defineRegistry } from "@json-render/react";
import { catalog } from "./catalog";

const cx = (...parts: Array<string | false | null | undefined>) =>
  parts.filter(Boolean).join(" ");

export const { registry, handlers } = defineRegistry(catalog, {
  components: {
    /* ── Structure ─────────────────────────────────────────────── */
    Page: ({ children }) => <main className="of-page">{children}</main>,

    Section: ({ children }) => <section className="stack">{children}</section>,

    Eyebrow: ({ props }) => (
      <div className={cx("eyebrow", props.category && `is-${props.category}`)}>
        <span className="dot">●</span>
        {props.text}
      </div>
    ),

    Heading: ({ props }) => {
      const cls = { hero: "t-hero", h1: "t-h1", h2: "t-h2", h3: "t-h3" }[
        props.level
      ];
      if (props.level === "h3") return <h3 className={cls}>{props.text}</h3>;
      if (props.level === "h2") return <h2 className={cls}>{props.text}</h2>;
      return <h1 className={cls}>{props.text}</h1>;
    },

    Text: ({ props }) => {
      const tone = props.tone ?? "body";
      const cls = {
        body: "t-body",
        lede: "t-lede",
        small: "t-small",
        dim: "t-body dim",
      }[tone];
      return <p className={cls}>{props.text}</p>;
    },

    Divider: ({ props }) =>
      props.label ? (
        <div className="divider-labeled">
          <span className="lbl">{props.label}</span>
        </div>
      ) : (
        <hr className="divider" />
      ),

    /* ── Containers ────────────────────────────────────────────── */
    Card: ({ props, children }) => (
      <div className="card" style={{ padding: "var(--sp-5)" }}>
        {props.title && (
          <h3 className="t-h3" style={{ marginBottom: "var(--sp-3)" }}>
            {props.title}
          </h3>
        )}
        {children}
      </div>
    ),

    Callout: ({ props }) => (
      <div className={cx("callout", `callout-${props.variant}`)}>
        {props.text}
      </div>
    ),

    /* ── Data display ──────────────────────────────────────────── */
    StatGrid: ({ children }) => <div className="stat-grid">{children}</div>,

    Stat: ({ props }) => (
      <div className={cx("stat", props.accent && "stat-accent")}>
        <div className="stat-value">{props.value}</div>
        <div className="stat-label">{props.label}</div>
      </div>
    ),

    Table: ({ props }) => (
      <table className="of-table">
        <thead>
          <tr>
            {props.columns.map((c, i) => (
              <th key={i}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {props.rows.map((row, r) => (
            <tr key={r}>
              {row.map((cell, c) => (
                <td key={c}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    ),

    /* ── Chips & status ────────────────────────────────────────── */
    KindChip: ({ props }) => (
      <span className={cx("kind", `kind-${props.kind}`)}>{props.kind}</span>
    ),

    Badge: ({ props }) => (
      <span className={cx("badge", props.variant && `badge-${props.variant}`)}>
        {props.text}
      </span>
    ),

    Tag: ({ props }) => (
      <span className={cx("tag", `is-${props.category}`)}>{props.text}</span>
    ),

    /* ── Generative ASCII art slot ─────────────────────────────── */
    AsciiArt: ({ props }) => (
      <div
        className={cx(props.dark && "dark")}
        style={props.dark ? { padding: "var(--sp-5)" } : undefined}
      >
        <pre
          className={cx("art", props.category && `is-${props.category}`)}
          style={props.category ? { color: `var(--c-${props.category})` } : undefined}
        >
          {props.art}
        </pre>
      </div>
    ),

    /* ── Interaction ───────────────────────────────────────────── */
    Button: ({ props, emit }) => (
      <button
        className={cx(
          "btn",
          props.variant === "primary" && "btn-primary",
          props.variant === "ghost" && "btn-ghost",
        )}
        onClick={() => emit("press")}
      >
        {props.label}
      </button>
    ),
  },

  // Action handlers the agent's spec can bind to via `on: { press: "..." }`.
  // In a real client these would call the host (export a file, refetch, open a
  // memory). Here they log so the prototype is self-contained.
  actions: {
    export_report: async () => {
      // eslint-disable-next-line no-console
      console.log("[action] export_report");
    },
    refresh: async () => {
      // eslint-disable-next-line no-console
      console.log("[action] refresh");
    },
    open_memory: async (params) => {
      // eslint-disable-next-line no-console
      console.log("[action] open_memory", params?.id);
    },
  },
});
