"""The ReDoS gate's self-check moved to a monitor; this keeps it from moving further.

`test_the_gate_still_fires_on_the_real_defect_class` is load-dependent, so every
required path deselects the `gate_power` marker and `gate-power.yml` runs it without
blocking (docs/specs/2026-07-30-redos-audit-fixes.md, D6, 2026-09-30). The gate's
threshold and `_ratio` stay checked in the required jobs by a deterministic test.

This guards against the accidental ways the split could drift: the monitor stops
running the self-check, the marker spreads to the gate, or a required path drops
tests by an option or a new entry point. It is not a defence against a determined
edit; a change to these files is visible in review.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # unit→tests→schliff→skills→repo root
TESTS = ROOT / "skills" / "schliff" / "tests"
WORKFLOWS = ROOT / ".github" / "workflows"

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
# Ways to drop tests that do not show in an invocation's own text.
FORBIDDEN = ("PYTEST_ADDOPTS", "addopts", "--deselect", "--ignore", " -k ")


def _entry_points() -> list:
    return sorted(WORKFLOWS.glob("*.y*ml")) + [ROOT / "Makefile", ROOT / "pyproject.toml"]


def test_every_pytest_invocation_is_the_expected_one():
    found = {}
    for path in _entry_points():
        # Drop comments: YAML `#` lines and the Makefile's `## help` text.
        text = re.sub(r"\s##.*", "", path.read_text(encoding="utf-8"))
        lines = [
            line for line in text.splitlines()
            if re.search(r"\bpytest\b", line) and not re.search(r"pip install|^\s*#|pytest\.ini_options", line)
        ]
        runs = []
        for line in lines:
            match = re.search(r"\S*(?:python[\d.]*\s+-m\s+)?pytest\b[^;\n]*", line)
            if match and ("tests" in match.group(0) or "-m pytest" in match.group(0)):
                runs.append(match.group(0).strip())
        if runs:
            found[path.relative_to(ROOT).as_posix()] = runs
    assert found == EXPECTED


def test_no_entry_point_drops_tests_out_of_band():
    hits = [
        f"{path.relative_to(ROOT)}: {token.strip()}"
        for path in _entry_points()
        for token in FORBIDDEN
        if token in path.read_text(encoding="utf-8")
    ]
    assert not hits, hits


def test_the_marker_sits_on_the_self_check_and_nowhere_else():
    uses = []
    for path in sorted(TESTS.rglob("*.py")):
        if path.name == Path(__file__).name:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if "gate_power" in line and "mark" in line:
                following = next((ln for ln in lines[i + 1:] if ln.strip().startswith("def ")), "")
                uses.append((path.relative_to(TESTS).as_posix(), following.strip()))
    assert uses == [(
        "unit/test_patterns_scale_linearly.py",
        "def test_the_gate_still_fires_on_the_real_defect_class():",
    )], uses
