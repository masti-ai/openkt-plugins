"""Thin HTTP client for the OpenKT API.

Why stdlib-only? Two reasons:
1. Hermes pins ``httpx==0.28.1`` exactly. Pulling httpx as a hard dep
   here would either match that pin (forcing future Hermes bumps to
   coordinate with this package) or conflict with it. urllib has none
   of that baggage.
2. The hot path is a handful of POSTs — connection pooling doesn't
   help us. Keepalive within a single Hermes turn isn't a thing
   because daemon threads tear down between turns.

Dual transport: PATs (``okt_pat_...``) go through ``/mcp`` JSON-RPC
because the REST endpoints (``/v1/memories/*``) use SupabaseJwtGuard
on the server side and reject PATs. JWTs go straight to REST. The
``_uses_mcp`` flag is set once at construct time; from then on each
method picks the right transport internally so callers don't care.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_API_BASE = "https://api.openkt.ai"
DEFAULT_TIMEOUT_S = 8.0


class OpenKTClient:
    """One HTTP call per method, never raises, always returns a dict.

    Methods that mutate (``save``, ``forget``) return the server's
    response envelope; methods that read (``recall``, ``search``,
    ``prime``, ``list_projects``) return the same envelope shape so the
    provider can treat them uniformly.

    Error contract: on ANY transport error, returns a dict with
    ``_error: <str>``. Callers must check for that — exceptions never
    leak out, because the provider runs these inside daemon threads
    that can't propagate to the agent.
    """

    def __init__(
        self,
        *,
        api_key: str,
        api_base: str = DEFAULT_API_BASE,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.timeout_s = timeout_s
        # Discriminate transport by token prefix — see module docstring.
        # PAT tokens (``okt_pat_*``) must go through the MCP endpoint
        # because REST is JWT-only.
        self._uses_mcp = bool(api_key and api_key.startswith("okt_pat_"))

    # ---- public API methods -------------------------------------------------

    def recall(
        self,
        *,
        query: str,
        project_id: str,
        limit: int = 5,
        vector_weight: float = 0.85,
        rerank: bool = True,
        min_confidence: float = 0.6,
        kind: str | None = None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {
            "query": query or "",
            "project_id": project_id,
            "limit": limit,
            "vector_weight": vector_weight,
            "rerank": rerank,
            "min_confidence": min_confidence,
        }
        if kind:
            args["kind"] = kind
        if self._uses_mcp:
            return self._mcp_call("kt_recall", args)
        return self._rest_post("/v1/memories/recall", args)

    def save(
        self,
        *,
        content: str,
        project_id: str,
        kind: str = "context",
        importance: float = 0.5,
        tag_slugs: list[str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "content": content,
            "kind": kind,
            "project_id": project_id,
            "importance": importance,
        }
        if tag_slugs:
            body["tag_slugs"] = tag_slugs
        if self._uses_mcp:
            return self._mcp_call("kt_save_memory", body)
        return self._rest_post("/v1/memories", body)

    def search(
        self,
        *,
        query: str,
        project_id: str,
        limit: int = 10,
        kind: str | None = None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {
            "query": query or "",
            "project_id": project_id,
            "limit": limit,
        }
        if kind:
            args["kind"] = kind
        if self._uses_mcp:
            return self._mcp_call("kt_search_memories", args)
        return self._rest_post("/v1/memories/search", args)

    def forget(self, *, id: str, hard: bool = False) -> dict[str, Any]:
        if self._uses_mcp:
            return self._mcp_call("kt_forget_memory", {"id": id, "hard": hard})
        # REST: DELETE /v1/memories/:id?hard=true
        qs = "?hard=true" if hard else ""
        return self._rest_request("DELETE", f"/v1/memories/{id}{qs}", body=None)

    def prime(self, *, project_id: str, with_briefing: bool = False) -> dict[str, Any]:
        """Get the categorized session-start memory block.

        NOTE: ``/v1/prime`` is JWT-guarded on the server side. PAT users
        get an ``_error`` here; the provider treats that as a no-op and
        falls back to recall-based standing context. The server team
        plans to extend BearerAuthGuard to /v1/prime — see pending
        ticket file.
        """
        body = {
            "project_id": project_id,
            "with_briefing": with_briefing,
            "with_categorized": True,
        }
        # /v1/prime has no MCP equivalent today, so always REST.
        return self._rest_post("/v1/prime", body)

    def list_projects(self) -> dict[str, Any]:
        if self._uses_mcp:
            return self._mcp_call("kt_list_projects", {})
        # REST list of visible projects.
        return self._rest_request("GET", "/v1/projects", body=None)

    # ---- transport layer ----------------------------------------------------

    def _rest_post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._rest_request("POST", path, body=body)

    def _rest_request(
        self, method: str, path: str, *, body: dict[str, Any] | None
    ) -> dict[str, Any]:
        url = f"{self.api_base}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "openkt-hermes/0.1",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            if not raw.strip():
                return {}
            parsed = json.loads(raw)
            # Some endpoints wrap responses in {data: ...} envelopes,
            # others return the bare object — we unwrap the envelope
            # here so provider code sees a consistent dict.
            if isinstance(parsed, dict):
                # Recall + search return {data: [...], meta: {...}}
                # already at the top level; prime returns
                # {categorized: {...}, ...} bare. Both shapes are fine.
                return parsed
            return {"data": parsed}
        except urllib.error.HTTPError as exc:
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8", errors="replace")[:400]
            except Exception:
                pass
            return {"_error": f"HTTP {exc.code}: {exc.reason} {body_text}".strip()}
        except urllib.error.URLError as exc:
            return {"_error": f"network error: {exc.reason!r}"}
        except (TimeoutError, OSError) as exc:
            return {"_error": f"transport error: {exc!r}"}
        except json.JSONDecodeError as exc:
            return {"_error": f"invalid JSON from server: {exc!r}"}

    def _mcp_call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """JSON-RPC tools/call against ``/mcp``.

        The MCP endpoint returns ``text/event-stream`` framing even for
        one-shot calls (lines like ``data: {...}``). We walk the body
        for the first ``data:`` payload; if no SSE framing is present,
        we treat the body as plain JSON.

        Tool results come back as ``result.content[0].text`` which is
        itself a JSON-encoded string of the actual response. We parse
        that and return it so callers see the same shape they'd see
        from the REST path — uniform downstream code.
        """
        url = f"{self.api_base}/mcp"
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "openkt-hermes/0.1",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            envelope: dict[str, Any] = {}
            for line in raw.splitlines():
                if line.startswith("data: "):
                    envelope = json.loads(line[6:])
                    break
            if not envelope and raw.strip():
                envelope = json.loads(raw)
            if "error" in envelope:
                return {"_error": str(envelope["error"])}
            content = (envelope.get("result") or {}).get("content") or []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text") or ""
                    if text.strip():
                        try:
                            inner = json.loads(text)
                            return inner if isinstance(inner, dict) else {"data": inner}
                        except json.JSONDecodeError:
                            return {"data": text}
            return envelope.get("result") or {}
        except urllib.error.HTTPError as exc:
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8", errors="replace")[:400]
            except Exception:
                pass
            return {"_error": f"HTTP {exc.code}: {exc.reason} {body_text}".strip()}
        except urllib.error.URLError as exc:
            return {"_error": f"network error: {exc.reason!r}"}
        except (TimeoutError, OSError) as exc:
            return {"_error": f"transport error: {exc!r}"}
        except json.JSONDecodeError as exc:
            return {"_error": f"invalid JSON-RPC from MCP: {exc!r}"}
