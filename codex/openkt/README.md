# OpenKT — Codex Plugin

OpenKT (Open Knowledge Transfer) brings persistent memory + context to
Codex (OpenAI's CLI agent). Same backend as the Claude Code plugin —
your memories transfer cleanly between harnesses.

## Hooks

Per Codex's hook spec, this plugin registers only:

- `SessionStart` → `kt prime` (project context + recent decisions)
- `UserPromptSubmit` → `recall.py` (semantic recall) + `capture.py`
  (auto-capture imperative/declarative user statements)

Codex does NOT fire `PostToolUse`, `PreCompact`, or `SessionEnd` in the
current spec, so those hooks from the Claude Code plugin aren't
registered here. Native-memory sync isn't relevant (Codex doesn't have
a native memory feature today).

## Prerequisites

1. **kt CLI** — install via `curl -fsSL https://openkt.ai/install.sh | sh`
2. **OpenKT account** — `kt login` (writes token to `~/.openkt/token`,
   patches shell rc, wires Codex MCP)
3. **Codex hook support** — Codex gates plugin hooks behind a feature
   flag in `~/.codex/config.toml`:

   ```
   [features]
   plugin_hooks = true
   ```

   Without this set, the hooks are silently skipped. Restart Codex
   after changing.

## Install

Until the Codex plugin marketplace formalizes, install by clone:

```
mkdir -p ~/.codex/plugins
git clone https://github.com/openkt-ai/codex-plugin ~/.codex/plugins/openkt
```

The hooks reference `${CODEX_PLUGIN_ROOT}/hooks/*.py` which Codex
resolves to this directory automatically.

## MCP server (separate from plugin)

The plugin registers hooks only. The MCP server is wired by `kt login`
into `~/.codex/config.toml`:

```toml
[mcp_servers.openkt]
url = "https://api.openkt.ai/mcp"
bearer_token_env_var = "OPENKT_TOKEN"
```

You can also use the local kt mcp server (auth + install tools) by
adding to `~/.codex/config.toml`:

```toml
[mcp_servers.openkt-local]
command = "kt"
args = ["mcp", "serve"]
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

- **Hooks aren't firing**: check `[features].plugin_hooks = true` in
  `~/.codex/config.toml`. Restart Codex.
- **MCP tools not visible to Codex**: confirm
  `bearer_token_env_var = "OPENKT_TOKEN"` is set and `OPENKT_TOKEN` is
  exported in the shell that launches Codex (`kt login` patches the
  rc; restart your shell after first install).
- **`kt: command not found` in hooks**: the hook scripts call `kt`
  on PATH. `kt login` patches your rc; if Codex launches from a
  context where the rc isn't sourced, set `PATH` explicitly.
