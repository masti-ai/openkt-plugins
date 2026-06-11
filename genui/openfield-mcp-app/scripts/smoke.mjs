/**
 * Smoke test for the openkt MCP App server.
 *
 * Spawns `node dist/main.js --stdio`, then drives it as an MCP client to assert
 * the MCP Apps wiring end-to-end without a graphical host:
 *   1. tools/list exposes `show_report` with `_meta.ui.resourceUri`
 *   2. resources/list exposes that `ui://` resource with the mcp-app MIME type
 *   3. resources/read returns a self-contained HTML bundle
 *   4. tools/call show_report returns a catalog-constrained spec as
 *      structuredContent (and a JSON text fallback)
 *
 * Run after `npm run build`:  node scripts/smoke.mjs
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const serverEntry = path.join(here, "..", "dist", "main.js");
const RESOURCE_URI = "ui://openfield/report.html";

const fail = (msg) => {
  console.error(`✗ ${msg}`);
  process.exitCode = 1;
};
const ok = (msg) => console.log(`✓ ${msg}`);

const transport = new StdioClientTransport({
  command: process.execPath,
  args: [serverEntry, "--stdio"],
});
const client = new Client({ name: "smoke", version: "0.0.0" });

try {
  await client.connect(transport);
  ok("connected (initialize handshake)");

  // 1. Tool with UI metadata.
  const { tools } = await client.listTools();
  const tool = tools.find((t) => t.name === "show_report");
  if (!tool) fail("show_report tool missing");
  else ok("show_report tool present");
  const uri = tool?._meta?.ui?.resourceUri ?? tool?._meta?.["ui/resourceUri"];
  if (uri !== RESOURCE_URI) fail(`tool _meta.ui.resourceUri = ${uri}`);
  else ok(`tool bound to ${uri}`);

  // 2. UI resource listed with the mcp-app MIME type.
  const { resources } = await client.listResources();
  const res = resources.find((r) => r.uri === RESOURCE_URI);
  if (!res) fail("ui:// resource missing from resources/list");
  else ok(`resource listed (mimeType=${res.mimeType})`);
  if (res && !String(res.mimeType).startsWith("text/html;profile=mcp-app"))
    fail(`unexpected resource mimeType: ${res.mimeType}`);

  // 3. Resource read returns a self-contained HTML bundle.
  const read = await client.readResource({ uri: RESOURCE_URI });
  const html = read.contents?.[0]?.text ?? "";
  if (!html.includes("<!doctype html") && !html.includes("<!DOCTYPE html"))
    fail("resource is not an HTML document");
  else ok(`resource read (${(html.length / 1024).toFixed(0)} KB HTML)`);
  if (/<script[^>]+src=/.test(html))
    fail("HTML references an external <script src> — not self-contained");
  else ok("HTML bundle is self-contained (no external <script src>)");

  // 4. Tool call returns a catalog-constrained spec.
  const result = await client.callTool({ name: "show_report", arguments: {} });
  const spec = result.structuredContent?.spec;
  if (!spec?.root || !spec?.elements) fail("structuredContent.spec is not a spec");
  else
    ok(
      `show_report → spec (root="${spec.root}", ${Object.keys(spec.elements).length} elements)`,
    );
  const textBlock = result.content?.find((c) => c.type === "text")?.text;
  if (!textBlock || !JSON.parse(textBlock)?.spec)
    fail("text-content JSON fallback missing");
  else ok("text-content JSON fallback present");

  await client.close();
  if (process.exitCode) console.error("\nSMOKE TEST FAILED");
  else console.log("\nALL CHECKS PASSED");
} catch (err) {
  console.error(err);
  process.exitCode = 1;
} finally {
  await transport.close().catch(() => {});
}
