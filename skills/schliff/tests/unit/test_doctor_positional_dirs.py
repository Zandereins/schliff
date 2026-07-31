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


# ---------------------------------------------------------------------------
# A directory the user NAMED must exist. Defaults must stay optional.
# ---------------------------------------------------------------------------

def test_missing_named_dir_is_an_error():
    """A typo'd path currently reports "No skills found" and exits 0.

    Indistinguishable from an empty directory, so a CI gate cannot catch the
    typo — and the report then lists the DEFAULT scan dirs it did not use.
    `verify` already errors on a missing file; `doctor` must not disagree.
    """
    proc = _run("/nope/definitely/not/here")
    assert proc.returncode != 0, (
        "a non-existent directory exited 0 — a typo is silently a clean run"
    )
    assert "not/here" in (proc.stderr + proc.stdout)


def test_named_path_that_is_a_file_is_an_error(tmp_path: Path):
    proc = _run(str(tmp_path / "notadir.md"))
    assert proc.returncode != 0


def test_existing_file_passed_as_dir_is_an_error(tmp_path: Path):
    f = tmp_path / "SKILL.md"
    f.write_text("# hi\n", encoding="utf-8")
    proc = _run(str(f))
    assert proc.returncode != 0, "a regular file was accepted as a scan directory"


def test_flag_form_is_validated_too(tmp_path: Path):
    proc = _run("--skill-dirs", str(tmp_path / "gone"))
    assert proc.returncode != 0


def test_default_dirs_are_NOT_validated():
    """Counter-test — the half that must not change.

    With no argument, doctor scans built-in defaults; `.claude/skills` legitimately
    does not exist in most repos. Validating those would break the no-arg case,
    which is the most common invocation.
    """
    proc = _run()
    assert proc.returncode == 0, (
        f"no-arg doctor regressed to exit {proc.returncode}: {proc.stderr.strip()[:300]}"
    )
