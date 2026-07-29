"""`schliff doctor <dir>` must work — it is what people actually type.

schliff's only verified external adopter documented `uvx schliff doctor <dir>` as his
step 1. It exited 2 with "unrecognized arguments" for 132 days, because the directory
was only reachable through `--skill-dirs`. Positional dirs are now an alias.

Giving both forms is refused rather than merged: a silent union would make the scanned
set depend on argument order, and a scanner whose scope is ambiguous is worse than one
that says no.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_PARENT = Path(__file__).resolve().parents[2]
CARD = SCRIPTS_PARENT / "SKILL.md"


def _run(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "scripts.cli", "doctor", *argv],
        cwd=SCRIPTS_PARENT, capture_output=True, text=True, timeout=180,
    )


@pytest.fixture
def skill_dir(tmp_path: Path) -> Path:
    (tmp_path / "SKILL.md").write_text(CARD.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_positional_dir_is_accepted(skill_dir: Path):
    """The adopter's documented step 1."""
    proc = _run(str(skill_dir))
    assert proc.returncode == 0, (
        f"`schliff doctor <dir>` failed (exit {proc.returncode}): {proc.stderr.strip()[:300]}"
    )
    assert "unrecognized arguments" not in proc.stderr


def test_positional_and_flag_agree(skill_dir: Path):
    """The alias must scan the same set, not merely not crash."""
    positional = _run(str(skill_dir), "--json")
    flagged = _run("--skill-dirs", str(skill_dir), "--json")
    assert positional.returncode == flagged.returncode == 0
    assert positional.stdout == flagged.stdout, "positional and --skill-dirs diverged"


def test_both_forms_at_once_is_refused(skill_dir: Path):
    """Ambiguous scope is an error, never a silent union."""
    proc = _run(str(skill_dir), "--skill-dirs", str(skill_dir))
    assert proc.returncode == 2
    assert "not both" in proc.stderr


def test_bare_doctor_still_scans_installed_skills():
    """No argument keeps its original meaning."""
    assert _run().returncode == 0
