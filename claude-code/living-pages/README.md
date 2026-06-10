# living-pages

Pages you can mark up.

Turns any folder of HTML into a live commenting surface — highlight text,
select elements, leave page-level notes. Your agent reads the margins and
revises; the page reloads with a walkthrough of what changed.

Built on [make-pages-interactive](https://github.com/paraschopra/make-pages-interactive)
by Paras Chopra (MIT), restyled in the Open Field design language — warm paper,
ink, one amber accent, monospace loading. The widget is self-contained and
`cf-` prefixed, so it won't fight the host page's CSS.

## Install

```
/plugin marketplace add masti-ai/openkt-plugins
/plugin install living-pages@openkt
```

## Use

In any project with HTML output, ask: *"make this page interactive"*,
*"let me comment on this page"*, or *"set up living pages here"*.

The agent injects the feedback layer, starts a local server, and watches the
inbox. You browse the page, mark it up, submit a batch. The agent edits the
HTML and the page reloads with a tour of the changes.

## How it works

```
you: highlight · select · note        agent: monitors inbox
        │                                     │
        └── POST /comment ──→ feedback/inbox.jsonl
                                              │
        page auto-reload ←── feedback/history.json ←── edits + batch entry
        (walkthrough of changes)
```

- `lib/server.py` — stdlib-only HTTP server. Serves the pages, accepts comment
  POSTs, shuts itself down on parent death or 10 minutes idle.
- `lib/feedback.js` — selection, commenting, processing state, change tour.
- `lib/feedback.css` — Open Field styling, tokens inlined.
- `scripts/inject.py` — idempotent tag injection / removal.

## Pairs with

- `openkt-demos` — build the page in the Open Field design language first,
  then make it living.
- `openkt` — your team's memory layer; decisions made in the margins can be
  remembered.
