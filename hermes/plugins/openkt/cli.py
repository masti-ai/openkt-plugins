"""Optional ``hermes openkt`` CLI subcommand.

Lets users do ``hermes openkt setup`` / ``hermes openkt status`` /
``hermes openkt project`` from inside Hermes without context-switching
to the ``kt`` CLI. Tiny — most actual work still lives in ``kt``.

Hermes's plugin loader looks for ``register_cli(subparser)`` here and
calls it during argparse setup.
"""
from __future__ import annotations

import argparse
import os
from typing import Any

from openkt_hermes.config import load_config


def register_cli(subparser: argparse.ArgumentParser) -> None:
    """Attach ``status`` / ``project`` subcommands to the openkt parser."""
    sub = subparser.add_subparsers(dest="openkt_cmd")

    sub.add_parser("status", help="Show OpenKT provider config and connection status")

    proj = sub.add_parser("project", help="Show the currently bound OpenKT project_id")
    proj.add_argument("--set", dest="set_project", help="Override the project_id for this Hermes profile")


def openkt_command(args: Any) -> int:
    """Entry point. Routes to the chosen subcommand or shows usage."""
    cmd = getattr(args, "openkt_cmd", None) or "status"
    if cmd == "status":
        return _cmd_status()
    if cmd == "project":
        return _cmd_project(args)
    print(f"unknown subcommand: {cmd}")
    return 1


def _cmd_status() -> int:
    hermes_home = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
    cfg = load_config(hermes_home)
    api_key_set = bool(os.environ.get("OPENKT_API_KEY") or os.environ.get("OPENKT_TOKEN"))
    print("OpenKT memory provider")
    print(f"  api_base:              {cfg.get('api_base')}")
    print(f"  scope:                 {cfg.get('default_project_scope')}")
    if cfg.get("default_project_scope") == "team":
        print(f"  team_project_id:       {cfg.get('team_project_id') or '(unset!)'}")
    print(f"  default_kind:          {cfg.get('default_kind')}")
    print(f"  api_key set in env:    {'yes' if api_key_set else 'no — set OPENKT_API_KEY'}")
    return 0


def _cmd_project(args: Any) -> int:
    hermes_home = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
    cfg = load_config(hermes_home)
    if getattr(args, "set_project", None):
        # We don't write here — that's `hermes memory setup`'s job.
        # Echo what the user would need to do.
        print(f"To set the bound project_id, run:")
        print(f"  hermes memory setup --provider openkt")
        print(f"and choose default_project_scope=team with team_project_id={args.set_project}")
        return 0
    if cfg.get("default_project_scope") == "team":
        print(cfg.get("team_project_id") or "(team mode but team_project_id is unset)")
    else:
        print("(personal mode — project_id resolves per-session from agent_identity/user_id)")
    return 0
