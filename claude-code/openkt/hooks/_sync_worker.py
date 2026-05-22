#!/usr/bin/env python3
"""Detached worker for sync_native_memory's async write path.

Spawned by sync_native_memory.py via subprocess.Popen(start_new_session=True)
so it survives the parent hook's exit. Reads a single JSON payload from
stdin describing the memory_remember args, makes the MCP call, logs the
outcome to ~/.openkt/logs/sync-hook.log, then exits.

Lives in a separate file (not inline in sync_native_memory.py) so the
parent hook can exec us directly without re-importing the parent's
state. Keeps the parent's "fire and forget" surface small + fast.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _mcp_client import call_tool, log_path

LOG = log_path("sync-hook.log")


def _log(msg: str) -> None:
    try:
        with open(LOG, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except Exception as e:
        _log(f"sync WORKER PARSE FAIL: {e!r}")
        return

    name = payload.get("name", "<unknown>")
    args = payload.get("args") or {}
    if not args:
        _log(f"sync WORKER NO ARGS: {name!r}")
        return

    # Tool name is kt_save_memory (openkt-server renamed from
    # memory_remember; same root-cause as the kt_recall rename — every
    # native-memory sync was silently 404ing on the old name).
    result = call_tool("kt_save_memory", args, timeout=15.0)
    if "_error" in result:
        _log(f"sync FAIL (async): {name!r} — {result['_error']}")
        return
    # Extract the created memory id from the MCP response if present.
    mem_id = "?"
    text = result.get("text") or ""
    try:
        inner = json.loads(text)
        mem_id = (inner.get("data") or {}).get("id", mem_id)
    except Exception:
        pass
    _log(f"sync OK (async): {name!r} → {mem_id[:8]}")


if __name__ == "__main__":
    main()
