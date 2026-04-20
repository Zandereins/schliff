"""Tests for scoring/runtime.py when enabled=True (TST-003).

Covers the enabled code path that is otherwise unreachable in CI:
1. enabled=True + claude CLI not installed -> graceful skip (score -1)
2. enabled=True + assertions all pass -> score > 0
3. enabled=True + assertions all fail -> score < 50
4. enabled=True + no eval suite -> score -1
5. enabled=True + eval suite without response_* assertions -> score -1
6. enabled=True + claude CLI returns non-zero -> score -1
7. enabled=True + subprocess timeout on invocation -> marked as timeout
"""
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scoring.runtime import score_runtime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MIN_SKILL = """---
name: runtime-test
description: >
  A minimal skill for runtime-path unit testing. Use when exercising
  score_runtime in tests.
---

# Runtime Test Skill

## Instructions
Return the word PASS when invoked.
"""


def _write_skill(tmp_path: Path, content: str = _MIN_SKILL) -> str:
    p = tmp_path / "SKILL.md"
    p.write_text(content, encoding="utf-8")
    return str(p)


def _mock_version_ok():
    """Mock for `claude --version` that succeeds."""
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = "1.0.0"
    mock.stderr = ""
    return mock


def _mock_invocation(response_text: str):
    """Mock for `claude -p ...` invocation."""
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = response_text
    mock.stderr = ""
    return mock


def _eval_suite_passing():
    """Eval suite whose response_contains assertions will pass for 'PASS OK'."""
    return {
        "test_cases": [
            {
                "id": "tc1",
                "prompt": "Invoke the skill",
                "assertions": [
                    {"type": "response_contains", "value": "PASS"},
                    {"type": "response_excludes", "value": "ERROR"},
                ],
            }
        ]
    }


def _eval_suite_failing():
    """Eval suite whose assertions will all fail for response 'unrelated'."""
    return {
        "test_cases": [
            {
                "id": "tc1",
                "prompt": "Invoke the skill",
                "assertions": [
                    {"type": "response_contains", "value": "PASS"},
                    {"type": "response_contains", "value": "MATCH"},
                ],
            }
        ]
    }


# ---------------------------------------------------------------------------
# 1. enabled=True but claude CLI not installed
# ---------------------------------------------------------------------------

def test_enabled_but_claude_cli_missing_returns_skip(tmp_path):
    """FileNotFoundError from subprocess.run -> score -1 (graceful)."""
    skill_path = _write_skill(tmp_path)
    with patch("subprocess.run", side_effect=FileNotFoundError("claude")):
        result = score_runtime(skill_path, eval_suite=_eval_suite_passing(), enabled=True)
    assert result["score"] == -1
    assert "claude_cli_unavailable" in result["issues"]


def test_enabled_but_claude_cli_nonzero_returns_skip(tmp_path):
    """claude --version returncode != 0 -> score -1."""
    skill_path = _write_skill(tmp_path)
    bad = MagicMock()
    bad.returncode = 2
    bad.stdout = ""
    bad.stderr = "unknown error"
    with patch("subprocess.run", return_value=bad):
        result = score_runtime(skill_path, eval_suite=_eval_suite_passing(), enabled=True)
    assert result["score"] == -1
    assert "claude_cli_unavailable" in result["issues"]


def test_enabled_but_version_check_times_out(tmp_path):
    """subprocess.TimeoutExpired on --version check -> score -1."""
    skill_path = _write_skill(tmp_path)
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 5)):
        result = score_runtime(skill_path, eval_suite=_eval_suite_passing(), enabled=True)
    assert result["score"] == -1
    assert "claude_cli_unavailable" in result["issues"]


# ---------------------------------------------------------------------------
# 2. enabled=True + assertions all pass
# ---------------------------------------------------------------------------

def test_enabled_assertions_pass_scores_positive(tmp_path):
    """When every assertion matches, score must be > 0 (in fact 100)."""
    skill_path = _write_skill(tmp_path)
    calls = {"n": 0}

    def fake_run(cmd, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _mock_version_ok()
        return _mock_invocation("PASS OK — all clear")

    with patch("subprocess.run", side_effect=fake_run):
        result = score_runtime(skill_path, eval_suite=_eval_suite_passing(), enabled=True)

    assert result["score"] > 0
    assert result["score"] == 100
    assert result["details"]["passed"] == 2
    assert result["details"]["total"] == 2


# ---------------------------------------------------------------------------
# 3. enabled=True + assertions all fail
# ---------------------------------------------------------------------------

def test_enabled_assertions_fail_scores_below_fifty(tmp_path):
    """When no assertion matches, score must be < 50 (in fact 0)."""
    skill_path = _write_skill(tmp_path)
    calls = {"n": 0}

    def fake_run(cmd, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _mock_version_ok()
        return _mock_invocation("unrelated output")

    with patch("subprocess.run", side_effect=fake_run):
        result = score_runtime(skill_path, eval_suite=_eval_suite_failing(), enabled=True)

    assert result["score"] < 50
    assert result["score"] == 0
    assert any(i.startswith("runtime_pass_rate_low") for i in result["issues"])


# ---------------------------------------------------------------------------
# 4. Graceful skips for missing/empty eval suite
# ---------------------------------------------------------------------------

def test_enabled_no_eval_suite_returns_skip(tmp_path):
    skill_path = _write_skill(tmp_path)
    with patch("subprocess.run", return_value=_mock_version_ok()):
        result = score_runtime(skill_path, eval_suite=None, enabled=True)
    assert result["score"] == -1
    assert "no_eval_suite_for_runtime" in result["issues"]


def test_enabled_empty_test_cases_returns_skip(tmp_path):
    skill_path = _write_skill(tmp_path)
    with patch("subprocess.run", return_value=_mock_version_ok()):
        result = score_runtime(skill_path, eval_suite={"test_cases": []}, enabled=True)
    # test_cases present but no runtime (response_*) assertions
    assert result["score"] == -1
    assert "no_runtime_assertions" in result["issues"]


def test_enabled_no_response_assertions_returns_skip(tmp_path):
    """Eval suite with test_cases but without response_* assertions is skipped."""
    skill_path = _write_skill(tmp_path)
    suite = {
        "test_cases": [
            {
                "id": "tc1",
                "prompt": "x",
                "assertions": [{"type": "file_exists", "value": "README.md"}],
            }
        ]
    }
    with patch("subprocess.run", return_value=_mock_version_ok()):
        result = score_runtime(skill_path, eval_suite=suite, enabled=True)
    assert result["score"] == -1
    assert "no_runtime_assertions" in result["issues"]


# ---------------------------------------------------------------------------
# 5. Invocation timeout path
# ---------------------------------------------------------------------------

def test_enabled_invocation_timeout_marks_timeout(tmp_path):
    """When `claude -p ...` times out, the case is marked 'timeout' and the
    assertions are counted as failures."""
    skill_path = _write_skill(tmp_path)
    calls = {"n": 0}

    def fake_run(cmd, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _mock_version_ok()
        raise subprocess.TimeoutExpired("claude", 60)

    with patch("subprocess.run", side_effect=fake_run):
        result = score_runtime(skill_path, eval_suite=_eval_suite_passing(), enabled=True)

    # passed=0/total=2 -> score 0, per_case has status=timeout
    assert result["score"] == 0
    assert result["details"]["passed"] == 0
    assert result["details"]["total"] == 2
    per_case = result["details"]["per_case"]
    assert len(per_case) == 1
    assert per_case[0]["status"] == "timeout"


# ---------------------------------------------------------------------------
# 6. enabled=False remains a no-op (sanity check the guard)
# ---------------------------------------------------------------------------

def test_disabled_returns_skip_without_subprocess(tmp_path):
    """enabled defaults to False -> must short-circuit and never invoke subprocess."""
    skill_path = _write_skill(tmp_path)
    with patch("subprocess.run") as p:
        result = score_runtime(skill_path, eval_suite=_eval_suite_passing())
    assert result["score"] == -1
    assert "runtime_not_enabled" in result["issues"]
    p.assert_not_called()
