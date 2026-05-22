# openkt-hermes

**The only Hermes memory provider where your teammate's session enriches your agent's context.**

OpenKT is an org-scoped knowledge platform with vector recall, decision/anti-pattern tagging, and team-shared projects. `openkt-hermes` is a thin Python adapter that makes it pluggable into [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) as a `MemoryProvider`.

Every other Hermes memory provider (Honcho, Mem0, Supermemory, Hindsight, Holographic, RetainDB, ByteRover, OpenViking) is single-user. OpenKT's project-scoped data model means multiple teammates' Hermes installs can share one memory pool: decisions, incident postmortems, and anti-patterns written by anyone on the team surface in everyone's recall.

## Install

```bash
pip install openkt-hermes
```

Then drop the plugin into your Hermes home:

```bash
mkdir -p "$HERMES_HOME/plugins/openkt"
# Either symlink (recommended — auto-updates with pip):
ln -s "$(python -c 'import openkt_hermes, os; print(os.path.dirname(openkt_hermes.__file__))')/../../plugins/openkt"/* "$HERMES_HOME/plugins/openkt/"
# Or copy:
cp -r path/to/openkt-hermes/plugins/openkt/* "$HERMES_HOME/plugins/openkt/"
```

Set your token:

```bash
# Mint a PAT at https://openkt.ai/settings/tokens
export OPENKT_API_KEY="okt_pat_..."
```

Activate the provider in `$HERMES_HOME/config.yaml`:

```yaml
memory:
  provider: openkt
```

Confirm:

```bash
$ hermes memory status
Provider:  openkt
Plugin:    installed ✓
Status:    available ✓
```

## Personal mode (default)

No config required — works out of the box. Each Hermes install gets its own isolated memory pool, keyed by `agent_identity` / `user_id` / `hermes_home` hash. Behaves like Mem0 or Supermemory.

```bash
export OPENKT_API_KEY="okt_pat_..."
# Done. Memories accumulate under personal/<identity> in OpenKT.
```

## Team mode (the differentiator)

One config flip and your whole team shares one memory pool. Write a decision once; every teammate's next Hermes session recalls it.

`$HERMES_HOME/openkt.json`:

```json
{
  "default_project_scope": "team",
  "team_project_id": "3d7a7a1a-e603-43ef-81db-f470cff9f3f5"
}
```

Get a `team_project_id` from `kt projects list` or the OpenKT dashboard. Every teammate sets the same `team_project_id`; OpenKT enforces org membership via the project's visibility setting.

Recommended write conventions (these are just kinds — server-side filters/UI surface them prominently):

- `kind: decision` — "we chose X over Y because Z"
- `kind: anti-pattern` — "don't do X without Y"
- `kind: incident` — "symptom S was caused by C; fix is F"
- `kind: pattern` — "the right way to do P is Q"
- `kind: context` — background facts (the default for auto-captures)

## What gets wired into Hermes

| Hermes hook | OpenKT behavior |
|---|---|
| `is_available()` | Returns True if `OPENKT_API_KEY` is set (no network call). |
| `initialize()` | Resolves project_id from kwargs+config; constructs HTTP client. |
| `system_prompt_block()` | `POST /v1/prime` → categorized decisions + anti-patterns into the system prompt. |
| `prefetch(query)` | Sync recall + format as Hermes additional-context block. |
| `queue_prefetch(query)` | Daemon thread → cache for next turn. |
| `sync_turn(user, asst)` | Daemon thread → save substantive assistant content; skips trivial acks. |
| `handle_tool_call()` | Dispatches `openkt_recall` / `openkt_save_memory` / `openkt_search_memories` / `openkt_forget_memory` (returns JSON). |
| `on_session_end()` | Daemon thread → save last meaningful user/assistant turns. |
| `on_pre_compress()` | Recall against last user message → string for the compression summary. |
| `on_memory_write()` | Mirror built-in MEMORY.md/USER.md writes into OpenKT. |
| `on_delegation()` | Save subagent task+result so the parent can recall it. |

`sync_turn`, `queue_prefetch`, `on_memory_write`, `on_session_end`, `on_delegation` all run in daemon threads — never block the turn response.

## Auth: PAT vs JWT

Two transport paths, picked automatically by token prefix:

- **`okt_pat_...`** — routed through `https://api.openkt.ai/mcp` (JSON-RPC). Works because the MCP endpoint accepts PATs via `BearerAuthGuard`. **Recommended** for headless / CI / multi-tenant use.
- **Supabase JWT** (`eyJ...`) — routed through `https://api.openkt.ai/v1/memories/*` (REST). Faster (no JSON-RPC envelope, no SSE framing). Useful during local dev via `kt login`.

Either token type works. The provider hides the transport choice from the caller.

Known gap: `POST /v1/prime` is JWT-only today. PAT users get `system_prompt_block() = ""` (no standing context block) but still get full recall + save. Server team plans to expose prime via `BearerAuthGuard`.

## Configuration reference

`$HERMES_HOME/openkt.json` — all keys optional, defaults shown:

```json
{
  "api_base": "https://api.openkt.ai",
  "default_project_scope": "personal",
  "team_project_id": "",
  "default_kind": "context",
  "default_importance": 0.5,
  "recall_limit": 5,
  "recall_vector_weight": 0.85,
  "recall_rerank": true,
  "recall_min_confidence": 0.6,
  "request_timeout_s": 8.0
}
```

The API key NEVER lives in this file — it comes from `OPENKT_API_KEY` (or `OPENKT_TOKEN`) env vars. A leaked `openkt.json` carries no credentials.

## Tool schemas (what the model sees)

- `openkt_recall(query, limit?, kind?)` — semantic+keyword recall (rerank by default). Returns the most relevant memories. Use BEFORE answering any non-trivial project question.
- `openkt_save_memory(content, kind?, importance?, tag_slugs?)` — save a fact/decision/anti-pattern. Use proactively when you learn something the next agent should know.
- `openkt_search_memories(query, limit?, kind?)` — browse/list without bumping recall counters.
- `openkt_forget_memory(id, hard?)` — archive (soft) or hard-delete (owner-only).

## Project_id resolution precedence

When multiple inputs are present, the highest-priority one wins:

1. `agent_workspace` kwarg (per-process override)
2. `team_project_id` config (team mode active)
3. `agent_identity` kwarg → `personal/<identity>`
4. `user_id` kwarg → `personal/<user>`
5. SHA256 hash of `hermes_home` → `personal/host-<hash>` (last resort)

## Development

```bash
pip install -e ".[test]"
pytest -v
```

Live integration tests run against `api.openkt.ai` when both env vars are set:

```bash
OPENKT_API_KEY=okt_pat_... \
OPENKT_TEST_PROJECT_ID=<a-real-uuid> \
pytest tests/test_integration.py -v
```

Without those vars, the integration suite skips cleanly so unit tests stay CI-friendly.

## License

MIT. See `LICENSE`.
