/**
 * Open Field component catalog for json-render.
 *
 * This is the *contract* an agent generates against. `defineCatalog` pairs each
 * component name with a Zod prop schema + a description; `catalog.prompt()` turns
 * the whole thing into the system prompt the model is constrained to. The model
 * can only emit these component types, with props that pass these schemas —
 * which is exactly the Open Field "the design language is not optional" rule,
 * enforced at the data layer instead of by convention.
 *
 * Tokens / classes referenced here come from `openfield.css` (vendored from
 * masti-ai/openfield via the openkt-demos plugin's openkt-pages.css). The
 * registry (registry.tsx) maps each component to those classes.
 */
import { defineCatalog } from "@json-render/core";
import { schema } from "@json-render/react/schema";
import { z } from "zod";

/** The five Deepwork earth categories — used for eyebrows, tags, ASCII art tint. */
const earth = z.enum(["clay", "ochre", "sand", "moss", "slate"]);

/** OpenKT memory kinds — the kind-chip palette. */
const memoryKind = z.enum([
  "context",
  "decision",
  "pattern",
  "anti-pattern",
  "question",
]);

export const catalog = defineCatalog(schema, {
  components: {
    /* ── Structure ─────────────────────────────────────────────── */
    Page: {
      props: z.object({}),
      slots: ["default"],
      description:
        "Top-level page wrapper (<main>). Put every other element inside one Page.",
    },
    Section: {
      props: z.object({}),
      slots: ["default"],
      description: "Vertical group of elements with standard spacing.",
    },
    Eyebrow: {
      props: z.object({
        text: z.string().describe("Short uppercase kicker label."),
        category: earth.nullable().describe("Earth accent color for the dot."),
      }),
      description: "The universal mono kicker that sits above a heading.",
      example: { text: "MEMORY SYNTHESIS", category: "clay" },
    },
    Heading: {
      props: z.object({
        text: z.string(),
        level: z
          .enum(["hero", "h1", "h2", "h3"])
          .describe("Display size; hero is the page title."),
      }),
      description: "A serif display heading.",
      example: { text: "Pricing knowledge base", level: "h1" },
    },
    Text: {
      props: z.object({
        text: z.string(),
        tone: z
          .enum(["body", "lede", "small", "dim"])
          .nullable()
          .describe("Emphasis; lede is a large intro paragraph."),
      }),
      description: "A paragraph of body copy.",
    },
    Divider: {
      props: z.object({
        label: z
          .string()
          .nullable()
          .describe("Optional centered label for a labeled rule."),
      }),
      description: "Horizontal rule, optionally labeled.",
    },

    /* ── Containers ────────────────────────────────────────────── */
    Card: {
      props: z.object({
        title: z.string().nullable(),
      }),
      slots: ["default"],
      description: "Bordered paper container. Children render inside it.",
    },
    Callout: {
      props: z.object({
        text: z.string(),
        variant: z
          .enum(["note", "success", "warn", "danger", "accent"])
          .describe("Semantic color of the left border."),
      }),
      description: "A left-bordered note/aside for emphasis.",
      example: { text: "Two facts conflict here.", variant: "warn" },
    },

    /* ── Data display ──────────────────────────────────────────── */
    StatGrid: {
      props: z.object({}),
      slots: ["default"],
      description: "Responsive grid of Stat tiles.",
    },
    Stat: {
      props: z.object({
        value: z.string(),
        label: z.string(),
        accent: z
          .boolean()
          .nullable()
          .describe("Render the value in the amber accent."),
      }),
      description: "A single KPI tile (big value + small label).",
      example: { value: "183", label: "memories", accent: false },
    },
    Table: {
      props: z.object({
        columns: z.array(z.string()),
        rows: z
          .array(z.array(z.string()))
          .describe("Each row is an array of cell strings aligned to columns."),
      }),
      description: "A simple data table.",
      example: {
        columns: ["KB", "Memories", "Owner"],
        rows: [["Pricing", "42", "Dana"]],
      },
    },

    /* ── Chips & status ────────────────────────────────────────── */
    KindChip: {
      props: z.object({
        kind: memoryKind,
      }),
      description:
        "OpenKT memory-kind chip (context / decision / pattern / anti-pattern / question).",
      example: { kind: "decision" },
    },
    Badge: {
      props: z.object({
        text: z.string(),
        variant: z
          .enum(["ok", "warn", "danger", "info", "accent"])
          .nullable(),
      }),
      description: "A status pill.",
      example: { text: "green", variant: "ok" },
    },
    Tag: {
      props: z.object({
        text: z.string(),
        category: earth,
      }),
      description: "An earth-colored content label.",
      example: { text: "infra", category: "slate" },
    },

    /* ── Generative ASCII art slot ─────────────────────────────── */
    AsciiArt: {
      props: z.object({
        art: z
          .string()
          .describe("Pre-formatted ASCII art (newlines preserved)."),
        category: earth
          .nullable()
          .describe("Earth accent color to tint the art."),
        dark: z
          .boolean()
          .nullable()
          .describe("Mount on an inverted dark panel."),
      }),
      description:
        "A slot for Deepwork generative ASCII art, colored from the palette.",
      example: {
        art: "  ╱╲  ╱╲\n ╱  ╲╱  ╲\n╱        ╲",
        category: "clay",
        dark: true,
      },
    },

    /* ── Interaction ───────────────────────────────────────────── */
    Button: {
      props: z.object({
        label: z.string(),
        variant: z.enum(["default", "primary", "ghost"]).nullable(),
      }),
      description:
        "A button. Wire it to a catalog action via the element's `on: { press: ... }` field.",
      example: { label: "Export report", variant: "primary" },
    },
  },

  actions: {
    export_report: { description: "Export the current view to a file." },
    refresh: { description: "Refresh the data behind the view." },
    open_memory: {
      params: z.object({ id: z.string() }),
      description: "Open a single memory by id.",
    },
  },
});

export type OpenFieldCatalog = typeof catalog;
