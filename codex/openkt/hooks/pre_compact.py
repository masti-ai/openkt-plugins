#!/usr/bin/env python3
"""PreCompact hook — checkpoint working state before Claude Code compacts.

Stub: log the event and exit 0. v1.1 will pull the conversation
transcript, summarize, and save as kind=context.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _mcp_client import log_path

LOG = log_path("precompact-hook.log")


def main() -> None:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        event = {}
    try:
        with open(LOG, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] precompact: keys={list(event.keys())}\n")
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
