/**
 * Entry point for the openkt MCP App server.
 *
 *   node dist/main.js --stdio   → stdio transport (Claude Desktop, VS Code, …)
 *   node dist/main.js           → Streamable HTTP on $PORT (default 3001) for
 *                                 MCPJam / the MCP Inspector and other HTTP hosts
 *
 * Two transports because our primary host (Claude Desktop) speaks stdio, while
 * the inspectors we test against (no Claude Desktop access in CI) speak HTTP.
 */
import { randomUUID } from "node:crypto";
import express, { type Request, type Response } from "express";
import cors from "cors";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { createServer } from "./server.js";

const MCP_PATH = "/mcp";

async function startStdio(): Promise<void> {
  await createServer().connect(new StdioServerTransport());
  // Stdout is the transport — log to stderr only.
  console.error("openkt-openfield MCP server ready on stdio");
}

async function startHttp(): Promise<void> {
  const port = Number.parseInt(process.env.PORT ?? "3001", 10);
  const app = express();
  app.use(express.json());
  // MCP Apps inspectors are browser-based; allow the dev-time cross-origin call
  // and expose the session-id header the Streamable HTTP transport uses.
  app.use(
    cors({
      origin: true,
      exposedHeaders: ["Mcp-Session-Id"],
      allowedHeaders: ["Content-Type", "Mcp-Session-Id", "MCP-Protocol-Version"],
    }),
  );

  // Stateless: a fresh server + transport per request. Simple and robust for a
  // prototype; no session bookkeeping to leak.
  app.all(MCP_PATH, async (req: Request, res: Response) => {
    const server = createServer();
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => randomUUID(),
    });
    res.on("close", () => {
      transport.close().catch(() => {});
      server.close().catch(() => {});
    });
    try {
      await server.connect(transport);
      await transport.handleRequest(req, res, req.body);
    } catch (err) {
      console.error("MCP request error:", err);
      if (!res.headersSent) {
        res.status(500).json({
          jsonrpc: "2.0",
          error: { code: -32603, message: "Internal server error" },
          id: null,
        });
      }
    }
  });

  const httpServer = app.listen(port, () => {
    console.error(
      `openkt-openfield MCP server listening on http://localhost:${port}${MCP_PATH}`,
    );
  });

  const shutdown = () => httpServer.close(() => process.exit(0));
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

async function main(): Promise<void> {
  if (process.argv.includes("--stdio")) {
    await startStdio();
  } else {
    await startHttp();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
