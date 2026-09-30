"""The ReDoS gate's self-check moved to a monitor; this keeps it from moving further.

`test_the_gate_still_fires_on_the_real_defect_class` is load-dependent, so the
required jobs deselect the `gate_power` marker and `gate-power.yml` runs it without
blocking a merge (docs/specs/2026-07-30-redos-audit-fixes.md, D6, 2026-09-30).
Two silent failures are possible, and each is a red here:

- the monitor stops running the self-check, so its blindness rate is never reported;
- the marker spreads to the gate itself, so it leaves the required jobs with
  nothing red to show for it.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # unit→tests→schliff→skills→repo root
SELF_CHECK = "tests/unit/test_patterns_scale_linearly.py::test_the_gate_still_fires_on_the_real_defect_class"


def _unit_invocations(workflow: str) -> list:
    text = (ROOT / ".github" / "workflows" / workflow).read_text(encoding="utf-8")
    return re.findall(r"python3 -m pytest tests/unit/.*", text)


def test_the_marker_selects_the_self_check_and_nothing_else():
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit/", "-m", "gate_power", "--collect-only", "-q"],
        cwd=ROOT / "skills" / "schliff", capture_output=True, text=True, check=False,
    ).stdout
    selected = [line for line in out.splitlines() if "::" in line]
    # Node ids are relative to pytest's rootdir, which depends on where it is
    # invoked from, so compare the part below skills/schliff.
    assert len(selected) == 1 and selected[0].endswith(SELF_CHECK), f"`-m gate_power` selects {selected}"


def test_every_required_unit_run_deselects_only_the_monitor():
    runs = _unit_invocations("test.yml")
    assert len(runs) == 2, f"expected the ubuntu and macOS unit runs, found {runs}"
    for run in runs:
        assert '-m "not gate_power"' in run, f"a required unit run no longer deselects the monitor: {run}"
        options = run.split("tests/unit/", 1)[1]
        assert options.count("-m ") == 1, f"a required unit run deselects more than the monitor: {run}"


def test_the_monitor_runs_the_self_check():
    runs = _unit_invocations("gate-power.yml")
    assert runs == ["python3 -m pytest tests/unit/ -m gate_power -v"], runs
