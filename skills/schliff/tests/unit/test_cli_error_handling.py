"""CLI error-handling — no raw tracebacks on user-triggerable error paths.

Before these fixes, ``schliff score`` printed full Python tracebacks on
common user mistakes (passing a directory, passing an oversized file). The
CLI must instead exit with a non-zero status and a short, readable error
message on stderr — and crucially, nothing on stdout should suggest a
successful run.

Covers both the source-of-truth fix in ``shared.read_skill_safe`` (explicit
``is_dir`` check with a helpful ValueError) and the CLI top-level handler
that catches ``OSError``/``ValueError`` and renders them without stack.
"""
import subprocess
import sys
from pathlib import Path

import pytest

CLI_PATH = str(Path(__file__).resolve().parent.parent.parent / "scripts" / "cli.py")
REPO_ROOT = Path(__file__).resolve().parents[4]


def _run_cli(*args, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, CLI_PATH, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(REPO_ROOT),
    )


# ---------------------------------------------------------------------------
# Directory passed where a file is expected
# ---------------------------------------------------------------------------

def test_score_on_directory_exits_non_zero():
    """Passing a directory to `schliff score` must not succeed silently.
    Pre-fix: `IsADirectoryError` propagated with a full traceback + RC 1.
    Post-fix: RC is non-zero but the message is terse and on stderr."""
    result = _run_cli("score", str(REPO_ROOT))
    assert result.returncode != 0, (
        f"Expected non-zero exit on directory input; got rc={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_score_on_directory_no_traceback_in_stderr():
    """No Python traceback should leak to the user for this foreseeable
    mistake. Tracebacks start with 'Traceback (most recent call last):'."""
    result = _run_cli("score", str(REPO_ROOT))
    assert "Traceback" not in result.stderr, (
        f"Raw traceback leaked to stderr on directory input:\n{result.stderr}"
    )


def test_score_on_directory_has_helpful_error_message():
    """User should see a short hint that the path is a directory."""
    result = _run_cli("score", str(REPO_ROOT))
    combined = (result.stderr + result.stdout).lower()
    assert "directory" in combined or "not a file" in combined, (
        f"Error message does not identify the path as a directory:\n"
        f"stderr={result.stderr!r}\nstdout={result.stdout!r}"
    )


# ---------------------------------------------------------------------------
# Oversized input
# ---------------------------------------------------------------------------

def test_score_on_oversize_file_exits_non_zero(tmp_path):
    """Files over MAX_SKILL_SIZE must fail cleanly with non-zero RC."""
    big = tmp_path / "big.md"
    big.write_text("x" * 1_100_000, encoding="utf-8")
    result = _run_cli("score", str(big))
    assert result.returncode != 0


def test_score_on_oversize_file_no_traceback_in_stderr(tmp_path):
    """Oversize file should produce a readable message, not a traceback."""
    big = tmp_path / "big.md"
    big.write_text("x" * 1_100_000, encoding="utf-8")
    result = _run_cli("score", str(big))
    assert "Traceback" not in result.stderr, (
        f"Raw traceback leaked to stderr on oversize file:\n{result.stderr}"
    )


def test_score_on_oversize_file_has_helpful_error_message(tmp_path):
    """User should see that the file exceeds the size cap."""
    big = tmp_path / "big.md"
    big.write_text("x" * 1_100_000, encoding="utf-8")
    result = _run_cli("score", str(big))
    combined = (result.stderr + result.stdout).lower()
    assert "exceeds" in combined or "too large" in combined or "size" in combined, (
        f"Error message does not identify the size problem:\n"
        f"stderr={result.stderr!r}\nstdout={result.stdout!r}"
    )


# ---------------------------------------------------------------------------
# read_skill_safe source-of-truth guard
# ---------------------------------------------------------------------------

def test_read_skill_safe_rejects_directory(tmp_path):
    """Direct unit test of the source-of-truth guard. ``read_skill_safe``
    must raise a clear ValueError when handed a directory path (not bubble
    up the cryptic IsADirectoryError from pathlib)."""
    import sys
    scripts_dir = str(Path(__file__).resolve().parent.parent.parent / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from shared import read_skill_safe, invalidate_cache

    invalidate_cache(str(tmp_path))
    with pytest.raises(ValueError, match="directory|not a file"):
        read_skill_safe(str(tmp_path))
