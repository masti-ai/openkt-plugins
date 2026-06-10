# OpenKT — Codex Plugin

OpenKT (Open Knowledge Transfer) brings persistent memory + context to
Codex (OpenAI's CLI agent). Same backend as the Claude Code plugin —
your memories transfer cleanly between harnesses.

## Hooks

This plugin registers the full OpenKT lifecycle, at parity with the
Claude Code plugin:

- `SessionStart` → `kt prime` (project context + recent decisions)
- `UserPromptSubmit` → `recall.py` (semantic recall) + `capture.py`
  (auto-capture imperative/declarative user statements)
- `PostToolUse` (`Write|Edit|MultiEdit`) → `sync_native_memory.py`
  (syncs harness-native memory writes upstream; a safe no-op on Codex
  until/unless Codex ships a native-memory feature — bundled for
  forward-compat and cross-harness parity)
- `PreCompact` → `pre_compact.py` (checkpoint working state before
  Codex compacts the conversation)
- `Stop` → `session_end.py` (final consolidation at session end)

The hook scripts read the same JSON event shape on stdin in both
harnesses, so they're copied verbatim from `../../shared/hooks/`.

## Prerequisites

1. **kt CLI** — install via `curl -fsSL https://openkt.ai/install.sh | sh`
2. **OpenKT account** — `kt login` (writes token to `~/.openkt/token`,
   patches shell rc, wires Codex MCP)
3. **Codex hook support** — Codex gates plugin-bundled hooks behind a
   feature flag in `~/.codex/config.toml`:

   ```toml
   [features]
   hooks = true
   ```

   Without this set, the hooks are silently skipped. Restart Codex
   after changing.

4. **Trust the hooks** — Codex does not run plugin-provided hooks until
   you explicitly trust them. After installing, run:

   ```
   /hooks
   ```

   inside Codex and approve the OpenKT hooks. Codex shows each command
   it will run; trust is required once per plugin version. Re-run
   `/hooks` after upgrading the plugin if the hook commands changed.

## Install

Until the Codex plugin marketplace formalizes, install by clone:

```
mkdir -p ~/.codex/plugins
git clone https://github.com/openkt-ai/codex-plugin ~/.codex/plugins/openkt
```

The hooks reference `${PLUGIN_ROOT}/hooks/*.py`, which Codex resolves
to this plugin's directory automatically.

After install: set `[features].hooks = true` (above), restart Codex,
then run `/hooks` to trust the OpenKT hooks.

## MCP server

The plugin bundles `.mcp.json` at its root, so the OpenKT MCP servers
ship with the plugin and are picked up on install — no manual
`config.toml` editing required:

```json
{
  "mcpServers": {
    "openkt":       { "url": "https://api.openkt.ai/mcp", "transport": "http",
                      "headers": { "Authorization": "Bearer ${env:OPENKT_TOKEN}" } },
    "openkt-local": { "command": "kt", "args": ["mcp", "serve"] }
  }
}
```

- `openkt` — the hosted memory API (`kt_recall`, `kt_save_memory`,
  `kt_search_memories`, `kt_forget_memory`). Needs `OPENKT_TOKEN`
  exported in the shell that launches Codex (`kt login` patches your
  rc; restart your shell after first install).
- `openkt-local` — the local `kt mcp serve` server, exposing
  auth/install tools (`kt_doctor`, `kt_login`, `kt_install_harness`,
  etc.).

If you prefer to wire the remote server by hand instead of using the
bundled config, `kt login` also writes it into `~/.codex/config.toml`:

```toml
[mcp_servers.openkt]
url = "https://api.openkt.ai/mcp"
bearer_token_env_var = "OPENKT_TOKEN"
```

## Verify

```
kt doctor --json
```

Should report all checks passing. If `codex` shows in the harness
report with `detected: true`, the wiring is in place.

## Project setup

```
cd <your-repo>
kt init
```

Writes `.openkt/manifest.json`. Commit it.

## Troubleshooting

- **Hooks aren't firing**: check `[features].hooks = true` in
  `~/.codex/config.toml`, and confirm you've run `/hooks` to trust the
  OpenKT hooks. Restart Codex after either change.
- **MCP tools not visible to Codex**: confirm `OPENKT_TOKEN` is
  exported in the shell that launches Codex (`kt login` patches the
  rc; restart your shell after first install).
- **`kt: command not found` in hooks**: the hook scripts call `kt`
  on PATH. `kt login` patches your rc; if Codex launches from a
  context where the rc isn't sourced, set `PATH` explicitly.
