"""OpenKT memory provider for Hermes Agent.

Public surface:
    OpenKTMemoryProvider — the MemoryProvider ABC subclass.
    register(ctx)        — Hermes plugin entry point.

Drop this package into ``$HERMES_HOME/plugins/openkt/`` (or pip
install + symlink) and set ``memory.provider: openkt`` in Hermes's
config.yaml to activate.
"""
from __future__ import annotations

from .provider import OpenKTMemoryProvider

__version__ = "0.1.0"
__all__ = ["OpenKTMemoryProvider", "register"]


def register(ctx: object) -> None:
    """Hermes plugin entry point.

    Called by Hermes's plugin loader. ``ctx`` is a context object with
    ``register_memory_provider(provider)``. We instantiate ONE provider
    and hand it over — Hermes manages the lifecycle from there.
    """
    ctx.register_memory_provider(OpenKTMemoryProvider())  # type: ignore[attr-defined]
