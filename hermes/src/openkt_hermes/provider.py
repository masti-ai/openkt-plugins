"""OpenKT MemoryProvider — the Hermes ABC subclass.

This module is the only file Hermes touches: it owns the lifecycle
(``initialize`` / ``shutdown``), the tool schemas the model sees, the
recall/save dispatch, and the daemon-thread choreography that keeps
turn responses non-blocking.

The provider is intentionally thin — every HTTP call is delegated to
``OpenKTClient``, every threading hop is delegated to ``_threading``,
every config decision is delegated to ``config``. This file is the
adapter between Hermes's call signatures and the OpenKT API.

Sources verified against:
- ``agent/memory_provider.py`` (the Hermes ABC; fetched from
  raw.githubusercontent.com/NousResearch/hermes-agent/main)
- ``plugins/memory/supermemory/__init__.py`` (canonical reference for
  a remote-API provider plugin)
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
from datetime import datetime, timezone
from typing import Any, Optional

try:
    # When running inside Hermes, the ABC lives at this exact path.
    from agent.memory_provider import MemoryProvider as _HermesMemoryProvider
except ImportError:
    # Standalone usage (tests, type checking, dev environments without
    # hermes-agent installed). We define a minimal shim with the same
    # method surface so the subclass is well-formed. This is purely a
    # development convenience — at runtime under Hermes the real class
    # is always imported.
    from abc import ABC, abstractmethod

    class _HermesMemoryProvider(ABC):  # type: ignore[no-redef]
        @property
        @abstractmethod
        def name(self) -> str: ...
        @abstractmethod
        def is_available(self) -> bool: ...
        @abstractmethod
        def initialize(self, session_id: str, **kwargs: Any) -> None: ...
        @abstractmethod
        def get_tool_schemas(self) -> list[dict[str, Any]]: ...
        def system_prompt_block(self) -> str: return ""
        def prefetch(self, query: str, *, session_id: str = "") -> str: return ""
        def queue_prefetch(self, query: str, *, session_id: str = "") -> None: ...
        def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None: ...
        def handle_tool_call(self, tool_name: str, args: dict[str, Any], **kwargs: Any) -> str:
            raise NotImplementedError
        def shutdown(self) -> None: ...
        def on_turn_start(self, turn_number: int, message: str, **kwargs: Any) -> None: ...
        def on_session_end(self, messages: list[dict[str, Any]]) -> None: ...
        def on_session_switch(self, new_session_id: str, *, parent_session_id: str = "", reset: bool = False, **kwargs: Any) -> None: ...
        def on_pre_compress(self, messages: list[dict[str, Any]]) -> str: return ""
        def on_delegation(self, task: str, result: str, *, child_session_id: str = "", **kwargs: Any) -> None: ...
        def get_config_schema(self) -> list[dict[str, Any]]: return []
        def save_config(self, values: dict[str, Any], hermes_home: str) -> None: ...
        def on_memory_write(self, action: str, target: str, content: str, metadata: Optional[dict[str, Any]] = None) -> None: ...


from . import _threading
from .client import OpenKTClient, DEFAULT_API_BASE
from .config import load_config, resolve_project_id, save_config_file

logger = logging.getLogger(__name__)


# Content-shape gates — keep noise out of the memory store.
# These are deliberately conservative; the bias is "save less" because
# false-positives pollute team-wide recall results for everyone.
_TRIVIAL_RE = re.compile(
    r"^(ok|okay|thanks|thank you|got it|sure|yes|no|yep|nope|k|ty|thx|np)\.?\s*$",
    re.IGNORECASE,
)
_MIN_SAVE_LENGTH = 30  # bytes of assistant content before it's worth saving


class OpenKTMemoryProvider(_HermesMemoryProvider):
    """Hermes memory provider backed by OpenKT.

    Two modes (decided at ``initialize()``):
    - Personal: ``project_id`` derived from ``user_id`` / ``agent_identity``
      / ``hermes_home`` hash. Isolated per user, like Mem0/Supermemory.
    - Team:    ``project_id`` taken from configured ``team_project_id``.
      Multiple teammates' Hermes installs point at the same OpenKT
      project; recall surfaces decisions/anti-patterns/incidents
      written by anyone on the team. THIS is the differentiator over
      every other Hermes memory provider.
    """

    def __init__(self, *, client: OpenKTClient | None = None) -> None:
        # Client can be injected for tests. In production it's
        # constructed lazily in initialize() after we know the api_base
        # from config.
        self._client: OpenKTClient | None = client
        self._config: dict[str, Any] = {}
        self._project_id: str = ""
        self._session_id: str = ""
        self._hermes_home: str = ""
        self._agent_context: str = "primary"
        self._pending_prefetch: str = ""
        self._pending_prefetch_lock = threading.Lock()

    # ---- identity -----------------------------------------------------------

    @property
    def name(self) -> str:
        return "openkt"

    # ---- availability -------------------------------------------------------

    def is_available(self) -> bool:
        """Config-only check. NEVER makes a network call.

        Per the Hermes ABC docstring: "Should not make network calls —
        just check config and installed deps." A network call here
        would tax every agent boot AND would make is_available()
        dependent on the user's connectivity at the wrong moment.
        """
        # Accept either OPENKT_API_KEY (the documented var) or the
        # OPENKT_TOKEN var the existing ``kt`` CLI writes. Both work
        # against the same auth path, so we may as well honor both.
        return bool(os.environ.get("OPENKT_API_KEY") or os.environ.get("OPENKT_TOKEN"))

    # ---- lifecycle ----------------------------------------------------------

    def initialize(self, session_id: str, **kwargs: Any) -> None:
        """Wire up the client, resolve project_id, prime config.

        Idempotent — calling twice with different kwargs replaces the
        bound config. Hermes only calls this once per session per the
        ABC docs, so we don't optimize for repeated calls.
        """
        self._session_id = session_id
        self._hermes_home = str(kwargs.get("hermes_home") or os.environ.get("HERMES_HOME") or "")
        self._agent_context = str(kwargs.get("agent_context") or "primary")
        self._config = load_config(self._hermes_home) if self._hermes_home else dict(load_config_defaults())
        self._project_id = resolve_project_id(self._config, kwargs={**kwargs, "hermes_home": self._hermes_home})

        # Only construct the live client if we don't already have one
        # (tests inject a fake). The API key comes from env — never
        # config, never disk — so a leaked openkt.json file can't ship
        # credentials.
        if self._client is None:
            api_key = os.environ.get("OPENKT_API_KEY") or os.environ.get("OPENKT_TOKEN") or ""
            api_base = str(self._config.get("api_base") or DEFAULT_API_BASE)
            timeout = float(self._config.get("request_timeout_s") or 8.0)
            self._client = OpenKTClient(api_key=api_key, api_base=api_base, timeout_s=timeout)

    def shutdown(self) -> None:
        """No durable resources to release — daemon threads die with
        the process automatically. Implemented to satisfy the ABC.
        """
        # Reset state so a stale provider can't accidentally serve a
        # post-shutdown call.
        with self._pending_prefetch_lock:
            self._pending_prefetch = ""

    # ---- session boundaries -------------------------------------------------

    def on_session_switch(
        self,
        new_session_id: str,
        *,
        parent_session_id: str = "",
        reset: bool = False,
        **kwargs: Any,
    ) -> None:
        self._session_id = new_session_id
        # On a true /reset / /new, flush the recall cache so we don't
        # leak the prior conversation's context into the fresh one.
        # On /resume / /branch / compression, keep the cache — the
        # logical conversation continues under a new id.
        if reset:
            with self._pending_prefetch_lock:
                self._pending_prefetch = ""

    def on_session_end(self, messages: list[dict[str, Any]]) -> None:
        """End-of-session extraction.

        Strategy: pick the last meaningful assistant turn AND any user
        turns that look like decisions/preferences (e.g. "we decided
        to use X"). Save them as separate memories so the server-side
        embed pipeline can rank them independently.

        Lower length bar than sync_turn — at session end we're more
        willing to record short summaries; sync_turn's job was to
        capture per-turn fact volume, this is "anything worth saving
        before we lose it." Bias is still on the conservative side
        (skip true acks like "OK"), but a 20-char declaration is fine.

        Non-blocking — daemon thread, fails open.
        """
        if self._agent_context != "primary":
            return
        if not messages:
            return
        _END_MIN_LEN = 15  # more permissive than sync_turn's 30
        # Look at last user message — if it contains a decision/
        # preference signal, save THAT (it's the load-bearing claim).
        last_user = next(
            (m for m in reversed(messages) if m.get("role") == "user" and m.get("content")),
            None,
        )
        if last_user:
            user_text = str(last_user.get("content") or "").strip()
            if len(user_text) >= _END_MIN_LEN and not _TRIVIAL_RE.match(user_text):
                if _detect_kind(user_text) != "context":  # only save if signal-laden
                    self._save_async(user_text, kind=_detect_kind(user_text))
        # Also save the last substantive assistant turn (if any).
        last_assistant = next(
            (m for m in reversed(messages) if m.get("role") == "assistant" and m.get("content")),
            None,
        )
        if last_assistant:
            asst_text = str(last_assistant.get("content") or "").strip()
            if len(asst_text) >= _END_MIN_LEN and not _TRIVIAL_RE.match(asst_text):
                self._save_async(asst_text, kind="context")

    # ---- tools --------------------------------------------------------------

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """OpenAI-style function schemas for the four core tools.

        These names are deliberately prefixed ``openkt_`` (not ``kt_``)
        to avoid colliding with the ``kt_*`` names Claude Code's MCP
        connector already injects. Inside Hermes there's no confusion;
        outside Hermes the names stand alone.
        """
        return [
            {
                "name": "openkt_recall",
                "description": (
                    "Recall the most relevant memories for a query from the user's OpenKT project. "
                    "Use this BEFORE answering any non-trivial question about the project — it "
                    "surfaces prior decisions, conventions, anti-patterns, and incident postmortems "
                    "the user (or their teammates, in team mode) have saved."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural-language search query.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of memories to return (default: 5, max: 50).",
                            "default": 5,
                        },
                        "kind": {
                            "type": "string",
                            "description": "Filter to one memory kind: decision, pattern, incident, skill, context, anti-pattern, debug-recipe, environment, note, fact, other.",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "openkt_save_memory",
                "description": (
                    "Save a non-obvious fact, decision, incident, pattern, or anti-pattern as a "
                    "project memory so future sessions (and teammates) can recall it. Use proactively "
                    "when you learn something the next agent should know."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The fact, decision, or pattern to save (1-20000 chars).",
                        },
                        "kind": {
                            "type": "string",
                            "description": "Memory kind. One of: decision, pattern, incident, skill, context, anti-pattern, debug-recipe, environment, note, fact, other.",
                            "default": "context",
                        },
                        "importance": {
                            "type": "number",
                            "description": "Importance score 0-1 (default: 0.5). Higher values surface more prominently in recall.",
                            "default": 0.5,
                        },
                        "tag_slugs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional tags (each: lowercase, hyphenated, 2-40 chars, max 8).",
                        },
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "openkt_search_memories",
                "description": (
                    "Browse or filter memories by query, kind, or tag without bumping recall counters. "
                    "Use for listing/browsing UX; prefer openkt_recall when you need context to answer."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query."},
                        "limit": {"type": "integer", "default": 10},
                        "kind": {"type": "string", "description": "Optional kind filter."},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "openkt_forget_memory",
                "description": (
                    "Archive (soft, recoverable) or hard-delete a memory by id. Always prefer soft "
                    "archive — hard delete is irreversible and owner-only."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Memory UUID to forget.",
                        },
                        "hard": {
                            "type": "boolean",
                            "description": "True to hard-delete; false (default) to archive.",
                            "default": False,
                        },
                    },
                    "required": ["id"],
                },
            },
        ]

    def handle_tool_call(self, tool_name: str, args: dict[str, Any], **kwargs: Any) -> str:
        """Dispatch tool calls to the client.

        Returns a JSON string per the ABC contract. NEVER raises —
        unknown tools / network failures both come back as JSON with
        an ``error`` key. Hermes's tool-call loop will pass the result
        back to the model as a tool message.
        """
        client = self._client
        if client is None:
            return json.dumps({"error": "OpenKT provider not initialized"})
        try:
            if tool_name == "openkt_recall":
                result = client.recall(
                    query=str(args.get("query") or ""),
                    project_id=self._project_id,
                    limit=int(args.get("limit") or self._config.get("recall_limit", 5)),
                    kind=args.get("kind"),
                    vector_weight=float(self._config.get("recall_vector_weight", 0.85)),
                    rerank=bool(self._config.get("recall_rerank", True)),
                    min_confidence=float(self._config.get("recall_min_confidence", 0.6)),
                )
                return json.dumps(self._normalize_recall(result))
            if tool_name == "openkt_save_memory":
                content = str(args.get("content") or "").strip()
                if not content:
                    return json.dumps({"error": "content is required"})
                result = client.save(
                    content=content,
                    project_id=self._project_id,
                    kind=str(args.get("kind") or self._config.get("default_kind", "context")),
                    importance=float(args.get("importance") or self._config.get("default_importance", 0.5)),
                    tag_slugs=args.get("tag_slugs") or None,
                )
                return json.dumps(result)
            if tool_name == "openkt_search_memories":
                result = client.search(
                    query=str(args.get("query") or ""),
                    project_id=self._project_id,
                    limit=int(args.get("limit") or 10),
                    kind=args.get("kind"),
                )
                return json.dumps(self._normalize_recall(result))
            if tool_name == "openkt_forget_memory":
                mem_id = str(args.get("id") or "").strip()
                if not mem_id:
                    return json.dumps({"error": "id is required"})
                result = client.forget(id=mem_id, hard=bool(args.get("hard") or False))
                return json.dumps(result)
            return json.dumps({"error": f"unknown tool: {tool_name}"})
        except Exception as exc:  # noqa: BLE001
            # Belt-and-suspenders — the client itself never raises, but
            # if a refactor breaks that contract we don't want a stack
            # trace to land in the agent's tool-call loop.
            logger.debug("openkt tool call raised: %r", exc)
            return json.dumps({"error": f"openkt error: {exc!r}"})

    # ---- recall surface -----------------------------------------------------

    def system_prompt_block(self) -> str:
        """Categorized standing context from POST /v1/prime.

        Format mirrors openkt-cli's hook output so users get a
        consistent experience across Claude Code + Hermes. Failure is
        silent — Hermes still gets the rest of the system prompt.

        For PAT users (where /v1/prime is JWT-only today), the prime
        call comes back with ``_error`` and we return "" — recall still
        works because it's PAT-compatible via the MCP path.
        """
        if not self._client or not self._project_id:
            return ""
        try:
            result = self._client.prime(project_id=self._project_id)
        except Exception as exc:  # noqa: BLE001
            logger.debug("openkt prime raised: %r", exc)
            return ""
        if "_error" in result:
            return ""
        categorized = result.get("categorized") or {}
        if not isinstance(categorized, dict):
            return ""
        decisions = categorized.get("decision") or []
        anti = categorized.get("anti-pattern") or []
        if not decisions and not anti:
            return ""
        lines = ["", "OpenKT standing project context:"]
        if decisions:
            lines.append("Key decisions:")
            for mem in decisions[:3]:
                lines.append(_format_memory_line(mem))
        if anti:
            lines.append("Anti-patterns to avoid:")
            for mem in anti[:3]:
                lines.append(_format_memory_line(mem))
        return "\n".join(lines) + "\n"

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Synchronous recall + format. Used right before the API call.

        Implementation strategy: if we've got a cached block from a
        recent ``queue_prefetch``, return that. Otherwise issue a fresh
        recall now — but always fail-open: a backend hiccup must never
        block the user's turn.
        """
        # Cache hit: prior queue_prefetch already populated this.
        with self._pending_prefetch_lock:
            cached = self._pending_prefetch
            # Consume the cache — next prefetch will re-fetch unless
            # the caller queued again.
            self._pending_prefetch = ""
        if cached:
            return cached

        if not self._client or not self._project_id:
            return ""
        try:
            result = self._client.recall(
                query=query,
                project_id=self._project_id,
                limit=int(self._config.get("recall_limit", 5)),
                vector_weight=float(self._config.get("recall_vector_weight", 0.85)),
                rerank=bool(self._config.get("recall_rerank", True)),
                min_confidence=float(self._config.get("recall_min_confidence", 0.6)),
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("openkt prefetch raised: %r", exc)
            return ""
        return self._format_recall_block(result, query)

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """Kick off a recall in a daemon thread; stash the result for
        the next ``prefetch()`` call.

        The signature is fire-and-forget per the ABC docs. We don't
        join the thread — by the time the next turn calls
        ``prefetch()``, either we've populated the cache (fast path)
        or we haven't (graceful: prefetch issues a fresh recall).
        """
        if not self._client or not self._project_id or not query:
            return

        def _do() -> None:
            try:
                result = self._client.recall(
                    query=query,
                    project_id=self._project_id,
                    limit=int(self._config.get("recall_limit", 5)),
                    vector_weight=float(self._config.get("recall_vector_weight", 0.85)),
                    rerank=bool(self._config.get("recall_rerank", True)),
                    min_confidence=float(self._config.get("recall_min_confidence", 0.6)),
                )
                block = self._format_recall_block(result, query)
                with self._pending_prefetch_lock:
                    self._pending_prefetch = block
            except Exception as exc:  # noqa: BLE001
                logger.debug("openkt queue_prefetch raised: %r", exc)

        _threading.run_in_daemon(_do, name="openkt-prefetch")

    def on_pre_compress(self, messages: list[dict[str, Any]]) -> str:
        """Surface a recall block for the compression summarizer.

        Strategy: take the last user message as the query and recall
        against it. The result is a string block that the compressor
        weaves into its summary prompt, so even after compression the
        agent still sees the pinned recall context.

        Non-critical — returns "" on any failure.
        """
        if not messages or not self._client or not self._project_id:
            return ""
        last_user = next(
            (m for m in reversed(messages) if m.get("role") == "user" and m.get("content")),
            None,
        )
        if not last_user:
            return ""
        query = str(last_user.get("content") or "")[:500]
        try:
            result = self._client.recall(
                query=query,
                project_id=self._project_id,
                limit=int(self._config.get("recall_limit", 5)),
            )
        except Exception:
            return ""
        return self._format_recall_block(result, query)

    # ---- write surface ------------------------------------------------------

    def sync_turn(
        self, user_content: str, assistant_content: str, *, session_id: str = ""
    ) -> None:
        """Persist a completed turn IFF the assistant said something
        save-worthy. Non-blocking — work happens in a daemon thread.

        Heuristic: skip trivial acks, skip very short responses. We bias
        toward "save less" because team-mode false-positives pollute
        every teammate's recall — better to miss a save than to spam
        the team's shared memory.
        """
        if self._agent_context != "primary":
            return  # never write from subagents/cron/flush
        text = (assistant_content or "").strip()
        if not text or _TRIVIAL_RE.match(text):
            return
        if len(text) < _MIN_SAVE_LENGTH:
            return
        # Lightweight kind detection — the right thing to do is server-
        # side classification, but bias-by-keyword keeps us shipping a
        # useful default until /v1/memories/enhance is wired in.
        kind = _detect_kind(text)
        # Save what the assistant said as context. The user content is
        # the "query" side of the QA pair — we don't need to store that
        # because recall reconstructs the question from the query.
        self._save_async(text, kind=kind, importance=0.5)

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Mirror Hermes's built-in MEMORY.md / USER.md writes.

        We only mirror ``add`` / ``replace`` — ``remove`` would require
        Hermes-side IDs that don't map to OpenKT memories, so we'd
        end up deleting random things.
        """
        if action not in ("add", "replace"):
            return
        if not content or not content.strip():
            return
        # Tag by target so team members can filter "user profile" vs
        # "agent memory" writes downstream.
        kind = "context" if target == "memory" else "note"
        self._save_async(content.strip(), kind=kind)

    def on_delegation(
        self,
        task: str,
        result: str,
        *,
        child_session_id: str = "",
        **kwargs: Any,
    ) -> None:
        """When a subagent finishes, save its task → result as a memory
        so the parent (and future sessions) can recall what was already
        delegated.
        """
        if not result or len(result.strip()) < _MIN_SAVE_LENGTH:
            return
        content = f"Delegated task: {task[:200]}\nResult: {result[:1500]}"
        self._save_async(content, kind="context")

    # ---- config -------------------------------------------------------------

    def get_config_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "key": "api_key",
                "description": "OpenKT personal access token (okt_pat_...) or Supabase JWT. Mint a PAT at https://openkt.ai/settings/tokens.",
                "secret": True,
                "required": True,
                "env_var": "OPENKT_API_KEY",
                "url": "https://openkt.ai/settings/tokens",
            },
            {
                "key": "api_base",
                "description": "OpenKT API base URL (advanced — change only for self-hosted or staging).",
                "secret": False,
                "default": DEFAULT_API_BASE,
            },
            {
                "key": "default_project_scope",
                "description": "personal (per-user isolation, default) or team (shared memory pool across teammates).",
                "secret": False,
                "default": "personal",
                "choices": ["personal", "team"],
            },
            {
                "key": "team_project_id",
                "description": "OpenKT project_id all teammates should share. Required when default_project_scope=team. Get this from `kt projects list` or the OpenKT dashboard.",
                "secret": False,
                "default": "",
            },
            {
                "key": "default_kind",
                "description": "Default memory kind for sync_turn auto-saves.",
                "secret": False,
                "default": "context",
                "choices": [
                    "decision", "pattern", "incident", "skill", "context",
                    "anti-pattern", "debug-recipe", "environment", "note",
                    "fact", "other",
                ],
            },
        ]

    def save_config(self, values: dict[str, Any], hermes_home: str) -> None:
        save_config_file(values, hermes_home)

    # ---- helpers ------------------------------------------------------------

    def _save_async(
        self,
        content: str,
        *,
        kind: str = "context",
        importance: float = 0.5,
    ) -> None:
        client = self._client
        project_id = self._project_id
        if not client or not project_id:
            return

        def _do() -> None:
            try:
                client.save(
                    content=content,
                    project_id=project_id,
                    kind=kind,
                    importance=importance,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("openkt save raised: %r", exc)

        _threading.run_in_daemon(_do, name="openkt-save")

    def _format_recall_block(self, result: dict[str, Any], query: str) -> str:
        """Render a recall payload as a Hermes additional-context block.

        Empty result → empty string (so Hermes skips the block).
        Error result → also empty (fail-open).
        """
        if not isinstance(result, dict) or "_error" in result:
            return ""
        memories = result.get("data") or []
        # Filter superseded / archived BEFORE rendering — surfacing
        # those would just confuse the model.
        visible = [
            m for m in memories
            if isinstance(m, dict) and not (m.get("superseded_by") or m.get("archived"))
        ]
        if not visible:
            return ""
        # Echo the query in the header so the user (and the model) can
        # see what was matched. Cap at 60 chars to keep the prompt tidy.
        header = f"[OpenKT recall · {len(visible)} memories for {query[:60]!r}]"
        lines = ["", header, "Relevant project memories:"]
        for mem in visible:
            lines.append(_format_memory_line(mem))
        lines.append("")
        return "\n".join(lines)

    def _normalize_recall(self, result: dict[str, Any]) -> dict[str, Any]:
        """Trim noise out of recall/search responses before returning to
        the model. Keeps the JSON payload small enough that a 5-result
        recall fits in a few hundred tokens, not a few thousand.
        """
        if not isinstance(result, dict):
            return {"data": [], "error": "invalid response"}
        if "_error" in result:
            return {"data": [], "error": str(result["_error"])}
        memories = result.get("data") or []
        slim = []
        for mem in memories:
            if not isinstance(mem, dict):
                continue
            slim.append({
                "id": mem.get("id", ""),
                "content": mem.get("content", ""),
                "kind": mem.get("kind", "context"),
                "importance": mem.get("importance", 0.5),
                "created_at": mem.get("created_at", ""),
                "tags": mem.get("tags") or [],
            })
        return {"data": slim, "count": len(slim), "project_id": self._project_id}


# ---- module-level helpers ----------------------------------------------------

def _format_memory_line(mem: dict[str, Any]) -> str:
    """One indented bullet per memory. Trims content + adds importance
    marker so the model can sort visually."""
    content = str(mem.get("content") or "").replace("\n", " ").strip()[:240]
    kind = mem.get("kind") or "context"
    when = str(mem.get("created_at") or "")[:10]
    importance = mem.get("importance", 0.5)
    marker = "★" if isinstance(importance, (int, float)) and importance >= 0.7 else "·"
    suffix = f" ({kind}{' · ' + when if when else ''})"
    return f"  {marker} {content}{suffix}"


def _detect_kind(text: str) -> str:
    """Quick keyword heuristic. Returns ``context`` as a safe default."""
    lowered = text.lower()
    if any(k in lowered for k in ("we decided", "decision:", "we'll use", "going with", "chose ")):
        return "decision"
    if any(k in lowered for k in ("don't ", "avoid ", "never ", "anti-pattern")):
        return "anti-pattern"
    if any(k in lowered for k in ("the bug was", "root cause", "incident:", "postmortem")):
        return "incident"
    if any(k in lowered for k in ("pattern:", "the right way", "best practice")):
        return "pattern"
    return "context"


def load_config_defaults() -> dict[str, Any]:
    """Return the default config dict — used when hermes_home isn't set
    (degenerate startup; should be rare)."""
    from .config import DEFAULT_CONFIG
    return dict(DEFAULT_CONFIG)
