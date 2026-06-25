"""Regression guard for the composite GitHub Action's hardening.

The action runs in the consumer's checked-out workspace (GITHUB_WORKSPACE), so
every `python3 -c` MUST use -P (PYTHONSAFEPATH) — otherwise CWD is on sys.path[0]
and an attacker's PR could plant a json.py / shadow the skills.* package at the
repo root to get code execution in the consumer's CI (security audit SC-1).
"""
from __future__ import annotations

import re
from pathlib import Path

ACTION_YML = Path(__file__).resolve().parents[4] / "action.yml"


def test_action_yml_exists_at_repo_root():
    # Marketplace eligibility + the path this guard inspects.
    assert ACTION_YML.is_file(), "action.yml must live at the repo root"


def test_every_python3_dash_c_uses_safepath():
    text = ACTION_YML.read_text(encoding="utf-8")
    # Find real invocations: `python3` followed (same line) by a `-c`, ignoring
    # prose comments (lines whose first non-space char is '#').
    offenders = []
    for i, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        # `python3 ... -c` on this line, but not `python3 -P ... -c`
        if re.search(r"python3\s+-c\b", line) and not re.search(r"python3\s+-P\b", line):
            offenders.append((i, line.strip()))
    assert not offenders, (
        "Every `python3 -c` in action.yml must use -P (PYTHONSAFEPATH) to avoid "
        f"CWD module shadowing in consumer CI (SC-1). Offending lines: {offenders}"
    )


def test_action_has_at_least_the_known_python_steps():
    # Sanity: the guard is actually looking at the scorer action, not an empty file.
    text = ACTION_YML.read_text(encoding="utf-8")
    assert text.count("python3 -P -c") >= 4, (
        "Expected >=4 hardened python3 -P -c invocations; the action may have changed "
        "shape — re-verify the SC-1 hardening still covers every python invocation."
    )
