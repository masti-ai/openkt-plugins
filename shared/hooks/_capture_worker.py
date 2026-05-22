#!/usr/bin/env python3
"""Detached worker for capture.py's CAPTURE pipeline.

Spawned by capture.py via subprocess.Popen(start_new_session=True) so
it survives the parent hook's exit. Reads a single JSON payload from
stdin describing the candidate capture, runs the Stage-2 → Stage-1
fallback chain, and logs the outcome to ~/.openkt/logs/capture-hook.log.

PRIMARY PATH — Stage 2:
  POST <api_base>/v1/capture { prompt, project_id }
  The server runs an LLM classifier + extractor. If the LLM decides
  the prompt is saveable, the server itself writes the memory and
  returns {saved: true, memory_id, ...}. Otherwise saved=false with
  a reason — we just log and move on.

FALLBACK PATH — Stage 1:
  If /v1/capture returns 404 (endpoint not deployed yet) OR the
  network fails entirely, fall back to a direct kt_save_memory call
  via _mcp_client.call_tool, using the Stage-1 heuristic kind_hint
  the parent classifier already produced. Lower quality (no LLM
  filter) but matches what CLI v0.1.18 was doing — never worse
  than the prior state during the rollout window.

Auth: reads the bearer from ~/.openkt/token; the same auto-refresh
path _mcp_client uses applies to the fallback save.
"""
from __future__ import annotations
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _mcp_client import call_tool, log_path

LOG = log_path("capture-hook.log")
TOKEN_FILE = Path(os.path.expanduser("~/.openkt/token"))


def _log(msg: str) -> None:
    try:
        with open(LOG, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _load_token() -> str:
    if not TOKEN_FILE.exists():
        return ""
    try:
        return TOKEN_FILE.read_text().strip()
    except Exception:
        return ""


def _stage2_capture(prompt: str, project_id: str, api_base: str, token: str) -> dict | None:
    """Try the Stage-2 server-side classification.

    Returns the parsed JSON response on success, or None if the server
    path is unavailable (404 / network / auth) — caller falls back to
    Stage 1. Returns an "error" dict for other server-side failures
    (5xx, malformed response) so we don't silently retry a broken
    endpoint forever.
    """
    body = json.dumps({"prompt": prompt, "project_id": project_id}).encode()
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}/v1/capture",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20.0) as r:
            raw = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Endpoint not deployed yet — caller falls back to Stage 1.
            return None
        # Read the error body for the log; non-fatal.
        try:
            err = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            err = ""
        return {"_error": f"HTTP {e.code}: {err}"}
    except (urllib.error.URLError, TimeoutError, OSError):
        # Network unreachable / DNS / timeout — fall back to Stage 1
        # rather than dropping the candidate capture entirely.
        return None
    try:
        env = json.loads(raw)
    except Exception:
        return {"_error": f"non-JSON response: {raw[:200]}"}
    # OpenKT REST envelope: {data, error, meta}. We want data.
    if env.get("error"):
        return {"_error": json.dumps(env["error"])[:300]}
    return env.get("data") or {}


def _stage1_fallback(prompt: str, kind: str, project_id: str) -> dict:
    """Direct kt_save_memory call — the v0.1.18 path.

    Used when the Stage-2 endpoint is unavailable. No LLM filter, so
    every match writes (subject to the regex gate + rate-limit the
    parent already applied).
    """
    args = {
        "content": prompt,
        "kind": kind,
        "project_id": project_id,
        "tag_slugs": ["captured-from-prompt", "stage1-fallback"],
    }
    result = call_tool("kt_save_memory", args, timeout=15.0)
    if "_error" in result:
        return {"saved": False, "reason": f"stage1 save failed: {result['_error']}"}
    text = result.get("text") or ""
    try:
        inner = json.loads(text)
        return {"saved": True, "memory_id": inner.get("id"), "reason": "stage1 fallback"}
    except Exception:
        return {"saved": True, "reason": "stage1 fallback (no id parsed)"}


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except Exception as e:
        _log(f"capture WORKER parse fail: {e!r}")
        return

    prompt = payload.get("prompt") or ""
    kind_hint = payload.get("kind_hint") or "context"
    project_id = payload.get("project_id") or ""
    api_base = payload.get("api_base") or "https://api.openkt.ai"

    if not prompt or not project_id:
        _log(f"capture WORKER missing args: prompt={bool(prompt)} project_id={bool(project_id)}")
        return

    token = _load_token()
    if not token:
        _log("capture WORKER no token — run `kt login`")
        return

    # Stage 2: server-side LLM classification.
    s2 = _stage2_capture(prompt, project_id, api_base, token)

    if s2 is None:
        # Endpoint not deployed or unreachable — fall through to Stage 1.
        result = _stage1_fallback(prompt, kind_hint, project_id)
        if result.get("saved"):
            _log(f"capture SAVED (stage1 fallback): kind={kind_hint} id={result.get('memory_id','?')[:8]} for: {prompt[:60]!r}")
        else:
            _log(f"capture FAIL (stage1 fallback): {result.get('reason','?')} for: {prompt[:60]!r}")
        return

    if "_error" in s2:
        _log(f"capture FAIL (stage2 error): {s2['_error']} for: {prompt[:60]!r}")
        return

    # Stage 2 returned a verdict. Log either outcome.
    if s2.get("saved"):
        memory_id = (s2.get("memory_id") or "?")[:8]
        kind = s2.get("kind", "?")
        conf = s2.get("confidence", "?")
        _log(f"capture SAVED (stage2): kind={kind} conf={conf} id={memory_id} for: {prompt[:60]!r}")
    else:
        reason = s2.get("reason", "saveable=false")[:120]
        _log(f"capture SKIP (stage2 verdict): {reason} for: {prompt[:60]!r}")


if __name__ == "__main__":
    main()
