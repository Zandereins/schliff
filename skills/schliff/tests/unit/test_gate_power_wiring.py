"""The ReDoS gate's self-check moved to a monitor; this keeps it from moving further.

`test_the_gate_still_fires_on_the_real_defect_class` is load-dependent, so every
required path deselects the `gate_power` marker and `gate-power.yml` runs it without
blocking (docs/specs/2026-07-30-redos-audit-fixes.md, D6, 2026-09-30). The gate's
logic stays checked in the required jobs by a deterministic test. Three silent
failures are possible, and each is a red here:

- the monitor stops running the self-check, so its blindness rate is never reported;
- the marker spreads to the gate itself, so the gate leaves the required jobs;
- a required path drops tests some other way (`-k`, `--deselect`, `--ignore`) or a
  new entry point runs the unit suite unfiltered.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # unit→tests→schliff→skills→repo root
SELF_CHECK = "tests/unit/test_patterns_scale_linearly.py::test_the_gate_still_fires_on_the_real_defect_class"

REQUIRED_V = 'python3 -m pytest tests/unit/ -m "not gate_power" -v'
REQUIRED_Q = 'python3 -m pytest tests/unit/ -m "not gate_power" -q'
# Every pytest invocation in CI and in the Makefile, exactly. A new one, or an
# extra option on an existing one, has to be added here on purpose.
EXPECTED = {
    ".github/workflows/gate-power.yml": ["python3 -m pytest tests/unit/ -m gate_power -v"],
    ".github/workflows/publish.yml": [REQUIRED_Q],
    ".github/workflows/test.yml": [REQUIRED_V, REQUIRED_Q],
    "Makefile": ['/usr/bin/python3 -m pytest skills/schliff/tests -m "not gate_power" -q'],
}


def _pytest_invocations() -> dict:
    files = sorted((ROOT / ".github" / "workflows").glob("*.yml")) + [ROOT / "Makefile"]
    found = {}
    for path in files:
        runs = re.findall(r"\S*python3? -m pytest[^;\n]*", path.read_text(encoding="utf-8"))
        if runs:
            found[path.relative_to(ROOT).as_posix()] = [run.strip() for run in runs]
    return found


def test_every_pytest_invocation_is_the_expected_one():
    assert _pytest_invocations() == EXPECTED


def test_the_marker_selects_the_self_check_and_nothing_else():
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit/", "-m", "gate_power", "--collect-only", "-q"],
        cwd=ROOT / "skills" / "schliff", capture_output=True, text=True, check=False,
    ).stdout
    selected = [line for line in out.splitlines() if "::" in line]
    # Node ids are relative to pytest's rootdir, which depends on where it is
    # invoked from, so compare the part below skills/schliff.
    assert len(selected) == 1 and selected[0].endswith(SELF_CHECK), f"`-m gate_power` selects {selected}"
