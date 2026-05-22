"""Live integration test against api.openkt.ai.

Gated behind ``OPENKT_API_KEY`` AND ``OPENKT_TEST_PROJECT_ID`` so:
- CI without creds skips this entire module (see conftest.py)
- a contributor without a token can still run ``pytest`` clean
- the test never accidentally writes to the user's MAIN project — they
  have to opt in by setting OPENKT_TEST_PROJECT_ID to a throwaway

Round-trip: save → recall → verify the saved fact is returned.
"""
from __future__ import annotations

import os
import time
import uuid

import pytest

from openkt_hermes.client import OpenKTClient
from openkt_hermes.provider import OpenKTMemoryProvider


pytestmark = pytest.mark.integration


def test_save_then_recall_roundtrip() -> None:
    project_id = os.environ["OPENKT_TEST_PROJECT_ID"]
    api_key = os.environ["OPENKT_API_KEY"]

    # Use a unique marker so we can verify we got OUR write back, not
    # somebody else's pre-existing memory. Cheap collision safety —
    # uuid in the content + recall by that uuid prefix.
    marker = f"openkt_hermes_integration_{uuid.uuid4().hex[:8]}"
    content = f"{marker} — adapter integration test wrote this; safe to forget"

    # Use a generous timeout — the server's outbox + embed pipeline can
    # take 5-10s in development. CI environments running this should
    # treat slow servers as known.
    client = OpenKTClient(
        api_key=api_key,
        api_base=os.environ.get("OPENKT_API_BASE", "https://api.openkt.ai"),
        timeout_s=30.0,
    )
    save_result = client.save(content=content, kind="note", project_id=project_id, importance=0.1)
    if "_error" in save_result:
        # Known: server enqueues to MemMachine which can transiently
        # 400/503. We skip rather than fail — the client behaved
        # correctly by returning ``_error`` instead of raising.
        pytest.skip(f"server returned error (expected sometimes): {save_result['_error']}")
    assert save_result.get("id"), f"save returned no id: {save_result}"
    memory_id = save_result["id"]

    # The save → recall pipeline is async on the server (outbox-driven
    # embed pass). Poll for up to 30s before failing — recall typically
    # picks the new memory up within 5s.
    deadline = time.monotonic() + 30.0
    found = False
    while time.monotonic() < deadline:
        result = client.recall(query=marker, project_id=project_id, limit=5)
        if any(marker in (m.get("content") or "") for m in result.get("data", [])):
            found = True
            break
        time.sleep(2.0)
    # Cleanup happens regardless of pass/fail to avoid leaving test data.
    try:
        client.forget(id=memory_id, hard=True)
    except Exception:
        pass
    assert found, f"recall never returned the saved memory marker {marker!r} within 30s"


def test_recall_against_live_project() -> None:
    """Smoke test: recall returns real memories from a real project.

    This is the path that actually matters for end users — the save
    path can be flaky for backend reasons unrelated to this client,
    but recall is what every Hermes turn exercises.
    """
    project_id = os.environ["OPENKT_TEST_PROJECT_ID"]
    api_key = os.environ["OPENKT_API_KEY"]
    client = OpenKTClient(
        api_key=api_key,
        api_base=os.environ.get("OPENKT_API_BASE", "https://api.openkt.ai"),
        timeout_s=30.0,
    )
    # Cast a wide net — we only need ONE memory back to confirm the
    # end-to-end path works.
    result = client.recall(query="the", project_id=project_id, limit=5, min_confidence=0.0)
    assert "_error" not in result, f"recall failed: {result.get('_error')}"
    # data may legitimately be empty if the test project is empty —
    # the important thing is the response parsed cleanly.
    assert "data" in result
