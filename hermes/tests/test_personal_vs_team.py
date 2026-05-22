"""Personal-vs-team project resolution tests.

This is the load-bearing differentiator over every other Hermes memory
provider — no other provider supports a shared team memory pool. These
tests pin the resolution rules so a refactor can't quietly regress the
team mode.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from openkt_hermes.config import resolve_project_id, load_config


class TestPersonalMode:
    def test_default_is_personal_when_no_config(
        self, hermes_home: str
    ) -> None:
        cfg = load_config(hermes_home)
        assert cfg["default_project_scope"] == "personal"

    def test_user_id_kwarg_used_for_personal_scope(
        self, hermes_home: str
    ) -> None:
        cfg = load_config(hermes_home)
        pid = resolve_project_id(cfg, kwargs={"user_id": "alice", "platform": "cli"})
        assert pid.startswith("personal/")
        assert "alice" in pid

    def test_hermes_home_hash_fallback(
        self, hermes_home: str
    ) -> None:
        cfg = load_config(hermes_home)
        # No user_id, no agent_identity — fall back to a hash of
        # hermes_home so the project_id is at least stable per install.
        pid = resolve_project_id(cfg, kwargs={"hermes_home": hermes_home, "platform": "cli"})
        assert pid.startswith("personal/")
        # Stable: same hermes_home produces same id across calls.
        pid2 = resolve_project_id(cfg, kwargs={"hermes_home": hermes_home, "platform": "cli"})
        assert pid == pid2


class TestTeamMode:
    def test_team_config_uses_team_project_id(
        self, hermes_home: str
    ) -> None:
        Path(hermes_home, "openkt.json").write_text(
            json.dumps({
                "default_project_scope": "team",
                "team_project_id": "org/acme/api",
            })
        )
        cfg = load_config(hermes_home)
        pid = resolve_project_id(cfg, kwargs={"user_id": "alice", "platform": "cli"})
        # Team mode: project_id is fixed to the configured team pool —
        # alice and bob both write into and recall from the same one.
        assert pid == "org/acme/api"

    def test_team_mode_ignores_per_user_kwargs(
        self, hermes_home: str
    ) -> None:
        """Team mode is intentionally insensitive to per-user kwargs —
        that's how teammates share a memory pool."""
        Path(hermes_home, "openkt.json").write_text(
            json.dumps({
                "default_project_scope": "team",
                "team_project_id": "org/acme/api",
            })
        )
        cfg = load_config(hermes_home)
        a = resolve_project_id(cfg, kwargs={"user_id": "alice", "platform": "cli"})
        b = resolve_project_id(cfg, kwargs={"user_id": "bob", "platform": "cli"})
        assert a == b == "org/acme/api"

    def test_agent_workspace_wins_over_team_config(
        self, hermes_home: str
    ) -> None:
        """If the agent process explicitly passes agent_workspace, that
        beats the team config — useful for per-process overrides."""
        Path(hermes_home, "openkt.json").write_text(
            json.dumps({"default_project_scope": "team", "team_project_id": "org/acme/api"})
        )
        cfg = load_config(hermes_home)
        pid = resolve_project_id(
            cfg, kwargs={"agent_workspace": "org/acme/special", "platform": "cli"}
        )
        assert pid == "org/acme/special"


class TestPrecedence:
    """Document the full precedence order in one place so the rules
    don't drift from the README claims."""

    @pytest.fixture
    def team_cfg(self, hermes_home: str) -> dict[str, Any]:
        Path(hermes_home, "openkt.json").write_text(
            json.dumps({"default_project_scope": "team", "team_project_id": "org/acme/api"})
        )
        return load_config(hermes_home)

    def test_workspace_beats_team_beats_personal(
        self, team_cfg: dict[str, Any]
    ) -> None:
        # 1. explicit agent_workspace — highest priority
        assert resolve_project_id(team_cfg, kwargs={"agent_workspace": "ws-1"}) == "ws-1"
        # 2. team config — next
        assert resolve_project_id(team_cfg, kwargs={"user_id": "alice"}) == "org/acme/api"
        # 3. personal fallback — only if scope is "personal"
        personal_cfg = {"default_project_scope": "personal"}
        assert resolve_project_id(
            personal_cfg, kwargs={"user_id": "alice"}
        ).startswith("personal/")
