/**
 * An *agent-emitted* spec. This is the kind of JSON a client agent would stream
 * back after being given `catalog.prompt()` as its system prompt and a user task
 * like "show me the state of the Pricing knowledge base." It references only
 * Open Field catalog components; props validate against the catalog's Zod
 * schemas. Hand-authored here to stand in for a live model call.
 */
import type { Spec } from "@json-render/core";

const ascii = `   ___                   _  _______
  / _ \\ _ __  ___ _ _   | |/ /_   _|
 | (_) | '_ \\/ -_) ' \\  | ' <  | |
  \\___/| .__/\\___|_||_| |_|\\_\\ |_|
       |_|   field memory`;

export const memoryDashboard: Spec = {
  root: "page",
  elements: {
    page: {
      type: "Page",
      props: {},
      children: [
        "art",
        "eyebrow",
        "title",
        "lede",
        "stats",
        "div1",
        "kb-card",
        "conflict",
        "div2",
        "table-heading",
        "kb-table",
        "actions",
      ],
    },

    art: {
      type: "AsciiArt",
      props: { art: ascii, category: "clay", dark: true },
      children: [],
    },

    eyebrow: {
      type: "Eyebrow",
      props: { text: "MEMORY SYNTHESIS", category: "clay" },
      children: [],
    },
    title: {
      type: "Heading",
      props: { text: "Pricing knowledge base", level: "hero" },
      children: [],
    },
    lede: {
      type: "Text",
      props: {
        text: "Synthesized from 42 memories across 6 teammates. One conflict resolved, one fork still open.",
        tone: "lede",
      },
      children: [],
    },

    stats: {
      type: "StatGrid",
      props: {},
      children: ["s1", "s2", "s3", "s4"],
    },
    s1: {
      type: "Stat",
      props: { value: "42", label: "memories", accent: false },
      children: [],
    },
    s2: {
      type: "Stat",
      props: { value: "6", label: "contributors", accent: false },
      children: [],
    },
    s3: {
      type: "Stat",
      props: { value: "1", label: "open fork", accent: true },
      children: [],
    },
    s4: {
      type: "Stat",
      props: { value: "94%", label: "confidence", accent: false },
      children: [],
    },

    div1: { type: "Divider", props: { label: "CURRENT STATE" }, children: [] },

    "kb-card": {
      type: "Card",
      props: { title: "What the team currently believes" },
      children: ["kb-row", "kb-body"],
    },
    "kb-row": {
      type: "Section",
      props: {},
      children: ["chip-decision", "tag-pricing", "badge-fresh"],
    },
    "chip-decision": {
      type: "KindChip",
      props: { kind: "decision" },
      children: [],
    },
    "tag-pricing": {
      type: "Tag",
      props: { text: "pricing", category: "ochre" },
      children: [],
    },
    "badge-fresh": {
      type: "Badge",
      props: { text: "fresh", variant: "ok" },
      children: [],
    },
    "kb-body": {
      type: "Text",
      props: {
        text: "Annual plans are discounted 20%. As of last week, the floor moved from $99 to $79 for the startup tier; enterprise pricing stays quote-based.",
        tone: "body",
      },
      children: [],
    },

    conflict: {
      type: "Callout",
      props: {
        text: "⟳ Floor price changed: $79 is current (was $99). Two memories disagreed; the newer decision wins.",
        variant: "warn",
      },
      children: [],
    },

    div2: { type: "Divider", props: { label: null }, children: [] },

    "table-heading": {
      type: "Heading",
      props: { text: "Memories by contributor", level: "h2" },
      children: [],
    },
    "kb-table": {
      type: "Table",
      props: {
        columns: ["Contributor", "Memories", "Latest kind"],
        rows: [
          ["Dana", "14", "decision"],
          ["Ravi", "9", "context"],
          ["Mei", "8", "pattern"],
          ["Tom", "6", "question"],
          ["Ada", "5", "anti-pattern"],
        ],
      },
      children: [],
    },

    actions: {
      type: "Section",
      props: {},
      children: ["btn-export", "btn-refresh"],
    },
    "btn-export": {
      type: "Button",
      props: { label: "Export report", variant: "primary" },
      // wire the press event to the catalog's export_report action
      on: { press: { action: "export_report" } },
      children: [],
    },
    "btn-refresh": {
      type: "Button",
      props: { label: "Refresh", variant: "ghost" },
      on: { press: { action: "refresh" } },
      children: [],
    },
  },
};
