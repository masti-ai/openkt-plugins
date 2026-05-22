#!/usr/bin/env python3
"""UserPromptSubmit hook — CAPTURE the user's transferred context.

OpenKT's product thesis: every user prompt is both a request AND a
context transfer. The recall hook (recall.py) already handles the
inbound side — pulls relevant memories into the prompt. CAPTURE is
the OUTBOUND side: when the user states a preference, decision,
correction, or domain fact in their prompt, save it as a memory so
the NEXT session inherits it.

Why this matters: agents don't reliably call memory_remember even
when primed. The user is a far better signal source than the agent's
self-direction. If we just listen to what the user says explicitly,
we get the highest-signal memories with zero ceremony.

Architecture: two-stage classifier.

  Stage 1 — heuristic gate (regex, microseconds, free).
    Match prompts that contain imperative/declarative patterns:
      - "I want…" / "I prefer…" / "I need…" → preference
      - "use X (for Y)" / "don't use X" → preference
      - "always W" / "never Z" → rule
      - "X is Y" / "the way Y works is…" → fact
      - "no, actually…" / "wait, that's wrong" → correction
    Below ~80% of prompts fail this gate and skip immediately.

  Stage 2 — light LLM classify+extract (~$0.001 per call).
    For prompts that pass the gate, POST /v1/capture to openkt-server.
    Server runs a small LLM that decides 'is this a saveable
    memory?' and if yes, returns the structured statement.

This v1 ships Stage 1 only. Stage 2 lights up automatically once the
server's /v1/capture endpoint is live (server-track bd issue) —
without re-shipping the CLI. Stage 1 is intentionally conservative:
it catches obvious patterns and skips ambiguous prompts.

Rate-limited: at most one save per ~30 seconds per user. Prevents a
brainstorming session from flooding the project with 50 partial
memories.

Fail-open: any error here exits 0; recall is the load-bearing path,
capture is bonus. The UserPromptSubmit event continues normally.
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _mcp_client import find_project_id, log_path

LOG = log_path("capture-hook.log")
STATE_FILE = Path(os.path.expanduser("~/.openkt/.capture-state.json"))
TOKEN_FILE = Path(os.path.expanduser("~/.openkt/token"))
RATE_LIMIT_SECONDS = 30
MIN_PROMPT_LEN = 25
MAX_PROMPT_LEN = 4000
CAPTURE_TIMEOUT_S = 20.0  # LLM classification can take a while
DEFAULT_API_BASE = "https://api.openkt.ai"

# ─── Heuristic patterns ─────────────────────────────────────────────
# Each (pattern, kind) tuple. Patterns are compiled once at module load.
# Kinds match openkt-server's MemoryKind enum: decision, pattern,
# anti-pattern, context, incident, skill, debug-recipe, environment,
# note, fact, other.
#
# Ordering matters: more specific patterns first so we attribute the
# right kind.

_CAPTURE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Anti-patterns ("don't…", "never…", "avoid…")
    (re.compile(r"\b(don'?t|do not)\s+(?:do|use|call|run|use|allow|let|build|ship|create)\b", re.I), "anti-pattern"),
    (re.compile(r"\b(never|avoid|stop)\s+\w+", re.I), "anti-pattern"),

    # Decisions ("use X (for Y) instead of Z", "prefer X over Y", "we chose X because")
    (re.compile(r"\b(use|prefer|pick|chose|going with)\s+\w+\s+(over|instead of|not|for)\s+\w+", re.I), "decision"),
    (re.compile(r"\bwe (?:chose|decided|went with)\b", re.I), "decision"),

    # Rules ("always W", "every X must Y", "X should Y")
    (re.compile(r"\balways\s+(?:use|run|do|call|prefer|check|deploy|test|wire)\b", re.I), "pattern"),
    (re.compile(r"\b(?:every|all)\s+\w+\s+(?:must|should|need to)\b", re.I), "pattern"),

    # Domain facts / configuration ("X is at Y", "the Y is X", "deploys to X", "lives at X")
    (re.compile(r"\b(?:lives|deploys|runs|listens|is hosted)\s+(?:at|on|in)\b", re.I), "environment"),
    (re.compile(r"\b(?:api|dashboard|landing|mcp|backend|server)\.[\w.-]+\.[a-z]{2,}", re.I), "environment"),

    # Declarative location/system statements — the natural-language form
    # users actually transfer context in. Examples that prompted the
    # 2026-05-15 widening:
    #   "the design system is at /home/ubuntu/openkt"
    #   "we deploy via CodePipeline"
    #   "the backend code lives in api/apps/server"
    #   "your project_id is fc35693b-4be8-4e08-8a81-d59c05676773"
    #   "the staging DB is on port 5433"
    # Conservative anchors ("the X is at/in/on", "we deploy/use/run via")
    # so we don't catch every "X is Y" sentence — those would be false
    # positives like "this code is wrong" or "the test is failing".
    (re.compile(r"\bthe\s+\w+(?:\s+\w+){0,3}\s+(?:is|lives|sits)\s+(?:at|in|on|under)\s+\S", re.I), "environment"),
    (re.compile(r"\bwe\s+(?:deploy|build|ship|publish|release|run|test)\s+(?:via|through|with|using|on)\b", re.I), "pattern"),
    (re.compile(r"\byour?\s+(?:project_id|org_id|user_id|api_key|token|account)\b", re.I), "context"),

    # Preferences (direct "I want…", "I prefer…", "I'd like…")
    (re.compile(r"\bI\s+(?:want|prefer|need|like|wish|expect)\b", re.I), "context"),

    # Corrections ("no, actually…", "wait, that's wrong", "let me clarify")
    (re.compile(r"\b(?:no(?:,|\s)\s*(?:actually|wait)|that'?s\s+(?:wrong|incorrect)|let me clarify)\b", re.I), "context"),

    # Incidents ("X broke when Y", "X was failing because Y", "we hit X")
    (re.compile(r"\b(?:broke|failed|crashed|died|404'?d|500'?d)\s+(?:when|because|on|while)\b", re.I), "incident"),
]


def _log(msg: str) -> None:
    try:
        with open(LOG, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        STATE_FILE.write_text(json.dumps(state))
        os.chmod(STATE_FILE, 0o600)
    except Exception:
        pass


def _classify(prompt: str) -> str | None:
    """Return the memory kind if the prompt looks worth saving, else None.

    Conservative by design — false-negatives are fine (we don't capture
    a borderline prompt), false-positives are noise. Stage 2 (server-
    side LLM) is what catches the borderline cases later.
    """
    # Drop the prompt if it's mostly noise wrappers (system reminders,
    # mail blocks). These are an artifact of specific harnesses
    # (Gas Town's gc mail plugin); they shouldn't get classified.
    clean = re.sub(r"<system-reminder>.*?</system-reminder>", "", prompt, flags=re.DOTALL)
    clean = re.sub(r"You have \d+ unread message.*?Run.*?\n", "", clean, flags=re.DOTALL)
    clean = clean.strip()

    if len(clean) < MIN_PROMPT_LEN or len(clean) > MAX_PROMPT_LEN:
        return None

    # Try each pattern; first match wins. Stop the moment we have a
    # hit — no point evaluating the remaining patterns.
    for pat, kind in _CAPTURE_PATTERNS:
        if pat.search(clean):
            return kind
    return None


def _check_rate_limit(state: dict) -> bool:
    """True if we're allowed to capture now; False if rate-limited."""
    last = state.get("last_capture_at", 0)
    return (time.time() - last) >= RATE_LIMIT_SECONDS


def main() -> None:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    prompt = (
        event.get("prompt")
        or event.get("user_prompt")
        or event.get("user_message")
        or event.get("user_input", "")
    )
    if not isinstance(prompt, str) or len(prompt) < MIN_PROMPT_LEN:
        sys.exit(0)

    # Scope to the current project. If no project bound, capture is a
    # no-op — there's nowhere to write the memory.
    project_id = find_project_id()
    if not project_id:
        sys.exit(0)

    # Stage 1: heuristic classify.
    kind = _classify(prompt)
    if kind is None:
        # Skip silently — most prompts don't pass the gate, no log noise.
        sys.exit(0)

    # Rate-limit. If we just captured something in the last 30s, skip
    # to avoid flooding the project with mid-brainstorm fragments.
    state = _load_state()
    if not _check_rate_limit(state):
        _log(f"capture SKIP (rate-limit): kind={kind} for: {prompt[:60]!r}")
        sys.exit(0)

    # Spawn a detached capture worker. Two execution paths:
    #   - PRIMARY (Stage 2): POST /v1/capture so the server's LLM
    #     classifier decides saveability + extracts a clean statement.
    #     Better quality, lower noise. Cost ~$0.001 per call.
    #   - FALLBACK (Stage 1): the server endpoint may not be deployed
    #     yet (404), the auth may be broken, the network may be down.
    #     In any of those cases the worker falls through to a direct
    #     kt_save_memory call via _sync_worker — same outcome the CLI
    #     was producing in v0.1.18 (heuristic-only).
    # We bake the prompt + kind + project_id into stdin and let the
    # worker decide which path to take. UserPromptSubmit returns
    # immediately regardless.
    worker = Path(__file__).parent / "_capture_worker.py"
    payload = json.dumps({
        "prompt": prompt[:MAX_PROMPT_LEN].strip(),
        "kind_hint": kind,  # the Stage-1 verdict; useful if we fall back
        "project_id": project_id,
        "api_base": os.environ.get("OPENKT_API_BASE") or DEFAULT_API_BASE,
    })
    try:
        proc = subprocess.Popen(
            [sys.executable, str(worker)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
        if proc.stdin:
            proc.stdin.write(payload.encode())
            proc.stdin.close()
        # Stamp the rate-limit clock AFTER we successfully spawn the
        # worker — otherwise a spawn failure would still burn the
        # cooldown window.
        state["last_capture_at"] = time.time()
        _save_state(state)
        _log(f"capture QUEUED: kind_hint={kind} for: {prompt[:80]!r}")
    except Exception as e:
        _log(f"capture SPAWN FAIL: {e!r}")


if __name__ == "__main__":
    main()
