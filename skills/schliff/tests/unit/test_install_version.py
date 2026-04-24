"""Tests for install.sh VERSION extraction portability (UR-001).

Regression: install.sh previously used ``grep -E '^version\\s*='`` for VERSION
extraction. ``\\s`` is a GNU grep extension; macOS ships BSD grep at
``/usr/bin/grep`` which interprets ``\\s`` literally as the character 's',
causing the match to silently fail. Result: installer printed
``Schliff v unknown Installer`` on every macOS user's first run.

The fix uses the POSIX character class ``[[:space:]]`` which is portable
across BSD and GNU grep.

These tests codify that install.sh must not regress back into GNU-only escape
sequences, and verify end-to-end extraction against the platform grep.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
INSTALL_SH = REPO_ROOT / "install.sh"
PYPROJECT = REPO_ROOT / "pyproject.toml"

# Shipped shell scripts that also run ``grep -E`` against user-authored content.
# Each must stay POSIX-portable (see beyond-diff audit for UR-001).
SHIPPED_SHELL_SCRIPTS = [
    REPO_ROOT / "install.sh",
    REPO_ROOT / "skills" / "schliff" / "scripts" / "analyze-skill.sh",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_version_grep_line(install_sh_text: str) -> str:
    """Locate the VERSION-extraction grep line in install.sh."""
    for raw in install_sh_text.splitlines():
        if "VERSION=" in raw and "grep" in raw and "pyproject" in raw:
            return raw
    raise AssertionError(
        "Could not locate VERSION-extraction grep line in install.sh. "
        "Expected a line matching 'VERSION=$(grep -E ... pyproject.toml ...)'."
    )


# ---------------------------------------------------------------------------
# Static pattern check — portable across all test runners
# ---------------------------------------------------------------------------

def test_install_sh_version_grep_has_no_gnu_only_escapes():
    """install.sh VERSION regex must not use GNU-only escape sequences.

    GNU grep extensions (``\\s``, ``\\d``, ``\\w``, ``\\b``, their uppercase
    complements) all silently fail on BSD grep — the pattern still parses,
    matches nothing, and ``VERSION`` falls through to ``"unknown"``. Use POSIX
    character classes (``[[:space:]]``, ``[[:digit:]]`` etc.) instead.
    """
    line = _find_version_grep_line(INSTALL_SH.read_text())
    gnu_only = [r"\s", r"\S", r"\d", r"\D", r"\w", r"\W", r"\b", r"\B"]
    offenders = [esc for esc in gnu_only if esc in line]
    assert not offenders, (
        f"install.sh VERSION grep uses GNU-only escape(s) {offenders} that "
        f"silently fail on BSD grep (macOS /usr/bin/grep). Replace with a "
        f"POSIX character class such as [[:space:]].\n"
        f"Offending line: {line.strip()!r}"
    )


# ---------------------------------------------------------------------------
# End-to-end extraction against the platform grep
# ---------------------------------------------------------------------------

def test_install_sh_pattern_matches_with_platform_grep():
    """The exact pattern from install.sh must match against pyproject.toml
    when invoked via ``/usr/bin/grep`` (BSD on macOS, GNU on Linux).

    Pre-fix on macOS: BSD grep treats ``\\s`` as literal 's' -> match fails
    -> VERSION="unknown" -> installer prints "Schliff v unknown Installer".
    Post-fix: ``[[:space:]]*`` matches on both platforms.
    """
    if not Path("/usr/bin/grep").exists():
        pytest.skip("/usr/bin/grep not available on this system")

    line = _find_version_grep_line(INSTALL_SH.read_text())
    match = re.search(r"grep -E '([^']+)'", line)
    assert match, f"Could not parse grep -E pattern from: {line.strip()!r}"
    pattern = match.group(1)

    result = subprocess.run(
        ["/usr/bin/grep", "-E", pattern, str(PYPROJECT)],
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode == 0, (
        f"/usr/bin/grep failed to match install.sh VERSION pattern "
        f"{pattern!r} against pyproject.toml. On macOS /usr/bin/grep is BSD "
        f"grep which does not support GNU escapes like \\s. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "version" in result.stdout.lower(), (
        f"grep matched but output does not contain 'version': {result.stdout!r}"
    )


@pytest.mark.parametrize("script_path", SHIPPED_SHELL_SCRIPTS, ids=lambda p: p.name)
def test_shipped_shell_script_has_no_gnu_only_grep_escapes(script_path):
    """Beyond-diff guard: all shipped shell scripts that call ``grep -E`` must
    stay POSIX-portable. GNU extensions (``\\s``, ``\\d``, ``\\w``, ``\\b`` and
    their uppercase complements) silently fail on classic BSD grep and produce
    wrong output instead of errors — the hardest class of portability bug.

    Scan extracts only ``grep`` / ``egrep`` command lines so unrelated use of
    backslash in other shell constructs is ignored.
    """
    if not script_path.exists():
        pytest.skip(f"{script_path} not present in this checkout")

    gnu_only = [r"\s", r"\S", r"\d", r"\D", r"\w", r"\W", r"\b", r"\B"]
    offenders: list[tuple[int, str, list[str]]] = []
    for lineno, raw in enumerate(script_path.read_text().splitlines(), start=1):
        stripped = raw.strip()
        if stripped.startswith("#"):
            continue
        if "grep" not in stripped and "egrep" not in stripped:
            continue
        found = [esc for esc in gnu_only if esc in raw]
        if found:
            offenders.append((lineno, raw.strip(), found))

    assert not offenders, (
        f"{script_path.relative_to(REPO_ROOT)} uses GNU-only escapes in "
        f"grep invocations — these silently fail on BSD grep. Replace with "
        f"POSIX character classes (e.g. [[:space:]] for \\s, [[:digit:]] for "
        f"\\d).\nOffenders:\n"
        + "\n".join(f"  L{lineno}: {escapes}  |  {line}" for lineno, line, escapes in offenders)
    )


def test_install_sh_header_does_not_print_unknown_version():
    """Run install.sh --help on the current platform and verify the header
    prints a concrete version, not 'unknown'.

    This is the final user-visible integration check. Requires bash and
    whatever grep ``install.sh`` picks up via PATH — whichever grep macOS or
    Linux users actually have. Skips if bash is unavailable.
    """
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not found on PATH")

    # --help exits with 0 and prints the header before any install action.
    env = os.environ.copy()
    result = subprocess.run(
        [bash, str(INSTALL_SH), "--help"],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        cwd=str(REPO_ROOT),
    )

    assert result.returncode == 0, (
        f"install.sh --help exited with {result.returncode}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "Schliff v" in result.stdout, (
        f"install.sh --help did not print a Schliff version header:\n"
        f"{result.stdout}"
    )
    assert "Schliff v unknown" not in result.stdout, (
        f"install.sh --help printed 'Schliff v unknown' — VERSION extraction "
        f"regressed. This is what UR-001 fixed; see install.sh grep line.\n"
        f"Full stdout:\n{result.stdout}"
    )
