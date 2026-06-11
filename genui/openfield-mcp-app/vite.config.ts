import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

// The HTML shell that becomes the `ui://` resource. Passed via env so the same
// config drives `vite dev` (no INPUT) and the single-file build (`INPUT=report.html`).
const INPUT = process.env.INPUT;
const isDevelopment = process.env.NODE_ENV === "development";

export default defineConfig({
  // `viteSingleFile` inlines every JS/CSS asset into one HTML file. MCP Apps
  // hosts render the `ui://` resource in a sandboxed iframe under a strict
  // default CSP (`default-src none; connect-src none` when `ui.csp` is omitted),
  // so the renderer + Open Field registry + tokens MUST be self-contained — no
  // runtime fetches. That is exactly what a single-file bundle guarantees.
  plugins: [react(), viteSingleFile()],
  build: {
    sourcemap: isDevelopment ? "inline" : undefined,
    cssMinify: !isDevelopment,
    minify: !isDevelopment,
    rollupOptions: INPUT ? { input: INPUT } : undefined,
    outDir: "dist",
    emptyOutDir: true,
  },
});
