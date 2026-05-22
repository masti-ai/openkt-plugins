"""Config loading and project_id resolution.

Two responsibilities:
1. Load ``$HERMES_HOME/openkt.json`` (provider config — non-secret
   knobs; the API key always lives in env).
2. Resolve the active project_id from a precedence ladder. The
   resolution rules ARE the personal-vs-team mode contract — every
   other Hermes memory provider is single-user, so this is the
   load-bearing differentiator. Tests/test_personal_vs_team.py pins
   the order so it can't quietly regress.

Precedence (highest wins):
    1. ``agent_workspace`` kwarg from Hermes initialize() — explicit
       override at the per-process level. Useful for "this Hermes
       instance is scoped to project X regardless of what config
       says."
    2. ``team_project_id`` from config — set once during ``hermes
       memory setup`` for team mode. Multiple teammates' Hermes
       installs all resolve to the same project_id, sharing the
       memory pool.
    3. ``agent_identity`` kwarg — Hermes profile name (e.g. "coder").
       A personal-scope project namespaced by profile.
    4. ``user_id`` kwarg — gateway user identifier (Telegram, Slack).
    5. Hash of ``hermes_home`` — last-resort stable fallback so the
       project_id at least doesn't drift between invocations of the
       same install.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

# Default knob values used when the config file is missing or partial.
# Kept here (not on the provider class) so resolve_project_id can be
# tested in isolation from the provider.
DEFAULT_CONFIG: dict[str, Any] = {
    "api_base": "https://api.openkt.ai",
    "default_project_scope": "personal",
    "team_project_id": "",
    "default_kind": "context",
    "default_importance": 0.5,
    "recall_limit": 5,
    "recall_vector_weight": 0.85,
    "recall_rerank": True,
    "recall_min_confidence": 0.6,
    "request_timeout_s": 8.0,
}

CONFIG_FILENAME = "openkt.json"


def load_config(hermes_home: str | os.PathLike[str]) -> dict[str, Any]:
    """Load + merge ``$HERMES_HOME/openkt.json`` over the defaults.

    Returns a fully-populated config dict — missing keys are filled
    with ``DEFAULT_CONFIG`` values, missing file means all defaults.

    Never raises. A broken JSON file falls back to defaults plus a
    silent log; we'd rather start with defaults than crash the agent.
    """
    cfg: dict[str, Any] = dict(DEFAULT_CONFIG)
    path = Path(hermes_home) / CONFIG_FILENAME
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update({k: v for k, v in data.items() if v is not None})
        except Exception:
            # Broken config file shouldn't kill the agent — fall back
            # to all-defaults. The user will see degraded behavior (no
            # team mode) but not a startup crash.
            pass
    return cfg


def save_config_file(values: dict[str, Any], hermes_home: str | os.PathLike[str]) -> Path:
    """Merge-write non-secret values into ``$HERMES_HOME/openkt.json``.

    Preserves existing keys not in ``values`` — this method is
    additive, not destructive. Returns the path written to.
    """
    home = Path(hermes_home)
    home.mkdir(parents=True, exist_ok=True)
    path = home / CONFIG_FILENAME
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                existing = raw
        except Exception:
            existing = {}
    existing.update(values)
    path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def resolve_project_id(
    config: dict[str, Any],
    *,
    kwargs: dict[str, Any] | None = None,
) -> str:
    """Pick the OpenKT project_id for this Hermes session.

    See the module docstring for the full precedence ladder. ``kwargs``
    is the dict Hermes passes to ``initialize()`` — we pull
    ``agent_workspace``, ``agent_identity``, ``user_id``, ``hermes_home``
    out of it.
    """
    kw = kwargs or {}

    # 1. explicit per-process override
    workspace = kw.get("agent_workspace")
    if workspace:
        return str(workspace)

    # 2. team mode: a single configured project_id wins for all users
    scope = str(config.get("default_project_scope") or "personal").lower()
    team_project_id = (config.get("team_project_id") or "").strip()
    if scope == "team" and team_project_id:
        return team_project_id

    # 3. personal: identity-namespaced
    identity = kw.get("agent_identity")
    if identity:
        return f"personal/{_slug(str(identity))}"

    # 4. gateway user id
    user_id = kw.get("user_id")
    if user_id:
        return f"personal/{_slug(str(user_id))}"

    # 5. hash of hermes_home — last resort
    hermes_home = kw.get("hermes_home") or os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes")
    digest = hashlib.sha256(str(hermes_home).encode("utf-8")).hexdigest()[:12]
    return f"personal/host-{digest}"


def _slug(raw: str) -> str:
    """Lowercased, dash-safe slug — keeps project_ids predictable."""
    out = []
    for ch in raw.strip().lower():
        if ch.isalnum() or ch in ("-", "_", "."):
            out.append(ch)
        else:
            out.append("-")
    slug = "".join(out).strip("-_") or "user"
    return slug[:64]  # mild cap — server allows 256, we leave headroom for prefixes
