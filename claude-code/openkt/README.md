# OpenKT — Claude Code Plugin

OpenKT (Open Knowledge Transfer) is the persistent memory + context
layer for Claude Code agents. Every decision, anti-pattern, and
non-obvious project fact you (or the agent) learn in one session is
captured, indexed, and auto-injected on every prompt in every future
session.

## What this plugin gives you

- **Auto-recall** on every prompt — the UserPromptSubmit hook calls
  the OpenKT MCP server and injects matching memories into the agent's
  context before it responds.
- **Auto-capture** of imperative/declarative things you say (decisions,
  preferences, corrections) — saved silently in the background, rate-
  limited so it doesn't spam.
- **Two MCP servers**:
  - `openkt` (remote): the hosted OpenKT memory layer with kt_recall,
    kt_save_memory, kt_search_memories, kt_forget_memory tools
  - `openkt-local` (stdio): the local `kt` binary exposing
    authentication, install, and project-binding tools (kt_doctor,
    kt_login, kt_install_harness, kt_init, etc.)
- **Slash commands**: `/openkt:recall`, `/openkt:remember`,
  `/openkt:doctor`, `/openkt:login`
- **Skills**: memory-curator (proactive memory writing),
  memory-recall (targeted lookups), memory-doctor (troubleshoot)

## Install

### From the marketplace (when published)

```
/plugin marketplace add openkt-ai/claude-plugin
/plugin install openkt
```

### From source

```
git clone https://github.com/openkt-ai/claude-plugin ~/.claude/plugins/openkt
```

### Prerequisite: install the kt CLI

```
curl -fsSL https://openkt.ai/install.sh | sh
kt login
```

`kt login` writes your token to `~/.openkt/token`, patches your shell rc
to export `OPENKT_TOKEN`, and registers OpenKT MCP with the harnesses
you have installed. The plugin's hooks read that token to make MCP
calls.

## Verify

```
/openkt:doctor
```

Should report all checks passing. If anything fails, the doctor output
includes the fix.

## Project setup

Once logged in, bind any repo to an OpenKT project:

```
cd <your-repo>
kt init
```

That writes `.openkt/manifest.json` (commit it — anyone cloning the
repo picks up the same project). Now every memory you write while
inside this directory is scoped to this project.

## How it works (TL;DR)

- SessionStart → `kt prime` injects the project's standing decisions
  + anti-patterns as opening context
- UserPromptSubmit → `recall.py` pushes matching memories before the
  agent sees your message; `capture.py` saves declarative/imperative
  things you said in the background
- PostToolUse (Write/Edit/MultiEdit) → `sync_native_memory.py` mirrors
  Claude's native memory_remember writes into OpenKT so cross-session
  recall finds them too

All hooks fail open — an OpenKT outage degrades to "no extra context"
rather than blocking your prompts.

## Customizing

The plugin reads `OPENKT_TOKEN` from your env (set by `kt login`).
Override the API base for staging/dev:

```
export OPENKT_API_BASE=http://localhost:4100
export OPENKT_MCP_URL=http://localhost:4100/mcp
```

## Privacy

Memories are stored on api.openkt.ai (hosted) by default. Per-project
visibility is controlled by your OpenKT org settings. Self-hosting is
on the roadmap; see https://openkt.ai for status.
