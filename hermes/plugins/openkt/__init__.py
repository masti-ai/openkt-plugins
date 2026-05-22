"""Hermes plugin entry point for OpenKT memory provider.

Drop this directory into ``$HERMES_HOME/plugins/openkt/`` (or install
``openkt-hermes`` via pip and symlink) to make Hermes discover the
provider. After dropping in, set ``memory.provider: openkt`` in
``$HERMES_HOME/config.yaml`` to activate.

The actual provider lives in the ``openkt_hermes`` package — this file
just wires Hermes's plugin loader to it. Keeping the plugin shim thin
(one import + one register call) means upgrades happen entirely through
``pip install --upgrade openkt-hermes``; the shim never has to change.
"""
from __future__ import annotations

from openkt_hermes import OpenKTMemoryProvider


def register(ctx: object) -> None:
    """Hermes calls this once during plugin discovery."""
    ctx.register_memory_provider(OpenKTMemoryProvider())  # type: ignore[attr-defined]
