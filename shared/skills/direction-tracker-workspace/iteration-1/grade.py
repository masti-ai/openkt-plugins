#!/usr/bin/env python3
"""Automated grader for direction-tracker eval runs.

Reads eval_metadata.json (assertions), runs each as a deterministic
check against the run's reply.md and DIRECTIONS.md, writes grading.json
with text/passed/evidence (the exact fields the viewer expects).
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

WS = Path(__file__).parent

EVALS = [
    ("first-time-multi-thread-detection", None),
    ("explicit-pool-view-query", WS / "explicit-pool-view-query/input/DIRECTIONS.md"),
    ("same-pool-subthread-no-drift", WS / "same-pool-subthread-no-drift/input/DIRECTIONS.md"),
    ("bulk-multi-direction-prompt", WS / "bulk-multi-direction-prompt/input/DIRECTIONS.md"),
]


def read(p: Path) -> str:
    try:
        return p.read_text()
    except FileNotFoundError:
        return ""


def has(haystack: str, *needles: str) -> str | None:
    """Return the first matching needle (case-insensitive), or None."""
    h = haystack.lower()
    for n in needles:
        if n.lower() in h:
            return n
    return None


# Negation patterns — explicit non-drift statements that shouldn't count
# as drift markers. The agent often narrates "no drift flag" when
# correctly suppressing one — that's the OPPOSITE of a drift flag.
NEGATION_PATTERNS = [
    r"no\s+drift\s+flag",
    r"no\s+drift\s+marker",
    r"didn't\s+(?:flag|trigger)\s+drift",
    r"not\s+a\s+drift",
    r"isn't\s+drift",
]


def has_drift_marker(reply: str, *markers: str) -> str | None:
    """Like has(), but strips negation patterns first so 'no drift flag'
    doesn't get counted as a drift marker."""
    cleaned = reply
    for neg in NEGATION_PATTERNS:
        cleaned = re.sub(neg, "", cleaned, flags=re.IGNORECASE)
    return has(cleaned, *markers)


def count_pools(text: str) -> int:
    return len(re.findall(r"^##\s*Pool\s+\d+", text, re.MULTILINE))


def has_status_flag(text: str) -> bool:
    return bool(re.search(r"`(LEADING|PARKED|BLOCKED|DONE|DRIFT|SEED|RESEARCH)`", text))


def grade_eval_1(reply: str, dirs: str, input_dirs: str) -> list[dict]:
    """first-time-multi-thread-detection — should create DIRECTIONS.md
    with 2 pools (CLI + Marketing) and drift-flag the reply."""
    out: list[dict] = []
    out.append({
        "text": "DIRECTIONS.md was created at project root (file didn't exist before)",
        "passed": len(dirs.strip()) > 0,
        "evidence": f"output DIRECTIONS.md is {len(dirs)} bytes (input was 0)",
    })
    n = count_pools(dirs)
    out.append({
        "text": "DIRECTIONS.md contains at least 2 distinct pools",
        "passed": n >= 2,
        "evidence": f"found {n} pool heading(s)",
    })
    cli_hit = has(dirs, "CLI", "auth refactor", "kt mcp serve")
    out.append({
        "text": "One pool captures the CLI auth refactor (from history)",
        "passed": cli_hit is not None,
        "evidence": f"matched '{cli_hit}'" if cli_hit else "no CLI/auth match in DIRECTIONS.md",
    })
    marketing_hit = has(dirs, "marketing", "landing", "hero")
    out.append({
        "text": "One pool captures the marketing landing thread (new)",
        "passed": marketing_hit is not None,
        "evidence": f"matched '{marketing_hit}'" if marketing_hit else "no marketing/landing match",
    })
    drift_hit = has(reply, "Note:", "pulling toward", "drift", "pivot", "park it")
    out.append({
        "text": "Reply text contains an inline drift flag mentioning the new pool",
        "passed": drift_hit is not None,
        "evidence": f"matched drift marker '{drift_hit}'" if drift_hit else "no drift flag in reply",
    })
    hero_hit = has(reply, "hero", "image", "above the fold")
    out.append({
        "text": "Reply still answers the hero image question (drift flag doesn't block)",
        "passed": hero_hit is not None,
        "evidence": f"reply discusses hero/image (matched '{hero_hit}')" if hero_hit else "no hero answer in reply",
    })
    out.append({
        "text": "Pool entries include at least one status flag",
        "passed": has_status_flag(dirs),
        "evidence": "status flags present" if has_status_flag(dirs) else "no `LEADING`/`SEED`/etc. found",
    })
    return out


def grade_eval_2(reply: str, dirs: str, input_dirs: str) -> list[dict]:
    """explicit-pool-view-query — should render but NOT modify."""
    out: list[dict] = []
    unchanged = dirs.strip() == input_dirs.strip()
    out.append({
        "text": "DIRECTIONS.md was NOT modified (byte-identical to input)",
        "passed": unchanged,
        "evidence": "post-state matches input exactly" if unchanged
        else f"diff: input {len(input_dirs)} bytes, output {len(dirs)} bytes",
    })
    out.append({
        "text": "Reply renders existing pool headers (Pool 1, Pool 2)",
        "passed": "Pool 1" in reply and "Pool 2" in reply,
        "evidence": f"Pool 1 in reply: {'Pool 1' in reply}; Pool 2 in reply: {'Pool 2' in reply}",
    })
    flags_in_reply = sum(1 for f in ("LEADING", "DONE", "SEED", "PARKED") if f in reply)
    out.append({
        "text": "Reply preserves status flags for entries (LEADING, DONE, SEED visible)",
        "passed": flags_in_reply >= 2,
        "evidence": f"{flags_in_reply} status-flag tokens preserved in reply",
    })
    leading_hit = has(reply, "leading edge", "focus", "installation is easier")
    out.append({
        "text": "Reply contains the leading-edge synthesis from DIRECTIONS.md",
        "passed": leading_hit is not None,
        "evidence": f"matched '{leading_hit}'" if leading_hit else "no leading-edge synthesis surfaced",
    })
    drift_hit = has_drift_marker(reply, "pulling toward", "I'll add it as `SEED`", "say 'pivot'", "park it")
    out.append({
        "text": "No drift flag in reply (this is a query, not a new direction)",
        "passed": drift_hit is None,
        "evidence": "no drift markers found" if drift_hit is None else f"unexpected drift marker: {drift_hit}",
    })
    orient_hit = has(reply, "refocus", "stay", "pivot", "want to", "?")
    out.append({
        "text": "Reply ends with an orientation question",
        "passed": reply.rstrip().endswith("?") or orient_hit is not None,
        "evidence": "ends with '?' or orientation cue" if (reply.rstrip().endswith("?") or orient_hit) else "no orientation question",
    })
    return out


def grade_eval_3(reply: str, dirs: str, input_dirs: str) -> list[dict]:
    """same-pool-subthread-no-drift — should add entry under Pool 1, NOT
    open Pool 2, NOT flag drift."""
    out: list[dict] = []
    modified = dirs.strip() != input_dirs.strip()
    out.append({
        "text": "DIRECTIONS.md was modified (a new entry was added)",
        "passed": modified,
        "evidence": "output differs from input" if modified else "output identical to input",
    })
    jwt_in_pool_1 = bool(re.search(r"##\s*Pool\s+1[^\n]*\n.*?(JWT|refresh|rotat|token rotat)", dirs, re.DOTALL | re.IGNORECASE))
    out.append({
        "text": "The new entry was added UNDER Pool 1 (auth refactor) — NOT as a new pool",
        "passed": jwt_in_pool_1,
        "evidence": "JWT/refresh entry found inside Pool 1 section" if jwt_in_pool_1 else "JWT entry not located under Pool 1",
    })
    n = count_pools(dirs)
    out.append({
        "text": "DIRECTIONS.md still has only Pool 1 (no Pool 2 introduced)",
        "passed": n == 1,
        "evidence": f"found {n} pool heading(s); expected 1",
    })
    drift_hit = has_drift_marker(reply, "pulling toward", "new Pool", "I'll add it as `SEED`", "park it", "say 'pivot'")
    out.append({
        "text": "No drift flag in reply (sub-thread of leading pool — should not flag)",
        "passed": drift_hit is None,
        "evidence": "no drift markers in reply" if drift_hit is None else f"unexpected drift marker '{drift_hit}'",
    })
    auth_hit = has(reply, "JWT", "refresh", "rotat", "401", "token")
    out.append({
        "text": "Reply answers the JWT-refresh question normally",
        "passed": auth_hit is not None,
        "evidence": f"reply discusses JWT/refresh (matched '{auth_hit}')" if auth_hit else "no JWT/refresh content",
    })
    out.append({
        "text": "New entry has a status flag",
        "passed": has_status_flag(dirs),
        "evidence": "status flag present in DIRECTIONS.md" if has_status_flag(dirs) else "no status flag",
    })
    return out


def grade_eval_4(reply: str, dirs: str, input_dirs: str) -> list[dict]:
    """bulk-multi-direction-prompt — 3 new pools, single consolidated note."""
    out: list[dict] = []
    n = count_pools(dirs)
    out.append({
        "text": "DIRECTIONS.md was modified to include 3 new pools (Analytics, Design sync, Deploy pipeline)",
        "passed": n >= 4,
        "evidence": f"found {n} pool heading(s); expected 4 (original Pool 1 + 3 new)",
    })
    pool_1_preserved = "Pool 1" in dirs and ("CLI" in dirs or "auth" in dirs)
    out.append({
        "text": "Pool 1 (CLI auth refactor) is preserved unchanged",
        "passed": pool_1_preserved,
        "evidence": "Pool 1 + CLI/auth still present" if pool_1_preserved else "Pool 1 missing or renamed",
    })
    # Count drift markers in reply — should be 1 consolidated, not 3 separate
    drift_marker_count = len(re.findall(r"(Note:|pulling toward|new Pool|orthogonal to)", reply, re.IGNORECASE))
    out.append({
        "text": "Reply contains a SINGLE consolidated note at top (not 3 separate drift flags)",
        "passed": 1 <= drift_marker_count <= 4,  # 1 note can reference all 3
        "evidence": f"{drift_marker_count} drift-marker occurrence(s) (consolidated if 1-4)",
    })
    analytics = has(reply, "analytics", "Plausible", "PostHog", "GA4")
    design = has(reply, "design", "color", "brand")
    deploy = has(reply, "pipeline", "deploy", "CI", "deployment")
    all_three = analytics is not None and design is not None and deploy is not None
    out.append({
        "text": "Consolidated note mentions all three new pools by name",
        "passed": all_three,
        "evidence": f"analytics={analytics is not None}, design={design is not None}, deploy={deploy is not None}",
    })
    leading_ask = has(reply, "leading edge", "which", "first", "want me to start", "which one")
    out.append({
        "text": "Reply asks which is the new leading edge or acknowledges all three threads",
        "passed": leading_ask is not None,
        "evidence": f"matched orientation prompt '{leading_ask}'" if leading_ask else "no leading-edge question",
    })
    themes_present = bool(re.findall(r"\*Theme:.+\*", dirs))
    out.append({
        "text": "Each new pool has a one-line theme description",
        "passed": themes_present,
        "evidence": "theme italic lines present in DIRECTIONS.md" if themes_present else "no *Theme:* lines",
    })
    out.append({
        "text": "Each new pool entry has a status flag",
        "passed": has_status_flag(dirs),
        "evidence": "status flags present" if has_status_flag(dirs) else "no status flags",
    })
    return out


GRADERS = {
    "first-time-multi-thread-detection": grade_eval_1,
    "explicit-pool-view-query": grade_eval_2,
    "same-pool-subthread-no-drift": grade_eval_3,
    "bulk-multi-direction-prompt": grade_eval_4,
}


def main() -> int:
    total = passed = 0
    for name, input_path in EVALS:
        eval_dir = WS / name
        input_dirs = read(input_path) if input_path else ""
        for arm in ("with_skill", "without_skill"):
            out_dir = eval_dir / arm / "outputs"
            reply = read(out_dir / "reply.md")
            dirs_md = read(out_dir / "DIRECTIONS.md")
            grader = GRADERS[name]
            assertions = grader(reply, dirs_md, input_dirs)
            n_total = len(assertions)
            n_passed = sum(1 for a in assertions if a["passed"])
            grading_doc = {
                "summary": {
                    "passed": n_passed,
                    "failed": n_total - n_passed,
                    "total": n_total,
                    "pass_rate": round(n_passed / n_total, 4) if n_total else 0.0,
                },
                "expectations": assertions,
            }
            (eval_dir / arm / "grading.json").write_text(json.dumps(grading_doc, indent=2))
            # Also write to run-1 subdir so aggregate_benchmark.py finds it
            (eval_dir / arm / "run-1").mkdir(parents=True, exist_ok=True)
            (eval_dir / arm / "run-1" / "grading.json").write_text(json.dumps(grading_doc, indent=2))
            total += n_total
            passed += n_passed
            print(f"{name:>40s} | {arm:>14s} | {n_passed}/{n_total}")
    print(f"\nTOTAL: {passed}/{total} = {passed/total*100:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
