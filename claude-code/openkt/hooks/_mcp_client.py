"""Minimal MCP streamable-http client for use from Claude Code hooks.

Stateless: a single tools/call POST per invocation. The OpenKT server
runs the MCP transport with sessionIdGenerator=undefined, so there is no
session handshake and no Mcp-Session-Id header to carry — every request
stands alone. Failures return {"_error": "<msg>"} — caller is expected
to fail open.

Auto-refresh: on a 401 from the MCP endpoint, we attempt a one-shot
refresh against the REST API's POST /v1/auth/refresh using the
refresh_token persisted by `kt login` in ~/.openkt/config.json. On
success we rewrite ~/.openkt/token + config.json so the rotation
sticks for every subsequent hook fire AND for `kt` CLI invocations. The
MCP call is then retried once with the new bearer. If refresh fails the
caller receives the original 401 with a helpful "_error" message.
"""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

# Canonical MCP URL is `https://api.openkt.ai/mcp` — co-located on the
# same Nest backend as the REST API. The MCP route is excluded from the
# `/v1` global prefix in openkt-server's main.ts (setGlobalPrefix
# excludes { path: "mcp", method: RequestMethod.ALL }) because MCP is
# versioned by @modelcontextprotocol/sdk, not by our REST API.
#
# The earlier `mcp.openkt.ai` hostname pointed at the same ALB but was
# retired during the 2026-05-15 consolidation. Pointing recall +
# kt_save_memory hooks there now hits 404s, which manifests as silently
# dead memory sync — the user gets ZERO captures despite hooks firing.
DEFAULT_MCP_URL = "https://api.openkt.ai/mcp"
DEFAULT_API_URL = "https://api.openkt.ai"
TOKEN_FILE = Path(os.path.expanduser("~/.openkt/token"))
CONFIG_FILE = Path(os.path.expanduser("~/.openkt/config.json"))
CLAUDE_JSON = Path(os.path.expanduser("~/.claude.json"))
LOG_DIR = Path(os.path.expanduser("~/.openkt/logs"))
DEFAULT_TIMEOUT = 8.0


def log_path(name: str) -> str:
    """Return a per-hook log file under ~/.openkt/logs/. Creates the dir
    with mode 0700 if missing — keeps hook logs off /tmp where they'd be
    world-readable on multi-user systems.
    """
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    except Exception:
        pass
    return str(LOG_DIR / name)


def find_project_id() -> str | None:
    """Walk up from cwd looking for .openkt/manifest.json. Returns the
    project_id field, or None if no manifest is found before $HOME.

    The hook subprocess inherits cwd from Claude Code, which mirrors the
    user's working directory in their session. If they're inside a
    `kt init`-ed repo, this finds the binding and we can scope MCP
    tool calls to that project. Without scope, memory_recall returns
    nothing (the server requires project_id to avoid cross-tenant
    leakage); memory_remember would write to a default scope that the
    user can't easily query later. Both bad — hence this helper.
    """
    home = os.path.realpath(os.path.expanduser("~"))
    try:
        cwd = os.path.realpath(os.getcwd())
    except Exception:
        return None
    while True:
        manifest_path = os.path.join(cwd, ".openkt", "manifest.json")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path) as f:
                    return json.load(f).get("project_id")
            except Exception:
                return None
        # Stop at $HOME (a manifest there would shadow every other
        # project's parent-walk) or at the filesystem root.
        if cwd == home or os.path.dirname(cwd) == cwd:
            return None
        cwd = os.path.dirname(cwd)


def _load_auth() -> tuple[str, str]:
    token = (os.environ.get("OPENKT_TOKEN") or "").strip()
    if not token and TOKEN_FILE.exists():
        try:
            token = TOKEN_FILE.read_text().strip()
        except Exception:
            token = ""
    if not token:
        raise RuntimeError("no OPENKT_TOKEN in env or ~/.openkt/token (run `kt login`)")
    url = os.environ.get("OPENKT_MCP_URL") or DEFAULT_MCP_URL
    return token, url


def _load_refresh_token() -> str:
    """Read refresh_token from ~/.openkt/config.json. Empty string if
    no config, or no refresh_token field — caller decides what to do.
    """
    if not CONFIG_FILE.exists():
        return ""
    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f) or {}
    except Exception:
        return ""
    return (cfg.get("refresh_token") or "").strip()


def _api_base() -> str:
    return (os.environ.get("OPENKT_API_BASE") or DEFAULT_API_URL).rstrip("/")


def _refresh_session() -> str:
    """Exchange the persisted refresh_token for a new access token.

    On success: write new access token to ~/.openkt/token, rotate
    refresh_token in ~/.openkt/config.json, also rewrite the literal
    bearer baked into ~/.claude.json's openkt MCP entry so Claude Code's
    own MCP client picks up the new credential the next time it spawns
    a tool call. Returns the new access token.

    On failure: raises with a message the caller surfaces as _error.
    """
    refresh = _load_refresh_token()
    if not refresh:
        raise RuntimeError("no refresh_token saved — run `kt login`")
    body = json.dumps({"refresh_token": refresh}).encode()
    req = urllib.request.Request(
        f"{_api_base()}/v1/auth/refresh",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10.0) as r:
        raw = r.read().decode("utf-8", errors="replace")
    payload = json.loads(raw) if raw.strip() else {}
    data = payload.get("data") if isinstance(payload, dict) else None
    if not data or not isinstance(data, dict):
        raise RuntimeError(f"refresh returned no data: {raw[:200]!r}")
    new_token = (data.get("token") or "").strip()
    new_refresh = (data.get("refresh_token") or "").strip()
    expires_at = data.get("expires_at")
    if not new_token:
        raise RuntimeError("refresh response missing token")

    # Persist. Token first (the file the rest of the system reads every
    # invocation), then config.json.
    try:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        TOKEN_FILE.write_text(new_token)
        os.chmod(TOKEN_FILE, 0o600)
    except Exception as e:
        # Best-effort — if we can't write, the next process will refresh
        # again on its own 401. Not fatal to the current call.
        pass

    try:
        cfg: dict = {}
        if CONFIG_FILE.exists():
            try:
                cfg = json.loads(CONFIG_FILE.read_text() or "{}") or {}
            except Exception:
                cfg = {}
        if new_refresh:
            cfg["refresh_token"] = new_refresh
        if isinstance(expires_at, (int, float)) and expires_at > 0:
            cfg["expires_at"] = int(expires_at)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2) + "\n")
        os.chmod(CONFIG_FILE, 0o600)
    except Exception:
        pass

    # Best-effort: rotate the literal bearer in ~/.claude.json so Claude
    # Code's own MCP client (NOT this hook — different code path) picks
    # up the new credential. Without this, the agent's direct calls to
    # memory_remember / memory_recall will keep 401-ing even though our
    # hooks now work fine.
    _rotate_claude_json_bearer(new_token)

    return new_token


def _rotate_claude_json_bearer(new_token: str) -> None:
    """Update the Authorization header on the openkt MCP entry in
    ~/.claude.json. Skips silently if the file or the entry doesn't
    exist — we never want hook flow to die because Claude Code config
    moved or the user uses a different harness.
    """
    if not CLAUDE_JSON.exists():
        return
    try:
        with open(CLAUDE_JSON) as f:
            cfg = json.load(f) or {}
    except Exception:
        return
    servers = cfg.get("mcpServers") or {}
    entry = servers.get("openkt") or {}
    headers = entry.get("headers") or {}
    if "Authorization" not in headers:
        return
    headers["Authorization"] = f"Bearer {new_token}"
    entry["headers"] = headers
    servers["openkt"] = entry
    cfg["mcpServers"] = servers
    try:
        tmp = CLAUDE_JSON.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(cfg, indent=2))
        os.replace(tmp, CLAUDE_JSON)
    except Exception:
        pass


def _post(url: str, body: dict, headers: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **headers,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
    # The server returns text/event-stream framing ('event: message\ndata: {...}')
    # even for one-shot calls. Walk lines for the first 'data: ' payload; if no
    # SSE framing is present, fall back to treating the body as plain JSON.
    for line in raw.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return json.loads(raw) if raw.strip() else {}


def _is_unauthorized(exc: Exception) -> bool:
    """True if the exception is an HTTP 401. Covers urllib.error.HTTPError
    directly and the wrapper Exception messages we sometimes see in the
    SSE-framing failure path.
    """
    if isinstance(exc, urllib.error.HTTPError) and exc.code == 401:
        return True
    msg = str(exc)
    return "401" in msg and "Unauthorized" in msg


def call_tool(tool_name: str, arguments: dict, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """One-shot MCP tool call. Returns {"text": "...", "raw": ...} or
    {"_error": "..."}. Never raises.

    On 401: attempt a one-shot refresh + retry. Refresh failure surfaces
    as _error so the caller (recall.py / sync hook) can fail open
    cleanly — the user keeps working; only memory sync is degraded.
    """
    try:
        token, url = _load_auth()
    except Exception as e:
        return {"_error": f"auth load failed: {e!r}"}

    def _do(bearer: str) -> dict:
        return _post(
            url,
            {
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
            {"Authorization": f"Bearer {bearer}"},
            timeout,
        )

    try:
        resp = _do(token)
    except Exception as e:
        if _is_unauthorized(e):
            try:
                new_token = _refresh_session()
            except Exception as re:
                return {"_error": f"tool call failed (401) and refresh failed: {re!r} (run `kt login`)"}
            try:
                resp = _do(new_token)
            except Exception as e2:
                return {"_error": f"tool call failed after refresh: {e2!r}"}
        else:
            return {"_error": f"tool call failed: {e!r}"}

    if "error" in resp:
        return {"_error": str(resp["error"])}

    content = resp.get("result", {}).get("content", [])
    text = "\n".join(b.get("text", "") for b in content if b.get("type") == "text")
    return {"text": text, "raw": resp.get("result")}
