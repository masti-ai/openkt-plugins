#!/usr/bin/env python3
"""PostToolUse hook — sync native-memory writes upstream (fire-and-forget).

Fires after Write / Edit / MultiEdit. If the path matches Claude Code's
native auto-memory dir (~/.claude/projects/<slug>/memory/*.md or the
legacy .claude-accounts/<account>/... layout), parses YAML frontmatter
+ body and pushes via memory_remember.

Async by design: the agent doesn't observe this hook's result — it's
purely a server-side sync. PostToolUse blocks the next action until the
hook returns, and a synchronous MCP call adds ~1.5s per write. We do
all the local work (parse, find project) up front, then spawn the
actual MCP call in a detached background process and exit in <50ms.
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _mcp_client import find_project_id, log_path

LOG = log_path("sync-hook.log")
# Match Claude Code's native auto-memory file paths. Supports BOTH
# layouts we've seen in the wild:
#   /.claude/projects/<slug>/memory/<file>.md          (current)
#   /.claude-accounts/<acct>/projects/<slug>/memory/<file>.md  (legacy)
# Index file MEMORY.md is intentionally NOT a memory itself — caller
# excludes it by basename below.
NATIVE_MEMORY_PATH_RE = re.compile(
    r"/\.claude(?:-accounts/[^/]+)?/projects/[^/]+/memory/[^/]+\.md$"
)


def _log(msg: str) -> None:
    try:
        with open(LOG, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def parse_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end < 0:
        return {}, content
    fm = content[3:end].strip()
    body = content[end + 4:].lstrip("\n")
    meta: dict = {}
    for line in fm.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body


def map_kind(native_type: str) -> str:
    table = {
        "feedback": "anti-pattern",
        "project": "decision",
        "reference": "context",
        "user": "context",
    }
    return table.get((native_type or "").lower(), "context")


def main() -> None:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    tool_name = event.get("tool_name") or event.get("tool") or ""
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        sys.exit(0)

    file_path = (
        event.get("tool_input", {}).get("file_path")
        or event.get("input", {}).get("file_path")
        or ""
    )
    if not file_path or not NATIVE_MEMORY_PATH_RE.search(file_path):
        sys.exit(0)
    if Path(file_path).name == "MEMORY.md":
        sys.exit(0)

    try:
        content = Path(file_path).read_text()
    except Exception:
        sys.exit(0)

    meta, body = parse_frontmatter(content)
    if not body.strip():
        sys.exit(0)

    name = meta.get("name") or Path(file_path).stem
    kind = map_kind(meta.get("type", ""))
    payload_content = f"{name}\n\n{body}".strip()

    # Scope the write to the current project. Memories without project
    # scope land in an unaddressable default bucket — `kt recall` from
    # the same dir wouldn't find them later. If the user isn't inside a
    # `kt init`-ed repo, skip — there's nothing to scope the write to.
    project_id = find_project_id()
    if not project_id:
        _log(f"sync SKIP (no project bound): {name!r}")
        sys.exit(0)

    # Build the kt_save_memory call args. Two contract details that
    # tripped earlier CLI versions:
    #   - the server-side tool is `kt_save_memory` (renamed from
    #     memory_remember). _sync_worker.py uses the new name.
    #   - the array field is `tag_slugs` (not `tags`), and each entry
    #     must match ^[a-z0-9][a-z0-9-]*[a-z0-9]$ (lowercase-kebab,
    #     2-40 chars). The native-memory `type` field gives us "feedback",
    #     "project", "reference", "user", "context" etc — all valid slugs.
    raw_type = (meta.get("type", "") or "").strip().lower()
    tag_slugs = [raw_type] if (len(raw_type) >= 2 and raw_type.replace("-", "a").isalnum()) else []
    args = {
        "content": payload_content,
        "kind": kind,
        "tag_slugs": tag_slugs,
        "project_id": project_id,
    }

    # Fire-and-forget: spawn a detached child that does the actual MCP
    # POST. Returning immediately unblocks Claude Code's PostToolUse
    # loop — saves ~1.5s per write on the hot path.
    worker = Path(__file__).parent / "_sync_worker.py"
    payload = json.dumps({"args": args, "name": name})
    try:
        subprocess.Popen(
            [sys.executable, str(worker)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # detach from this process group
            close_fds=True,
        ).stdin.write(payload.encode())
        _log(f"sync QUEUED: {name!r}")
    except Exception as e:
        _log(f"sync SPAWN FAIL: {name!r} — {e!r}")


if __name__ == "__main__":
    main()
