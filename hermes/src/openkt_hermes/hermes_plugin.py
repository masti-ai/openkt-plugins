"""Hermes entry-point module for pip-installed discovery.

Hermes scans the ``hermes_agent.plugins`` entry-point group at startup and
calls ``register(ctx)`` on each module it finds. Installing ``openkt-hermes``
via pip is then enough — no symlink into ``$HERMES_HOME/plugins/`` needed.
The drop-in shim at ``plugins/openkt/`` remains for users who prefer the
file-based install; both paths register the same provider.
"""
from __future__ import annotations

from openkt_hermes import OpenKTMemoryProvider


def register(ctx: object) -> None:
    ctx.register_memory_provider(OpenKTMemoryProvider())  # type: ignore[attr-defined]
