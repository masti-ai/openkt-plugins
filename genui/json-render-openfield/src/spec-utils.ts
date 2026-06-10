/**
 * Tiny normalizer for agent-emitted specs.
 *
 * This json-render version's React schema marks every element's `visible` field
 * as required (non-optional), even though `<Renderer>` happily renders elements
 * that omit it. A real client normalizes / repairs streamed model output before
 * validating it against the catalog; this is the minimal version of that step —
 * it fills the structural defaults (`visible: true`, `children: []`) so the spec
 * passes `catalog.validate()`. Authored specs stay clean and intent-only.
 */
import type { Spec, UIElement } from "@json-render/core";

export function withDefaults(spec: Spec): Spec {
  const elements: Record<string, UIElement> = {};
  for (const [id, el] of Object.entries(spec.elements)) {
    elements[id] = {
      children: [],
      visible: true,
      ...el,
    };
  }
  return { ...spec, elements };
}
