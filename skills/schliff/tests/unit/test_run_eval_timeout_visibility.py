"""`run-eval.sh`'s 2-second ReDoS guard is best-effort, and its absence was silent.

`_GREP_TIMEOUT` is set only when `gtimeout` or `timeout` resolves on PATH. Neither is
present on a stock macOS, so there the guard is inert AND its `124) pattern timed out`
branch is dead code — with nothing in the output saying so. A guard you cannot tell apart
from a working one is worse than a documented absence.

Scope, measured rather than assumed: the sink does not backtrack. GNU grep, BSD grep 2.6.0
and ugrep 7.5.0 are all DFA-based and stayed flat (0.044-0.050s) on the patterns
`validate_regex_complexity` accepts (`a*a*a*...b`, `a{1,10}{1,10}b`, `(\\w+\\s?)*$`). So
this is defence in depth, not a live hole — which is exactly why the fix is a warning and
NOT a portable Python fallback. Swapping ERE for Python `re` is what left six assertions
dead on CI for months (see tests/unit/test_eval_suite_is_portable_ere.py).

Both directions are pinned, and neither depends on which machine runs the suite. One test
asserts the warning appears if and only if a timeout binary resolves HERE — the real
decision on the real platform. A second supplies a shim `timeout` on PATH, because the
first only ever exercises one branch per machine: locally both binaries are absent, so a
mutation that warns unconditionally would be invisible without it.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
_RUN_EVAL = _SCRIPTS / "run-eval.sh"

_TIMEOUT_BINARIES = ("gtimeout", "timeout")


def _timeout_binary_available() -> bool:
    return any(shutil.which(b) for b in _TIMEOUT_BINARIES)


@pytest.fixture
def sandbox(tmp_path: Path):
    """A skill plus suite in tmp_path, with HOME redirected.

    run-eval.sh writes to three roots: `<skill dir>/.schliff-eval`, `<skill dir>/.schliff`
    and `${HOME}/.schliff/meta`. The first two are contained by putting the skill in
    tmp_path; the third needs HOME overridden, or a test run appends to the real
    calibration log. A test that shells out to the product inherits the product's writes.
    """
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\nname: probe\ndescription: Use when probing. Trigger on probe.\n---\n\n"
        "# Probe\n\nRun `make build` to build.\n",
        encoding="utf-8")
    suite = tmp_path / "eval-suite.json"
    suite.write_text(json.dumps({
        "test_cases": [{
            "id": "tc1",
            "prompt": "probe",
            "assertions": [
                {"type": "contains", "value": "Probe", "description": "has the heading"},
                {"type": "pattern", "value": "make build", "description": "names the build"},
            ],
        }],
    }), encoding="utf-8")
    return skill, suite, tmp_path


def _run(sandbox):
    skill, suite, home = sandbox
    return subprocess.run(
        ["bash", str(_RUN_EVAL), str(skill), str(suite), "--no-runtime-auto"],
        capture_output=True, text=True, cwd=str(home),
        env={"HOME": str(home), "PATH": __import__("os").environ["PATH"]},
    )


def test_missing_timeout_binary_is_announced(sandbox):
    """The whole point: an inert guard must say so."""
    result = _run(sandbox)
    announced = "regex timeout guard" in result.stderr.lower()
    if _timeout_binary_available():
        assert not announced, (
            f"a timeout binary resolves here ({[b for b in _TIMEOUT_BINARIES if shutil.which(b)]}), "
            f"so the guard is active and must not warn:\n{result.stderr}"
        )
    else:
        assert announced, (
            "neither gtimeout nor timeout resolves here, so the 2s guard is inert and its "
            "`124)` branch is dead code — that must be visible in the output, not silent.\n"
            f"stderr was:\n{result.stderr}"
        )


def test_no_warning_when_a_timeout_binary_is_present(sandbox, tmp_path):
    """The other direction, made testable on ANY platform.

    The if-and-only-if test above only exercises one branch per machine: locally both
    binaries are absent, so a mutation that warns unconditionally is indistinguishable
    there. Supplying a shim `timeout` on PATH pins the "guard active -> stays quiet"
    direction everywhere, so neither branch depends on which machine runs the suite.
    """
    import os
    skill, suite, home = sandbox
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    shim = shim_dir / "timeout"
    # Drops the duration and execs the rest, so the run behaves normally.
    shim.write_text("#!/bin/sh\nshift\nexec \"$@\"\n", encoding="utf-8")
    shim.chmod(0o755)

    result = subprocess.run(
        ["bash", str(_RUN_EVAL), str(skill), str(suite), "--no-runtime-auto"],
        capture_output=True, text=True, cwd=str(home),
        env={"HOME": str(home), "PATH": f"{shim_dir}:{os.environ['PATH']}"},
    )
    assert "regex timeout guard" not in result.stderr.lower(), (
        f"a timeout binary is on PATH, so the guard is active and the note must not "
        f"appear:\n{result.stderr}"
    )
    payload = json.loads(result.stdout)
    assert payload["pass_rate"]["total"] == 2, result.stdout


def test_the_run_still_succeeds_either_way(sandbox):
    """The warning is a note, not a failure: assertions must still be evaluated."""
    result = _run(sandbox)
    payload = json.loads(result.stdout)
    assert payload["pass_rate"]["total"] == 2, result.stdout
    assert payload["pass_rate"]["errored"] == 0, result.stdout


def test_nothing_was_written_outside_the_sandbox(sandbox):
    """Guards the fixture itself — if HOME leaked, this test is measuring the real home."""
    _skill, _suite, home = sandbox
    _run(sandbox)
    real_meta = Path.home() / ".schliff" / "meta" / "calibration-log.jsonl"
    before = real_meta.stat().st_mtime if real_meta.exists() else None
    _run(sandbox)
    after = real_meta.stat().st_mtime if real_meta.exists() else None
    assert before == after, (
        "run-eval.sh wrote to the real calibration log — HOME is not contained by the "
        "fixture, so every other assertion here is measuring the wrong environment"
    )
