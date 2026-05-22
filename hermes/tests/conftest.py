"""Shared pytest fixtures for openkt-hermes.

Two fixture flavors:
1. ``mock_client`` — replaces the HTTP client with an in-memory fake so
   unit tests can assert against the abstract contract without ever
   touching the network. This is the default for the whole suite.
2. ``live_client`` — gated behind ``OPENKT_API_KEY`` + an explicit
   ``OPENKT_TEST_PROJECT_ID`` env var. Lets a single integration test
   exercise the real `api.openkt.ai` endpoints end-to-end. Skips
   automatically in CI without creds, so the suite still runs green.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


class FakeClient:
    """In-memory stand-in for ``OpenKTClient``.

    Stores every call in ``self.calls`` so tests can assert "the provider
    invoked ``save`` once with this content"  without spinning up a
    server. Returns whatever we set on ``responses[<method>]`` next, so
    a single test can stage a recall response, a save response, and a
    prime response in sequence.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        # Default responses — tests can override per call.
        self.responses: dict[str, Any] = {
            "recall": {"data": [], "meta": {}},
            "save": {"id": "mem_test"},
            "search": {"data": [], "meta": {}},
            "forget": {"forgotten": True, "id": "mem_test"},
            "prime": {"categorized": {}, "with_categorized": True},
            "list_projects": {"projects": []},
        }
        # Track every issued HTTP request so threading tests can wait
        # for daemon threads to flush.
        self._completion_events: list = []

    def _record(self, method: str, **kwargs: Any) -> Any:
        self.calls.append({"method": method, **kwargs})
        return self.responses.get(method, {})

    def recall(self, **kwargs: Any) -> dict[str, Any]:
        return self._record("recall", **kwargs)

    def save(self, **kwargs: Any) -> dict[str, Any]:
        return self._record("save", **kwargs)

    def search(self, **kwargs: Any) -> dict[str, Any]:
        return self._record("search", **kwargs)

    def forget(self, **kwargs: Any) -> dict[str, Any]:
        return self._record("forget", **kwargs)

    def prime(self, **kwargs: Any) -> dict[str, Any]:
        return self._record("prime", **kwargs)

    def list_projects(self, **kwargs: Any) -> dict[str, Any]:
        return self._record("list_projects", **kwargs)


@pytest.fixture
def fake_client() -> FakeClient:
    return FakeClient()


@pytest.fixture
def hermes_home(tmp_path: Path) -> str:
    """Per-test fake HERMES_HOME so config writes don't leak between tests."""
    home = tmp_path / "hermes"
    home.mkdir()
    return str(home)


@pytest.fixture
def provider(fake_client: FakeClient, hermes_home: str, monkeypatch: pytest.MonkeyPatch):
    """An initialized OpenKTMemoryProvider with a fake client wired in.

    Sets OPENKT_API_KEY so is_available() returns True without prompting
    integration tests. Uses session_id ``s1`` and a personal project.
    """
    monkeypatch.setenv("OPENKT_API_KEY", "okt_pat_unit_test_dummy_key")
    from openkt_hermes.provider import OpenKTMemoryProvider

    p = OpenKTMemoryProvider(client=fake_client)
    p.initialize(
        session_id="s1",
        hermes_home=hermes_home,
        platform="cli",
        agent_identity="coder",
        user_id="user-test",
    )
    return p


# ---- Integration test gating -------------------------------------------------

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip integration tests unless the user explicitly opted in.

    Two signals required:
    - ``OPENKT_API_KEY`` set (so the client can authenticate)
    - ``OPENKT_TEST_PROJECT_ID`` set (so we have a project to write into
      without polluting the user's main project)
    """
    if os.environ.get("OPENKT_API_KEY") and os.environ.get("OPENKT_TEST_PROJECT_ID"):
        return
    skip = pytest.mark.skip(
        reason="integration test — set OPENKT_API_KEY + OPENKT_TEST_PROJECT_ID to run"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
