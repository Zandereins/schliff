"""Tests for scripts/collect-traffic.sh (plugin-channel-experiment collector).

This test suite never invokes ``gh`` and never touches the network — it only
inspects the script's own source (for the same POSIX-grep-portability rule
UR-001 established in test_install_version.py) and the already-seeded
docs/experiments/plugin-channel/traffic.jsonl baseline line on disk.

Portability check: rather than duplicating the GNU-only-escape scan logic,
this reuses ``_scan_shell_script_for_gnu_only_grep_escapes`` from
test_install_version.py and adds collect-traffic.sh to that module's shared
``SHIPPED_SHELL_SCRIPTS`` list. That list already drives a parametrized test
that sweeps every shipped shell script, so extending it is what actually
wires collect-traffic.sh into the existing regression guard instead of
maintaining a second, easily-forgotten copy of the same rule.
"""
import json
from pathlib import Path

from test_install_version import (
    SHIPPED_SHELL_SCRIPTS,
    _scan_shell_script_for_gnu_only_grep_escapes,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
COLLECT_TRAFFIC_SH = REPO_ROOT / "scripts" / "collect-traffic.sh"
TRAFFIC_JSONL = REPO_ROOT / "docs" / "experiments" / "plugin-channel" / "traffic.jsonl"


# ---------------------------------------------------------------------------
# POSIX grep/sed portability (UR-001 rule, applied to the new script)
# ---------------------------------------------------------------------------

def test_collect_traffic_sh_is_registered_as_a_shipped_shell_script():
    """collect-traffic.sh must be covered by the shared portability sweep.

    Missing from SHIPPED_SHELL_SCRIPTS means the parametrized test in
    test_install_version.py silently never looks at this file.
    """
    assert COLLECT_TRAFFIC_SH in SHIPPED_SHELL_SCRIPTS, (
        "scripts/collect-traffic.sh is not in test_install_version."
        "SHIPPED_SHELL_SCRIPTS, so it is not covered by the GNU-only-grep-"
        "escape regression sweep (UR-001)."
    )


def test_collect_traffic_sh_has_no_gnu_only_grep_escapes():
    """Direct check on collect-traffic.sh itself (belt-and-suspenders)."""
    assert COLLECT_TRAFFIC_SH.exists(), f"{COLLECT_TRAFFIC_SH} not found"
    offenders = _scan_shell_script_for_gnu_only_grep_escapes(COLLECT_TRAFFIC_SH)
    assert not offenders, (
        f"collect-traffic.sh uses GNU-only grep escapes that silently fail "
        f"on BSD grep (macOS /usr/bin/grep): {offenders}"
    )


def test_collect_traffic_sh_fails_loudly_without_gh():
    """Script must set -euo pipefail and check for gh explicitly."""
    text = COLLECT_TRAFFIC_SH.read_text()
    assert "set -euo pipefail" in text
    assert "command -v gh" in text
    assert "gh auth status" in text


def test_collect_traffic_sh_never_overwrites_a_baseline_line():
    """The per-day dedup must exempt lines carrying "note":"baseline".

    A live run can land on the same UTC date as the seeded baseline (it did,
    on 2026-08-11 itself). Without this exemption the very first live run
    would silently replace the seeded historical anchor.
    """
    text = COLLECT_TRAFFIC_SH.read_text()
    assert '\\"note\\":\\"baseline\\"' in text, (
        "collect-traffic.sh does not appear to special-case baseline lines "
        "in its per-day dedup logic"
    )


# ---------------------------------------------------------------------------
# Seeded baseline
# ---------------------------------------------------------------------------

def test_traffic_jsonl_exists_and_every_line_parses():
    assert TRAFFIC_JSONL.exists(), f"{TRAFFIC_JSONL} not found"
    lines = [ln for ln in TRAFFIC_JSONL.read_text().splitlines() if ln.strip()]
    assert lines, "traffic.jsonl has no lines"
    for ln in lines:
        json.loads(ln)  # must not raise


def test_traffic_jsonl_contains_the_seeded_baseline_line():
    lines = [ln for ln in TRAFFIC_JSONL.read_text().splitlines() if ln.strip()]
    baseline_lines = [json.loads(ln) for ln in lines if json.loads(ln).get("note") == "baseline"]
    assert len(baseline_lines) == 1, (
        f"expected exactly one baseline-tagged line, found {len(baseline_lines)}"
    )
    baseline = baseline_lines[0]
    assert baseline["collected_at"].startswith("2026-08-11")
    for key in ("views", "clones", "referrers", "paths", "repo"):
        assert key in baseline, f"baseline line missing '{key}' key"
    assert baseline["repo"] == {"forks": 1, "stars": 13, "watchers": 0}
