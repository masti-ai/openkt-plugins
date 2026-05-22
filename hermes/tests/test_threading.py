"""Threading contract tests.

The Hermes docs are explicit: ``sync_turn`` MUST be non-blocking. The
``_threading`` module is our daemon-thread helper — these tests pin its
behavior so a future refactor doesn't accidentally make ``sync_turn``
block (which would hang every Hermes turn response).
"""
from __future__ import annotations

import threading
import time

from openkt_hermes._threading import run_in_daemon


def test_run_in_daemon_returns_immediately() -> None:
    """The helper must not block on the work — that's the whole point."""
    done = threading.Event()

    def slow_work() -> None:
        time.sleep(0.5)
        done.set()

    t0 = time.monotonic()
    run_in_daemon(slow_work)
    elapsed = time.monotonic() - t0
    assert elapsed < 0.1, f"run_in_daemon blocked for {elapsed:.3f}s"
    # The work should still complete in the background.
    assert done.wait(timeout=2.0)


def test_run_in_daemon_marks_thread_daemon() -> None:
    """Daemon threads die with the parent — required so a hung HTTP
    call doesn't hold the Hermes process open at shutdown."""
    captured: dict[str, threading.Thread] = {}

    def work() -> None:
        captured["t"] = threading.current_thread()

    run_in_daemon(work)
    # Give the thread a moment to start.
    for _ in range(50):
        if "t" in captured:
            break
        time.sleep(0.01)
    assert captured["t"].daemon is True


def test_exceptions_in_daemon_dont_crash_caller() -> None:
    """A daemon-thread crash MUST be swallowed — leaking to stderr is
    OK; raising up the stack would mean a flaky network call crashed
    the agent process."""
    def boom() -> None:
        raise RuntimeError("kaboom")

    # No exception escapes here.
    run_in_daemon(boom)
    # The caller continues.
    assert True
