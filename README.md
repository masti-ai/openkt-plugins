# OpenKT Plugins

Per-harness packaging for [OpenKT](https://openkt.ai) — the persistent
memory + context layer for AI agents.

This repo holds **plugin manifests + glue** for each supported harness.
The actual memory / search / API logic lives upstream in
[openkt-cli](https://github.com/masti-ai/openkt-cli) (the `kt` binary)
and [openkt-server](https://github.com/openkt-ai/openkt-server) (the
hosted API + MCP).

## Layout

```
openkt-plugins/
├── shared/                   # Single source of truth for cross-harness assets
│   ├── hooks/                # Python hook scripts (harness-agnostic)
│   ├── skills/               # Markdown skills (memory-curator, recall, doctor)
│   └── commands/             # Slash command markdown
│
├── claude-code/openkt/       # Claude Code plugin
│   ├── .claude-plugin/plugin.json
│   ├── .mcp.json             # Two MCP servers: remote + local kt mcp serve
│   ├── hooks/                # Hooks copied from ../shared/hooks/
│   │   └── hooks.json        # SessionStart, UserPromptSubmit, PostToolUse, PreCompact, SessionEnd
│   ├── skills/               # Copied from ../shared/skills/
│   ├── commands/             # Copied from ../shared/commands/
│   └── README.md
│
├── codex/openkt/             # Codex plugin
│   ├── .codex-plugin/plugin.json
│   ├── hooks/
│   │   ├── hooks.json        # SessionStart + UserPromptSubmit ONLY
│   │   └── *.py              # recall.py, capture.py, _mcp_client.py, _capture_worker.py
│   └── README.md
│
├── hermes/                   # Hermes Agent (NousResearch) memory provider
│   ├── src/openkt_hermes/    # Python pip-installable package
│   ├── plugins/openkt/       # Drop-in for $HERMES_HOME/plugins/openkt/
│   ├── tests/                # 59 unit + 2 gated integration tests
│   ├── pyproject.toml
│   └── README.md
│
├── .claude-plugin/marketplace.json   # Claude Code marketplace manifest
└── .agents/plugins/marketplace.json  # Codex marketplace manifest
```

## Why separate plugins?

Each harness has its own plugin format and hook lifecycle:

| Hook | Claude Code | Codex |
|------|------------|-------|
| SessionStart | ✓ | ✓ |
| UserPromptSubmit | ✓ | ✓ |
| PostToolUse | ✓ | ✗ (not in spec) |
| PreCompact | ✓ | ✗ |
| SessionEnd | ✓ | ✗ |

The Codex plugin omits the hooks Codex doesn't fire. Shared hook
scripts (`recall.py`, `capture.py`) work in both because they read the
same JSON event shape on stdin.

## Install

### Claude Code

```
/plugin marketplace add masti-ai/openkt-plugins
/plugin install openkt@openkt
```

### Codex

Codex's official directory is "coming soon" (per OpenAI's plugin docs).
Until then, add this repo as a personal marketplace:

```
/plugin marketplace add masti-ai/openkt-plugins
```

Enable plugin-bundled hooks:

```toml
# ~/.codex/config.toml
[features]
plugin_hooks = true
```

### Hermes (NousResearch hermes-agent)

```
pip install openkt-hermes
export OPENKT_API_KEY="okt_pat_..."
echo 'memory: {provider: openkt}' >> "$HERMES_HOME/config.yaml"
```

For team mode (shared memory across teammates), see `hermes/README.md`.

## Dev workflow

When updating shared assets:

1. Edit files under `shared/hooks/`, `shared/skills/`, or
   `shared/commands/`
2. Re-run the copy script (TODO: add `make sync` target):
   ```
   cp shared/hooks/*.py claude-code/openkt/hooks/
   cp -r shared/skills/* claude-code/openkt/skills/
   cp shared/commands/*.md claude-code/openkt/commands/
   cp shared/hooks/recall.py shared/hooks/capture.py \
      shared/hooks/_mcp_client.py shared/hooks/_capture_worker.py \
      shared/hooks/_sync_worker.py codex/openkt/hooks/
   ```
3. Test in your harness (see per-plugin README).

## Versioning

Both plugins follow the same semver. Bumps live in:
- `claude-code/openkt/.claude-plugin/plugin.json` → `version`
- `codex/openkt/.codex-plugin/plugin.json` → `version`

The hooks themselves don't version separately — they're sourced from
the `kt` CLI's `internal/wire/hooks/*.py`, so the kt binary version is
the source of truth for hook behaviour.
