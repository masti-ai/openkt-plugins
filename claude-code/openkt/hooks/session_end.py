#!/usr/bin/env python3
"""SessionEnd hook — final consolidation.

Stub: log the event and exit 0. v1.1 will run an LLM extraction over
the session transcript to distill durable memories the agent missed.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _mcp_client import log_path

LOG = log_path("sessionend-hook.log")


def main() -> None:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        event = {}
    try:
        with open(LOG, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] sessionend: keys={list(event.keys())}\n")
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
