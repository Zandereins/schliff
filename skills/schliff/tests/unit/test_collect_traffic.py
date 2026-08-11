"""Tests for scripts/collect-traffic.sh (plugin-channel-experiment collector).

This test suite never invokes the real ``gh`` CLI and never touches the
network. Instead, most tests copy the real script into an isolated tmp
REPO_ROOT and put a stub ``gh`` executable first on PATH, then run the real
script via ``bash`` and inspect what it actually did — the dedup/overwrite
path, the baseline exemption, and both fail-loud exits are all exercised end
to end. Only the "do not invoke gh" constraint from the brief is about the
network call; running the script itself against a stub is exactly what the
brief's "make the behaviour visible in the test" requirement asks for.

The remaining tests inspect the shared portability rule (UR-001) and the
already-seeded docs/experiments/plugin-channel/traffic.jsonl baseline line
on disk, neither of which needs to run the script.
"""
import json
import os
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from test_install_version import (
    SHIPPED_SHELL_SCRIPTS,
    _scan_shell_script_for_gnu_only_grep_escapes,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
COLLECT_TRAFFIC_SH = REPO_ROOT / "scripts" / "collect-traffic.sh"
TRAFFIC_JSONL = REPO_ROOT / "docs" / "experiments" / "plugin-channel" / "traffic.jsonl"

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Stub `gh` CLI: answers `gh auth status` and `gh api ...` with canned,
# offline data so collect-traffic.sh can be run for real without any
# network access. GH_STUB_AUTH_EXIT lets a test simulate "unauthenticated".
GH_STUB = """#!/bin/sh
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit "${GH_STUB_AUTH_EXIT:-0}"
fi
if [ "$1" = "api" ]; then
  case "$*" in
    *traffic/views*)
      printf '%s' '{"count":1,"uniques":1,"views":[]}'
      ;;
    *traffic/clones*)
      printf '%s' '{"count":2,"uniques":2,"clones":[]}'
      ;;
    *traffic/popular/referrers*)
      printf '%s' '[]'
      ;;
    *traffic/popular/paths*)
      printf '%s' '[]'
      ;;
    *)
      printf '%s' '{"stargazers_count":99,"forks_count":9,"subscribers_count":1}'
      ;;
  esac
  exit 0
fi
exit 1
"""


def _make_sandbox(tmp_path, auth_exit=0, with_gh=True):
    """Isolated REPO_ROOT: a copy of the real script under scripts/, plus
    (optionally) a stub `gh` first on PATH. Returns (script_copy, out_file, env).
    """
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True)
    script_copy = scripts_dir / "collect-traffic.sh"
    script_copy.write_text(COLLECT_TRAFFIC_SH.read_text())
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IEXEC)

    env = os.environ.copy()
    if with_gh:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        gh_stub = bin_dir / "gh"
        gh_stub.write_text(GH_STUB)
        gh_stub.chmod(gh_stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
    else:
        # Deliberately no gh anywhere on PATH.
        env["PATH"] = "/usr/bin:/bin"
    env["GH_STUB_AUTH_EXIT"] = str(auth_exit)

    out_file = repo_root / "docs" / "experiments" / "plugin-channel" / "traffic.jsonl"
    return script_copy, out_file, env


def _run(script_copy, env):
    return subprocess.run(
        ["bash", str(script_copy)],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


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


# ---------------------------------------------------------------------------
# Real execution against a stub `gh` — no network, but the actual script runs
# ---------------------------------------------------------------------------

def test_collect_traffic_sh_exits_nonzero_without_gh(tmp_path):
    script_copy, out_file, env = _make_sandbox(tmp_path, with_gh=False)
    result = _run(script_copy, env)
    assert result.returncode != 0, "script must fail loudly when gh is missing"
    assert "gh" in result.stderr.lower()
    assert not out_file.exists(), "no output should be written when gh is missing"


def test_collect_traffic_sh_exits_nonzero_when_unauthenticated(tmp_path):
    script_copy, out_file, env = _make_sandbox(tmp_path, auth_exit=1)
    result = _run(script_copy, env)
    assert result.returncode != 0, "script must fail loudly when gh is unauthenticated"
    assert "gh" in result.stderr.lower()
    assert not out_file.exists(), "no output should be written when unauthenticated"


def test_collect_traffic_sh_first_run_appends_one_valid_line(tmp_path):
    script_copy, out_file, env = _make_sandbox(tmp_path)
    result = _run(script_copy, env)
    assert result.returncode == 0, result.stderr

    lines = [ln for ln in out_file.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1
    obj = json.loads(lines[0])  # must parse
    assert obj["collected_at"].startswith(TODAY)
    for key in ("views", "clones", "referrers", "paths", "repo"):
        assert key in obj


def test_collect_traffic_sh_is_idempotent_same_day(tmp_path):
    """Running twice on the same day must not append a second line."""
    script_copy, out_file, env = _make_sandbox(tmp_path)

    first = _run(script_copy, env)
    assert first.returncode == 0, first.stderr
    first_lines = [ln for ln in out_file.read_text().splitlines() if ln.strip()]
    assert len(first_lines) == 1
    first_timestamp = json.loads(first_lines[0])["collected_at"]

    second = _run(script_copy, env)
    assert second.returncode == 0, second.stderr
    second_lines = [ln for ln in out_file.read_text().splitlines() if ln.strip()]

    assert len(second_lines) == 1, (
        f"expected exactly 1 line after two same-day runs, got {len(second_lines)}: "
        f"{second_lines}"
    )
    second_timestamp = json.loads(second_lines[0])["collected_at"]
    # Overwrite-in-place means the timestamp is refreshed, not frozen.
    assert second_timestamp >= first_timestamp


def test_collect_traffic_sh_never_overwrites_a_baseline_line(tmp_path):
    """A baseline line dated today must survive a same-day live run untouched,
    and the live run must land as a second, separate line rather than
    merging into or replacing the baseline.
    """
    script_copy, out_file, env = _make_sandbox(tmp_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    baseline_line = json.dumps(
        {
            "collected_at": f"{TODAY}T00:00:00Z",
            "views": {"count": 0},
            "clones": {"count": 0},
            "referrers": [],
            "paths": [],
            "repo": {"stargazers_count": 0, "forks_count": 0, "subscribers_count": 0},
            "note": "baseline",
        },
        separators=(",", ":"),
    )
    out_file.write_text(baseline_line + "\n")

    result = _run(script_copy, env)
    assert result.returncode == 0, result.stderr

    lines = [ln for ln in out_file.read_text().splitlines() if ln.strip()]
    assert len(lines) == 2, f"expected baseline + 1 live line, got {len(lines)}: {lines}"

    parsed = [json.loads(ln) for ln in lines]
    baseline_survivors = [o for o in parsed if o.get("note") == "baseline"]
    assert len(baseline_survivors) == 1
    assert baseline_survivors[0] == json.loads(baseline_line), (
        "the seeded baseline line must be byte-for-byte unchanged"
    )

    live_lines = [o for o in parsed if o.get("note") != "baseline"]
    assert len(live_lines) == 1
    assert live_lines[0]["collected_at"].startswith(TODAY)

    # Running again the same day must still not duplicate the live line.
    result2 = _run(script_copy, env)
    assert result2.returncode == 0, result2.stderr
    lines2 = [ln for ln in out_file.read_text().splitlines() if ln.strip()]
    assert len(lines2) == 2, f"expected baseline + 1 live line after 2nd run, got {len(lines2)}"


# ---------------------------------------------------------------------------
# Seeded baseline (static inspection, no script execution needed)
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
    # Same schema the script itself produces (see
    # test_traffic_jsonl_repo_schema_is_consistent_across_lines below) — the
    # raw baseline capture used gh repo view's {forks,stars,watchers} field
    # names; these were normalized to gh api's {forks_count,stargazers_count,
    # subscribers_count} so every line in the file shares one repo schema.
    assert baseline["repo"] == {
        "stargazers_count": 13,
        "forks_count": 1,
        "subscribers_count": 0,
    }


def test_traffic_jsonl_repo_schema_is_consistent_across_lines():
    """Every line's `repo` object must use the same key set as the script
    produces (stargazers_count/forks_count/subscribers_count), including the
    seeded baseline. A schema-inconsistent file lets a later reader parse
    `repo.*` successfully on some lines and get KeyErrors on others.
    """
    expected_keys = {"stargazers_count", "forks_count", "subscribers_count"}
    lines = [ln for ln in TRAFFIC_JSONL.read_text().splitlines() if ln.strip()]
    for i, ln in enumerate(lines):
        obj = json.loads(ln)
        assert set(obj["repo"].keys()) == expected_keys, (
            f"line {i} has repo keys {sorted(obj['repo'].keys())}, "
            f"expected {sorted(expected_keys)}"
        )
