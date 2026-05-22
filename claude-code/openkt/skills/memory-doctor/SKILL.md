---
name: memory-doctor
description: Diagnose OpenKT installation, auth, and project-binding issues when the user reports "memories aren't sticking" or "the hooks don't seem to fire". Run `kt doctor` and interpret the results.
---

# OpenKT install / auth doctor

When something feels off — `kt remember` runs but the memory doesn't
show up in next session, the auto-recall block is empty when you
expected hits, you see "Tool not found" errors — there's a fixed
diagnostic sequence to walk through.

## Step 1: Run kt doctor

```
kt doctor --json
```

Returns a structured report with:
  - `checks[]`: pass/fail entries for auth token, /me, dashboard
    reachable, MCP reachable, harnesses installed, project binding,
    MCP contract
  - `harnesses[]`: every harness (claude_code, cursor, codex, opencode)
    with the signals we probed (binary in PATH, config dir, macOS app)
    and the verdict
  - `passed` / `failed` counts

## Step 2: Interpret common failures

- **"no token at ~/.openkt/token"** → user must run `kt login`
- **"HTTP 401 from /me"** → token expired, refresh failed →
  `kt login` (the user's been signed out)
- **"harnesses installed: none"** → wiring never ran. The user's hooks
  won't fire. Fix with `kt install --for=claude_code` (or whichever
  harness they use)
- **"server is missing required tools: kt_*"** → backend contract
  drift. The user's CLI version expects MCP tool names the deployed
  server doesn't expose. `kt update` and retry
- **"manifest at ... references missing project"** → user moved or
  the project was deleted upstream. Walk them through
  `kt init` in the repo (delete `.openkt/manifest.json` first)

## Step 3: Harness detection signals

For each harness, doctor shows ALL probed signals. Examples:

```
cursor:
  config dir ~/.cursor: ✓ /home/user/.cursor
  binary `cursor` in PATH: ✗ not found
  macOS app bundle: ✗ /Applications/Cursor.app not present
  → detected (config dir is enough)
```

Detection is permissive — ANY positive signal flips "detected". If a
harness shows "not detected" but the user insists it's installed, they
can force-wire it via:

```
kt install --for=<harness>
```

This bypasses the detection gate entirely.

## Step 4: Fall back to manual reset

If doctor passes but memories still aren't working, the nuclear option:

```
kt logout && kt login
```

This:
  - Re-fetches a fresh token (and refresh token)
  - Re-runs all harness wiring
  - Re-installs hooks
  - Re-registers MCP servers

After this, the user opens a new session — old sessions hold the stale
MCP connection until they restart.
