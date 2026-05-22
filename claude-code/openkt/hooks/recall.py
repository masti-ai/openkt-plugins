#!/usr/bin/env python3
"""UserPromptSubmit hook — push-based memory recall over MCP.

On every user message we inject TWO context blocks into the agent's
prompt:

  1. Semantic recall — top-K memories matching the user's prompt
     (the existing behavior; calls kt_recall via the streamable-HTTP
     MCP endpoint).

  2. Standing project context — top decisions + anti-patterns for
     the project regardless of the prompt. Sourced from a cache
     file that `kt prime` writes at session-start (categorized
     payload from /v1/prime). Zero extra per-prompt API cost; the
     cache is refreshed on the next prime + has a 4h TTL so long
     sessions don't pin stale decisions forever.

The two blocks together give the agent both prompt-relevant memories
AND the standing knowledge it needs to make informed decisions on
EVERY turn — which fixes the "open knowledge transfer" gap where
semantic recall can miss high-importance standing facts that don't
happen to lexically match the current prompt.

Fails open — a Mind outage or missing cache degrades to "no memory
injected" rather than blocking the prompt.
"""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent))
from _mcp_client import call_tool, find_project_id, log_path

LOG = log_path("recall-hook.log")
MIN_PROMPT_LEN = 15
RECALL_LIMIT = 5
RECALL_TIMEOUT_S = 5.0

# Standing-context pinning — read from kt prime's cache. The cache
# is written when categorized memories are returned by /v1/prime
# (server PR #17 / 2026-05-15+). When the cache is absent or stale,
# this block is silently skipped — the recall hook still injects
# semantic results so the agent never gets an empty enrichment.
STANDING_CACHE_TTL = timedelta(hours=4)
STANDING_DECISIONS = 2  # top-N decisions pinned per prompt
STANDING_ANTI_PATTERNS = 2  # top-N anti-patterns pinned per prompt


def _log(msg: str) -> None:
    try:
        with open(LOG, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _standing_cache_path(project_id: str) -> Path:
    """Mirror of cmd/openkt/prime.go:standingCachePath(). Both must
    agree byte-for-byte or the hook reads from the wrong location.
    Honors OPENKT_HOME for test isolation; otherwise rooted at
    ~/.openkt/cache.
    """
    base = os.environ.get("OPENKT_HOME") or str(Path.home() / ".openkt")
    return Path(base) / "cache" / f"standing-{project_id}.json"


def _read_standing(project_id: str) -> dict[str, list[dict]] | None:
    """Read the standing-context cache for this project, or return
    None if the file is missing / unreadable / older than the TTL.

    The TTL gate is the safety against pinning yesterday's decisions
    to today's session — agents change project state, and a stale
    cache should fall back to "no standing block" rather than feed
    outdated context that contradicts current reality.
    """
    path = _standing_cache_path(project_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return None
    fetched_at = payload.get("fetched_at")
    if not fetched_at:
        return None
    try:
        # tolerate Z-suffix and offset formats
        ts = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
    except Exception:
        return None
    if datetime.now(timezone.utc) - ts > STANDING_CACHE_TTL:
        return None
    cat = payload.get("categorized")
    if not isinstance(cat, dict):
        return None
    return cat


def _format_standing_block(categorized: dict[str, list[dict]]) -> str:
    """Render decisions + anti-patterns as a "Standing project context"
    additional-context block. Returns empty string if both buckets
    are empty (which causes the caller to skip the block entirely).
    """
    decisions = categorized.get("decision") or []
    anti = categorized.get("anti-pattern") or []
    if not decisions and not anti:
        return ""

    def _line(mem: dict) -> str:
        content = (mem.get("content") or "").replace("\n", " ").strip()[:240]
        importance = mem.get("importance", 0.5)
        marker = "★" if (isinstance(importance, (int, float)) and importance >= 0.7) else "·"
        return f"  {marker} {content}"

    lines = ["", "Standing project context (pinned every prompt):"]
    if decisions:
        lines.append("Key decisions:")
        for mem in decisions[:STANDING_DECISIONS]:
            lines.append(_line(mem))
    if anti:
        lines.append("Anti-patterns to avoid:")
        for mem in anti[:STANDING_ANTI_PATTERNS]:
            lines.append(_line(mem))
    lines.append("")
    return "\n".join(lines)


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
    if len(prompt) < MIN_PROMPT_LEN:
        sys.exit(0)

    # Scope the recall to the current project. Without project_id the
    # server returns no memories (correct — recall should never leak
    # across projects). If the user isn't inside a `kt init`-ed repo,
    # there's nothing project-scoped to recall, so exit clean.
    project_id = find_project_id()
    if not project_id:
        sys.exit(0)

    # Recall tuning — defaults bias toward semantic match because the
    # raw user prompt is noisy (system reminders, mail blocks, multi-
    # paragraph context). Surface keyword wins (e.g. "overkill") were
    # dominating results in v0.1.16 with the server defaults
    # (workspace=0.4, vector=0.6, rerank=false). Tightened here:
    #   - vector_weight bumped to 0.85, workspace_weight implicit 0.15:
    #     semantic embedding now dominates surface-token match.
    #   - rerank=true: server runs an LLM re-rank pass over the top-K
    #     hybrid hits so the final ordering reflects intent, not just
    #     similarity score.
    #   - min_confidence=0.6: filters memories the server itself isn't
    #     confident in (saves noise; matches the bench threshold
    #     openkt-server is benchmarking against).
    # These are CLI-side knobs; the eventual right config lives in
    # api/docs/recall-bench.md once the server team runs their sweep.
    args = {
        "query": prompt,
        "limit": RECALL_LIMIT,
        "project_id": project_id,
        "vector_weight": 0.85,
        "rerank": True,
        "min_confidence": 0.6,
    }
    # Standing-context block FIRST — read kt prime's cache. This is
    # independent of the semantic recall API call; the agent should
    # see standing decisions + anti-patterns even when the MCP recall
    # fails (no token, network down, server error). Pinning this
    # block to the prompt is the load-bearing piece of "open knowledge
    # transfer": high-importance facts the agent should never lose
    # mid-session, no matter what the network state is.
    standing = _read_standing(project_id) or {}
    standing_block = _format_standing_block(standing)

    # Tool name is kt_recall (openkt-server renamed from memory_recall;
    # CLI versions ≤v0.1.15 still called the old name and silently
    # 404'd every recall, which is why no memories were getting injected
    # despite hooks being wired correctly).
    result = call_tool("kt_recall", args, timeout=RECALL_TIMEOUT_S)
    if "_error" in result:
        _log(f"recall failed: {result['_error']}")
        # Recall API down — still emit the standing block (if any)
        # so the agent retains pinned context. Without this, every
        # offline / unauthed prompt would lose ALL context, even the
        # parts that don't require an API call.
        if standing_block:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": standing_block,
                }
            }))
        sys.exit(0)

    # MCP returns tool result.content[0].text; recall service returns
    # the {data: [...], meta: {...}} envelope as JSON inside that text.
    text = result.get("text", "")
    try:
        payload = json.loads(text) if text else {}
    except Exception:
        _log(f"recall PARSE FAIL for: {prompt[:60]!r}")
        if standing_block:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": standing_block,
                }
            }))
        sys.exit(0)
    memories = payload.get("data") or []

    # Filter superseded / archived BEFORE deciding whether to inject.
    # An all-archived response is functionally the same as no results.
    visible = [m for m in memories if not (m.get("superseded_by") or m.get("archived"))][:RECALL_LIMIT]

    # Always log every recall — success counts as well as failures — so
    # `tail -f ~/.openkt/logs/recall-hook.log` gives the user a live
    # view of "is the loop actually working." Previously this hook only
    # logged on errors; silent success meant zero way to confirm activity.
    _log(f"recall OK ({len(visible)} memories) for: {prompt[:60]!r}")

    if not visible:
        # No semantic matches — still emit the standing block (if any)
        # plus a one-line marker so the user sees the hook fired.
        empty_marker = f"\n[OpenKT auto-recall · 0 memories for {prompt[:40]!r}]\n"
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": empty_marker + standing_block,
            }
        }))
        return

    # Header line includes the count + a query echo so both the agent
    # AND the user (skimming the prompt) can see at a glance that the
    # hook fired and how much context it pulled in. This is the
    # observability surface that lets users confirm OpenKT is working.
    header = f"[OpenKT auto-recall · {len(visible)} memories for {prompt[:40]!r}]"
    lines = ["", header, "Relevant memories from prior project context (auto-recalled):"]
    for m in visible:
        content = (m.get("content") or "").replace("\n", " ").strip()[:240]
        kind = m.get("kind") or "context"
        when = (m.get("created_at") or "")[:10]
        importance = m.get("importance", 0.5)
        marker = "★" if importance > 0.7 else "·"
        lines.append(f"  {marker} {content} ({kind}{' · ' + when if when else ''})")
    lines.append("")
    context = "\n".join(lines) + standing_block

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }))


if __name__ == "__main__":
    main()
