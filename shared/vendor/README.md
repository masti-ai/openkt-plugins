# shared/vendor

Third-party assets vendored into this repo with a pinned ref, so updates flow
from one place instead of being copied by hand into each consumer.

## openfield

[masti-ai/openfield](https://github.com/masti-ai/openfield) — the Deepwork Labs
× OpenKT design system. One source of truth for tokens, ASCII art, loading
vocabulary, and the application shell across every surface in this repo.

```
openfield/
├── tokens/mix.css       design tokens + base components (source of truth)
├── art/_art.js          generative ASCII art library
├── loading/loading.js   spinners, bars, streaming typer, agent faces
├── app/pg-app.css       application shell — sidebar, cards, tables, drawer
├── app/pg-shell.js      shell injector + Cmd-K palette
├── SKILL.md             rules for agents building in this system
├── llms.txt             machine-readable index
└── README.md            upstream readme
```

The exact upstream commit is pinned in [`openfield.lock`](openfield.lock).
**Never edit files under `openfield/` by hand** — they are overwritten on every
sync. Make changes upstream, then re-pin.

### Updating

```bash
# Reproduce the vendored tree at the pinned commit (e.g. after a fresh clone):
./sync-openfield.sh

# Move the pin to the current tip of the tracked ref and refresh everything:
./sync-openfield.sh --update
```

### Consumers

The sync script propagates the foundation files into each consumer in the same
run, so the vendored copy and the shipped copies never drift. Current mapping:

| Vendored source            | Consumer (shipped copy)                                                     |
|----------------------------|-----------------------------------------------------------------------------|
| `openfield/tokens/mix.css` | `claude-code/openkt-demos/skills/interactive-demo/assets/openkt-pages.css`  |
| `openfield/art/_art.js`    | `claude-code/openkt-demos/skills/interactive-demo/assets/openkt-art.js`     |
| `openfield/loading/loading.js` | `claude-code/openkt-demos/skills/interactive-demo/assets/openkt-loading.js` |

The interactive-demo skill keeps its own asset names (`openkt-*`) because the
skill is a packaged plugin: it bundles its assets so a published demo is
self-contained and never reaches back into `shared/vendor/` at runtime. The sync
is a **build-time** copy — edit upstream, run the script, commit the result.

`openkt-demo.css`, `openkt-demo.js`, and `template.html` in that skill are
demo-specific (tabs / knowledge-graph / report cards) and are **not** part of
openfield; the sync leaves them untouched.

To add a new consumer, append a `src=dst` pair to the `CONSUMERS` array in
`sync-openfield.sh`.
