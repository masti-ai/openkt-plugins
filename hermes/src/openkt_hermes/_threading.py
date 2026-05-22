"""Daemon-thread helper for non-blocking writes.

The Hermes ``MemoryProvider`` ABC requires ``sync_turn()`` to return
without blocking the turn response. The simplest correct implementation
is to spawn a daemon thread per fire-and-forget call:

- daemon=True so a hung HTTP request doesn't keep the Hermes process
  alive at shutdown
- swallowed exceptions so a network blip in a write-path doesn't crash
  the parent agent

Why per-call threads instead of a thread pool?
- The volume is tiny (one write per turn at most, plus occasional
  on_session_end / on_memory_write fires).
- A pool would need a shutdown story (worker join on provider.shutdown).
- Threads are lightweight on Python 3.11+; the overhead is negligible
  compared to the HTTP latency we're hiding.

If we ever need to bound concurrency (e.g. someone has 1000 turns/sec)
we can swap this for a bounded pool without changing the call sites.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)


def run_in_daemon(fn: Callable[[], None], *, name: str | None = None) -> threading.Thread:
    """Run ``fn`` in a daemon thread and return immediately.

    Returns the started ``Thread`` for tests that want to assert on
    daemon status. Production callers should ignore the return value —
    we don't ever join these threads.
    """
    def _wrapper() -> None:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            # Log but swallow — exceptions on the write path must never
            # escape to the agent process. The user's session keeps
            # going; only memory sync is degraded.
            logger.debug("openkt-hermes daemon thread failed: %r", exc)

    t = threading.Thread(target=_wrapper, daemon=True, name=name or "openkt-hermes")
    t.start()
    return t
