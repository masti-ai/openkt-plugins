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
└── codex/openkt/             # Codex plugin
    ├── .codex-plugin/plugin.json
    ├── hooks/
    │   ├── hooks.json        # SessionStart + UserPromptSubmit ONLY
    │   └── *.py              # recall.py, capture.py, _mcp_client.py, _capture_worker.py
    └── README.md
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

## Marketplace install (when published)

### Claude Code

```
/plugin marketplace add openkt-ai/claude-plugin
/plugin install openkt
```

### Codex

The Codex plugin marketplace is still being formalized. Until then,
clone directly:

```
git clone https://github.com/openkt-ai/codex-plugin ~/.codex/plugins/openkt
```

And enable hooks:

```toml
# ~/.codex/config.toml
[features]
plugin_hooks = true
```

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
