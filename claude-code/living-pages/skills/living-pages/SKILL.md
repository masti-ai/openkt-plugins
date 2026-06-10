---
name: living-pages
description: Turn a directory of static HTML pages into a live commenting surface. Injects a feedback library, starts a tiny server, and routes user comments into a JSONL inbox that the agent monitors and responds to by editing the pages. Trigger phrases — "make this page interactive", "make these pages living", "let me comment on this page", "add feedback to these pages", "living pages".
---

# Living Pages

Turns any folder of HTML files into a surface the user can mark up — text
selections, element selections, page-level notes. Comments POST to a local
JSONL inbox; you (the agent) monitor that inbox, edit the HTML in response,
append to `feedback/history.json`, and the page auto-reloads with a walkthrough
of what changed. Pages that respond — living pages.

## When to invoke

User says any of:
- "make this page interactive" / "make these pages living" → **Setup flow**
- "add feedback to this page" / "let me comment on this page" → **Setup flow**
- "set up living pages on <dir>" → **Setup flow**
- "stop the feedback server" / "kill the server" → **Stop flow**
- "remove the feedback layer" / "make pages static again" → **Removal flow**

## Setup flow

1. **Identify the target directory.** Usually the user's current working
   directory or a folder they named. If ambiguous, ask.
2. **Inject the feedback tags** into every `*.html` in that directory:
   ```
   python ${CLAUDE_PLUGIN_ROOT}/scripts/inject.py <dir>
   ```
   Add `--recursive` if the pages live in subfolders. The script is idempotent —
   safe to re-run. It also creates `<dir>/feedback/inbox.jsonl` and
   `<dir>/feedback/history.json` if missing.
3. **Pick a port.** Default 5050. Before starting, check what's there:
   ```
   curl -s --max-time 2 http://localhost:5050/info
   ```
   - JSON with `artifact_dir` matching this `<dir>` → reuse it, skip to step 5.
   - JSON with a *different* `artifact_dir` → port held by another exploration.
     Either ask the user to free it (`lsof -ti:5050 | xargs kill`) or try 5051,
     5052, … (tell the user the URL).
   - No response → port 5050 is free.
4. **Start the server in the background** via Bash with `run_in_background: true`:
   ```
   python ${CLAUDE_PLUGIN_ROOT}/lib/server.py <dir> --port <chosen>
   ```
   The server auto-shuts-down on parent death or 10 min of idle, so you don't
   need to manage its lifecycle.
5. **Tell the user the URL.** For example: `http://localhost:5050/index.html`
   (use whatever filename they actually have). If they have multiple pages,
   list the top-level ones.
6. **Start a Monitor on the inbox** so new comments notify you immediately:
   ```
   Monitor on path: <dir>/feedback/inbox.jsonl
   ```
   Do NOT poll — let the Monitor notification arrive.

## Responding to a feedback batch

When a new batch arrives in `inbox.jsonl`:
- Read the entry. Each comment has a stable `cf_id` and a selector pointing to
  the exact element/text the user commented on.
- Edit the relevant HTML files to address each comment. Wrap each modified
  region with `<span data-cf-change="ch-<short-slug>">…</span>` (or add
  `data-cf-change` to an existing wrapping element) so the post-reload
  walkthrough can find the change. One anchor per change.
- **Append** a new batch object to the end of `<dir>/feedback/history.json`
  (newest = last; the library walks from the end to find the latest batch).
  Schema:
  ```json
  {
    "batch_id": "b-<timestamp-or-slug>",
    "timestamp": "<ISO 8601>",
    "comments": [ /* echo back the inbox comments you addressed */ ],
    "changes": [
      {
        "id": "ch-<slug>",
        "in_response_to": ["<cf_id from inbox>"],
        "anchor": "ch-<slug>",
        "title": "short, concrete",
        "description": "longer prose (hidden in UI, just for the record)"
      }
    ]
  }
  ```
- The page polls `history.json`, sees the new batch, auto-reloads (scroll
  position preserved), and offers the user a walkthrough of the changes. The
  processing banner clears automatically when any `in_response_to` matches a
  submitted comment id.

## On startup in a directory that already has feedback

If you find `<dir>/feedback/inbox.jsonl` and `<dir>/feedback/history.json` and
the skill has been invoked in this session:
1. Scan inbox for comment ids.
2. Scan history's `changes[*].in_response_to` union — those are already processed.
3. If unprocessed comments exist, tell the user the count and ask whether to
   process now.
4. Either way, set up the Monitor on the inbox.

## Stop flow

1. Identify the port. If you started the server in this session, you know it.
   Otherwise check `curl -s http://localhost:5050/info` (try 5051, 5052 if 5050
   returns nothing or a different artifact).
2. Kill it: `lsof -ti:<port> | xargs kill` (use `kill -9` only if a plain kill
   doesn't free the port within a few seconds — the server traps SIGTERM and
   exits cleanly).
3. Confirm: `lsof -i :<port>` should be silent.

Note: in most cases the user doesn't need to manually stop the server. It
auto-shuts-down when (a) the parent process dies or (b) no client requests for
10 min. Manual stop is for when they want the port back right now.

## Removal flow (clean static copy)

```
python ${CLAUDE_PLUGIN_ROOT}/scripts/inject.py <dir> --remove
```
Strips both tags from every `*.html`. Leaves the `feedback/` directory alone
(delete manually if not wanted).

## Files in this plugin

```
living-pages/
├── .claude-plugin/plugin.json
├── skills/living-pages/SKILL.md   # this file
├── lib/
│   ├── feedback.js                # client: selection + commenting + walkthrough
│   ├── feedback.css               # Open Field styling (paper + ink + one amber)
│   └── server.py                  # stdlib-only HTTP server
└── scripts/
    └── inject.py                  # idempotent tag injection / removal
```

## Gotchas

- The injected `<link>` and `<script>` reference absolute paths
  `/lib/feedback.css` and `/lib/feedback.js`. These resolve through
  `server.py`, which routes `/lib/*` to the plugin's own `lib/` directory.
  Pages only work when opened through this server — opening the HTML file
  directly in a browser silently skips the widget (the page itself renders).
- `history.json` order matters: append, don't prepend.
- `anchor` values must match a `data-cf-change` attribute actually present in
  the HTML. Typos cause "anchor not found" warnings post-reload.
- The widget is styled in the Open Field design language and is self-contained
  (tokens inlined, `cf-` prefixed) — it won't fight the host page's CSS.
