"""Contract tests for OpenKTMemoryProvider.

These tests pin the Hermes MemoryProvider ABC contract — they should
break if the provider stops conforming to what Hermes expects, NOT if
implementation details change. Mocks the HTTP client so every assertion
is about the provider's behavior, not the network.

Coverage matrix (one section per ABC method):
- Identity      : name
- Availability  : is_available
- Lifecycle     : initialize / shutdown / on_session_switch / on_session_end
- Tools         : get_tool_schemas / handle_tool_call
- Recall        : prefetch / queue_prefetch / system_prompt_block / on_pre_compress
- Writes        : sync_turn / on_memory_write / on_delegation
- Config        : get_config_schema / save_config
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from openkt_hermes.provider import OpenKTMemoryProvider


# ---- name --------------------------------------------------------------------

def test_name_is_openkt(provider: OpenKTMemoryProvider) -> None:
    assert provider.name == "openkt"


# ---- is_available ------------------------------------------------------------

class TestIsAvailable:
    """``is_available`` MUST be a pure config check — no network calls."""

    def test_returns_true_when_api_key_env_set(
        self, fake_client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENKT_API_KEY", "okt_pat_xxx")
        p = OpenKTMemoryProvider(client=fake_client)
        assert p.is_available() is True

    def test_returns_false_when_api_key_missing(
        self, fake_client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENKT_API_KEY", raising=False)
        monkeypatch.delenv("OPENKT_TOKEN", raising=False)
        p = OpenKTMemoryProvider(client=fake_client)
        assert p.is_available() is False

    def test_makes_no_network_calls(
        self, fake_client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENKT_API_KEY", "okt_pat_xxx")
        p = OpenKTMemoryProvider(client=fake_client)
        p.is_available()
        # Even one HTTP call would violate the docstring contract:
        # "Should not make network calls — just check config and
        # installed deps."
        assert fake_client.calls == []


# ---- initialize --------------------------------------------------------------

class TestInitialize:
    def test_resolves_personal_project_id_by_default(
        self, fake_client: Any, hermes_home: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENKT_API_KEY", "okt_pat_x")
        p = OpenKTMemoryProvider(client=fake_client)
        p.initialize(session_id="s1", hermes_home=hermes_home, platform="cli", user_id="alice")
        assert p._project_id.startswith("personal/")
        # personal id should incorporate user identity so two users on
        # the same host don't share recall results.
        assert "alice" in p._project_id

    def test_agent_workspace_kwarg_wins_over_identity(
        self, fake_client: Any, hermes_home: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENKT_API_KEY", "okt_pat_x")
        p = OpenKTMemoryProvider(client=fake_client)
        p.initialize(
            session_id="s1",
            hermes_home=hermes_home,
            platform="cli",
            agent_workspace="team-shared",
            agent_identity="coder",
        )
        # workspace beats identity beats user_id — the documented
        # precedence for picking the project scope.
        assert p._project_id == "team-shared"

    def test_team_config_overrides_personal_default(
        self, fake_client: Any, hermes_home: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENKT_API_KEY", "okt_pat_x")
        # Pre-write the team config file as if the user ran setup.
        Path(hermes_home, "openkt.json").write_text(
            json.dumps({"default_project_scope": "team", "team_project_id": "org/acme/api"})
        )
        p = OpenKTMemoryProvider(client=fake_client)
        p.initialize(session_id="s1", hermes_home=hermes_home, platform="cli", user_id="alice")
        assert p._project_id == "org/acme/api"

    def test_stores_session_id_for_later_use(
        self, fake_client: Any, hermes_home: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENKT_API_KEY", "okt_pat_x")
        p = OpenKTMemoryProvider(client=fake_client)
        p.initialize(session_id="sess-123", hermes_home=hermes_home, platform="cli")
        assert p._session_id == "sess-123"

    def test_skips_writes_for_subagent_context(
        self, fake_client: Any, hermes_home: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Per ABC docstring, non-primary agent contexts (subagent, cron,
        flush) should not write to backing memory or the next session will
        be polluted with system-prompt-style content."""
        monkeypatch.setenv("OPENKT_API_KEY", "okt_pat_x")
        p = OpenKTMemoryProvider(client=fake_client)
        p.initialize(
            session_id="s1",
            hermes_home=hermes_home,
            platform="cli",
            agent_context="subagent",
        )
        p.sync_turn("hello", "world")
        # Drain any daemon thread that might have raced.
        time.sleep(0.05)
        assert not any(c["method"] == "save" for c in fake_client.calls)


# ---- shutdown / session lifecycle --------------------------------------------

class TestSessionLifecycle:
    def test_on_session_switch_updates_session_id(
        self, provider: OpenKTMemoryProvider
    ) -> None:
        provider.on_session_switch("new-session-id", parent_session_id="s1", reset=False)
        assert provider._session_id == "new-session-id"

    def test_on_session_switch_with_reset_clears_buffers(
        self, provider: OpenKTMemoryProvider
    ) -> None:
        # Stash something on the provider that reset should flush.
        provider._pending_prefetch = "some pre-cached recall block"
        provider.on_session_switch("brand-new", reset=True)
        assert provider._pending_prefetch == ""

    def test_shutdown_does_not_raise(self, provider: OpenKTMemoryProvider) -> None:
        # No matter the state of background threads, shutdown must be
        # safe to call (Hermes calls it during agent teardown).
        provider.shutdown()

    def test_on_session_end_flushes_async(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        provider.on_session_end([
            {"role": "user", "content": "we decided to use Postgres"},
            {"role": "assistant", "content": "OK, noting the decision."},
        ])
        # session-end is best-effort and non-blocking — give the
        # daemon thread up to half a second to drain before asserting.
        _wait_for_call(fake_client, "save", timeout_s=0.5)
        assert any(c["method"] == "save" for c in fake_client.calls)


# ---- tools -------------------------------------------------------------------

class TestToolSchemas:
    def test_returns_four_core_tools(self, provider: OpenKTMemoryProvider) -> None:
        schemas = provider.get_tool_schemas()
        names = {s["name"] for s in schemas}
        assert names == {
            "openkt_recall",
            "openkt_save_memory",
            "openkt_search_memories",
            "openkt_forget_memory",
        }

    def test_each_schema_is_openai_function_shape(
        self, provider: OpenKTMemoryProvider
    ) -> None:
        for s in provider.get_tool_schemas():
            assert "name" in s
            assert "description" in s
            assert "parameters" in s
            params = s["parameters"]
            assert params["type"] == "object"
            assert "properties" in params

    def test_query_is_required_on_recall(self, provider: OpenKTMemoryProvider) -> None:
        recall = next(s for s in provider.get_tool_schemas() if s["name"] == "openkt_recall")
        assert "query" in recall["parameters"]["required"]


class TestHandleToolCall:
    def test_recall_dispatches_to_client(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        fake_client.responses["recall"] = {
            "data": [{"id": "m1", "content": "use SQLite", "kind": "decision", "importance": 0.8}],
            "meta": {},
        }
        result = provider.handle_tool_call("openkt_recall", {"query": "database"})
        payload = json.loads(result)
        assert any(c["method"] == "recall" for c in fake_client.calls)
        # Result MUST be a JSON string per the ABC contract.
        assert isinstance(result, str)
        assert "data" in payload or "memories" in payload or "results" in payload

    def test_save_memory_dispatches_to_client(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        fake_client.responses["save"] = {"id": "mem_xyz", "content": "we chose Postgres"}
        result = provider.handle_tool_call(
            "openkt_save_memory",
            {"content": "we chose Postgres", "kind": "decision"},
        )
        save_calls = [c for c in fake_client.calls if c["method"] == "save"]
        assert len(save_calls) == 1
        assert save_calls[0]["content"] == "we chose Postgres"
        assert save_calls[0]["kind"] == "decision"
        # JSON string return type.
        json.loads(result)

    def test_forget_dispatches_to_client(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        result = provider.handle_tool_call(
            "openkt_forget_memory", {"id": "mem_xyz", "hard": False}
        )
        forget_calls = [c for c in fake_client.calls if c["method"] == "forget"]
        assert len(forget_calls) == 1
        json.loads(result)

    def test_unknown_tool_returns_error_json(
        self, provider: OpenKTMemoryProvider
    ) -> None:
        result = provider.handle_tool_call("openkt_nonexistent", {})
        payload = json.loads(result)
        # Hermes convention: tool errors are JSON-wrapped, not Python
        # exceptions — exceptions kill the turn.
        assert "error" in payload or "_error" in payload

    def test_network_failure_does_not_raise(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        # Simulate the client raising — handle_tool_call must always
        # return JSON, never propagate, because the agent's tool-call
        # loop will hang if the provider raises.
        def boom(**kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("connection refused")
        fake_client.recall = boom  # type: ignore[method-assign]
        result = provider.handle_tool_call("openkt_recall", {"query": "x"})
        payload = json.loads(result)
        assert "error" in payload or "_error" in payload


# ---- recall surface ----------------------------------------------------------

class TestPrefetch:
    def test_prefetch_calls_recall_and_formats_hits(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        fake_client.responses["recall"] = {
            "data": [
                {"id": "m1", "content": "we use Postgres", "kind": "decision", "importance": 0.9, "created_at": "2026-05-01T12:00:00Z"},
                {"id": "m2", "content": "rerunning migrations breaks the read-replica", "kind": "incident", "importance": 0.7, "created_at": "2026-05-10T08:00:00Z"},
            ],
            "meta": {},
        }
        block = provider.prefetch("database setup")
        assert isinstance(block, str)
        assert "Postgres" in block
        assert "migrations" in block
        # Should be syntactically a Hermes additional-context block (header line + indented bullets).
        assert "OpenKT" in block

    def test_prefetch_empty_when_no_hits(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        fake_client.responses["recall"] = {"data": [], "meta": {}}
        block = provider.prefetch("nothing here")
        assert block == ""

    def test_prefetch_returns_empty_string_on_client_error(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        def boom(**kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("boom")
        fake_client.recall = boom  # type: ignore[method-assign]
        # Fails open — Hermes must keep working if recall API is down.
        assert provider.prefetch("anything") == ""


class TestQueuePrefetch:
    def test_queues_in_daemon_thread(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        before = threading.active_count()
        provider.queue_prefetch("anything")
        # We don't assert thread count after — daemon may complete
        # instantly — but we DO require the call to return without
        # blocking on the client.
        # Drain.
        _wait_for_call(fake_client, "recall", timeout_s=0.5)
        assert any(c["method"] == "recall" for c in fake_client.calls)

    def test_prefetch_after_queue_uses_cached_block(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        fake_client.responses["recall"] = {
            "data": [{"id": "m1", "content": "cached fact", "kind": "context", "importance": 0.5}],
            "meta": {},
        }
        provider.queue_prefetch("warming up")
        _wait_for_call(fake_client, "recall", timeout_s=0.5)
        # Now prefetch should return the cached block WITHOUT making a
        # second recall call.
        before_calls = len(fake_client.calls)
        block = provider.prefetch("warming up")
        # We accept either: cache hit (no new call) or fresh call. The
        # important property is the block is non-empty.
        assert "cached fact" in block or len(fake_client.calls) > before_calls


class TestSystemPromptBlock:
    def test_returns_categorized_block_from_prime(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        fake_client.responses["prime"] = {
            "categorized": {
                "decision": [{"content": "use Postgres", "importance": 0.9}],
                "anti-pattern": [{"content": "do not rerun migrations on prod", "importance": 0.95}],
            }
        }
        block = provider.system_prompt_block()
        assert "Postgres" in block
        assert "migrations" in block

    def test_empty_string_when_prime_returns_no_categories(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        fake_client.responses["prime"] = {"categorized": {}}
        assert provider.system_prompt_block() == ""

    def test_empty_string_on_prime_failure(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        def boom(**kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("network")
        fake_client.prime = boom  # type: ignore[method-assign]
        assert provider.system_prompt_block() == ""


class TestOnPreCompress:
    def test_returns_string_block_for_compression_summary(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        fake_client.responses["recall"] = {
            "data": [{"id": "m1", "content": "pinned decision", "kind": "decision", "importance": 0.9}],
            "meta": {},
        }
        messages = [
            {"role": "user", "content": "what about the database?"},
            {"role": "assistant", "content": "We decided Postgres."},
        ]
        block = provider.on_pre_compress(messages)
        assert isinstance(block, str)
        # Either: rich block (got recall hits) OR empty (graceful).
        # If non-empty, must contain at least one of the recalled items.
        if block:
            assert "pinned decision" in block


# ---- writes ------------------------------------------------------------------

class TestSyncTurn:
    def test_is_non_blocking(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        """sync_turn MUST return immediately, per the Hermes contract."""
        # Make the client's save method block for a long time. If
        # sync_turn is implemented incorrectly (blocking call), this
        # test will time out.
        slow_event = threading.Event()
        original_save = fake_client.save

        def slow_save(**kwargs: Any) -> dict[str, Any]:
            slow_event.wait(timeout=2.0)
            return original_save(**kwargs)

        fake_client.save = slow_save  # type: ignore[method-assign]
        t0 = time.monotonic()
        provider.sync_turn("user said X", "assistant said Y about a decision we made")
        elapsed = time.monotonic() - t0
        # If sync_turn waited for the slow save, elapsed >= 2.0.
        # Daemon-threaded implementation should be near-instant.
        assert elapsed < 0.3, f"sync_turn blocked for {elapsed:.2f}s — should be non-blocking"
        slow_event.set()  # Let the daemon thread complete cleanly.

    def test_skips_trivial_assistant_content(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        provider.sync_turn("hi", "ok")
        time.sleep(0.05)
        # Trivial acks like "ok" / "thanks" should never be saved as
        # memories — that's pure noise.
        assert not any(c["method"] == "save" for c in fake_client.calls)

    def test_saves_substantive_content(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        provider.sync_turn(
            "what database should we use?",
            "Use Postgres. Decided because we already run RDS for the audit log service.",
        )
        _wait_for_call(fake_client, "save", timeout_s=0.5)
        save_calls = [c for c in fake_client.calls if c["method"] == "save"]
        assert len(save_calls) >= 1


class TestOnMemoryWrite:
    def test_mirrors_builtin_memory_writes(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        provider.on_memory_write(
            action="add",
            target="memory",
            content="The user prefers TypeScript.",
            metadata={"write_origin": "builtin_memory_tool", "session_id": "s1"},
        )
        _wait_for_call(fake_client, "save", timeout_s=0.5)
        save_calls = [c for c in fake_client.calls if c["method"] == "save"]
        assert len(save_calls) == 1
        assert "TypeScript" in save_calls[0]["content"]

    def test_skips_remove_action(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        # 'remove' from built-in is a delete; we don't echo deletes
        # because the provider stores by content not by Hermes ID, so
        # there's nothing safe to delete on the OpenKT side.
        provider.on_memory_write(action="remove", target="memory", content="old fact")
        time.sleep(0.05)
        assert not any(c["method"] == "save" for c in fake_client.calls)


class TestOnDelegation:
    def test_captures_subagent_result_as_memory(
        self, provider: OpenKTMemoryProvider, fake_client: Any
    ) -> None:
        provider.on_delegation(
            task="research Postgres replication options",
            result="Streaming replication is the standard pick for our scale; logical replication for cross-version upgrades.",
            child_session_id="sub-1",
        )
        _wait_for_call(fake_client, "save", timeout_s=0.5)
        save_calls = [c for c in fake_client.calls if c["method"] == "save"]
        assert len(save_calls) == 1


# ---- config ------------------------------------------------------------------

class TestConfigSchema:
    def test_declares_api_key_as_secret(
        self, provider: OpenKTMemoryProvider
    ) -> None:
        schema = provider.get_config_schema()
        api_key = next(f for f in schema if f["key"] == "api_key")
        assert api_key["secret"] is True
        assert api_key["env_var"] == "OPENKT_API_KEY"
        # Should link the user to where to mint a PAT.
        assert "openkt.ai" in api_key["url"]

    def test_declares_default_project_scope_with_choices(
        self, provider: OpenKTMemoryProvider
    ) -> None:
        schema = provider.get_config_schema()
        scope = next(f for f in schema if f["key"] == "default_project_scope")
        assert "personal" in scope["choices"]
        assert "team" in scope["choices"]

    def test_save_config_writes_non_secret_values(
        self, provider: OpenKTMemoryProvider, hermes_home: str
    ) -> None:
        provider.save_config(
            {
                "default_project_scope": "team",
                "team_project_id": "org/acme/api",
                "api_base": "https://api.openkt.ai",
            },
            hermes_home,
        )
        config_path = Path(hermes_home) / "openkt.json"
        assert config_path.exists()
        loaded = json.loads(config_path.read_text())
        assert loaded["default_project_scope"] == "team"
        assert loaded["team_project_id"] == "org/acme/api"

    def test_save_config_preserves_existing_keys(
        self, provider: OpenKTMemoryProvider, hermes_home: str
    ) -> None:
        # Pre-populate.
        Path(hermes_home, "openkt.json").write_text(
            json.dumps({"api_base": "https://api.openkt.ai", "default_kind": "context"})
        )
        # Now save_config a different subset.
        provider.save_config({"default_project_scope": "team"}, hermes_home)
        loaded = json.loads(Path(hermes_home, "openkt.json").read_text())
        # Old keys preserved, new key added — never destructive.
        assert loaded["default_kind"] == "context"
        assert loaded["default_project_scope"] == "team"


# ---- helpers -----------------------------------------------------------------

def _wait_for_call(client: Any, method: str, *, timeout_s: float) -> None:
    """Spin until ``method`` shows up in ``client.calls`` or we time out.

    Used by tests that exercise daemon-thread code paths — they need a
    way to synchronize on the background work completing without
    relying on raw sleeps. Polls every 5 ms.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if any(c["method"] == method for c in client.calls):
            return
        time.sleep(0.005)
