"""Unit tests for schliff verify (verify.py)."""
import json
import time
from pathlib import Path

import pytest

import verify as verify_mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def good_skill(tmp_path):
    """A well-formed SKILL.md that scores high."""
    content = '''---
name: test-skill
description: >
  A comprehensive test skill for verifying scoring functions.
  Use when running automated quality checks on skill files.
  Do NOT use for creating new skills from scratch.
---

# Test Skill

Use this skill when you need to verify skill quality scoring.

## When to Use

- Run automated quality checks on skill files
- Verify scoring functions produce expected results
- Test the verification pipeline

## How to Use

1. Run `schliff score path/to/SKILL.md` to get a baseline
2. Review the dimension breakdown
3. Fix any weak dimensions

## Scope

This skill handles: scoring verification, quality checks.
This skill does NOT handle: skill creation, runtime evaluation.

## Error Behavior

If the skill file is missing, return exit code 2.
If scoring fails, log the error and return exit code 2.

## Dependencies

Requires: Python 3.9+, scoring package.
'''
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text(content, encoding="utf-8")
    return str(skill_path)


@pytest.fixture
def bad_skill(tmp_path):
    """A poorly-formed SKILL.md that scores low."""
    content = '''no frontmatter here
TODO: add description
FIXME: add examples
This might maybe probably help with stuff.
'''
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    skill_path = bad_dir / "SKILL.md"
    skill_path.write_text(content, encoding="utf-8")
    return str(skill_path)


@pytest.fixture
def history_file(tmp_path):
    """A temporary history file path."""
    return str(tmp_path / ".schliff" / "history.jsonl")


# ---------------------------------------------------------------------------
# _score_skill
# ---------------------------------------------------------------------------

class TestScoreSkill:
    def test_returns_composite(self, good_skill):
        result = verify_mod._score_skill(good_skill)
        assert "composite" in result
        assert isinstance(result["composite"], float)
        assert 0 <= result["composite"] <= 100

    def test_returns_grade(self, good_skill):
        result = verify_mod._score_skill(good_skill)
        assert result["grade"] in ("S", "A", "B", "C", "D", "E", "F")

    def test_returns_dimensions(self, good_skill):
        result = verify_mod._score_skill(good_skill)
        assert "dimensions" in result
        assert "structure" in result["dimensions"]
        assert "clarity" in result["dimensions"]

    def test_bad_skill_scores_lower(self, good_skill, bad_skill):
        good = verify_mod._score_skill(good_skill)
        bad = verify_mod._score_skill(bad_skill)
        assert good["composite"] > bad["composite"]


# ---------------------------------------------------------------------------
# score_to_grade (imported from terminal_art)
# ---------------------------------------------------------------------------

class TestScoreToGrade:
    def test_grades_via_verify(self):
        # verify.py re-exports terminal_art.score_to_grade; spot-check
        # that _score_skill's grade field maps through consistently.
        from terminal_art import score_to_grade
        assert score_to_grade(100) == "S"
        assert score_to_grade(95) == "S"
        assert score_to_grade(90) == "A"
        assert score_to_grade(80) == "B"
        assert score_to_grade(70) == "C"
        assert score_to_grade(55) == "D"
        assert score_to_grade(30) == "F"


# ---------------------------------------------------------------------------
# History: load_last_score / append_history
# ---------------------------------------------------------------------------

class TestHistory:
    def test_no_history_returns_none(self, good_skill, history_file):
        result = verify_mod.load_last_score(good_skill, history_file)
        assert result is None

    def test_append_and_load(self, good_skill, history_file):
        result = {"composite": 82.5, "grade": "B", "dimensions": {}}
        verify_mod.append_history(good_skill, result, history_file)

        loaded = verify_mod.load_last_score(good_skill, history_file)
        assert loaded == 82.5

    def test_loads_latest_entry(self, good_skill, history_file):
        r1 = {"composite": 70.0, "grade": "C", "dimensions": {}}
        r2 = {"composite": 85.0, "grade": "A", "dimensions": {}}
        verify_mod.append_history(good_skill, r1, history_file)
        verify_mod.append_history(good_skill, r2, history_file)

        loaded = verify_mod.load_last_score(good_skill, history_file)
        assert loaded == 85.0

    def test_regression_skipped_across_weight_regimes(self, good_skill, history_file):
        """If the prior history entry used a different weight model, the regression
        gate must SKIP (not silently fail) — and never compare across regimes."""
        # Seed a prior 'calibrated' entry (different regime from a canonical verify run).
        seeded = {
            "composite": 95.0, "grade": "A", "dimensions": {},
            "weight_coverage": 1.0, "weight_source": "calibrated", "weights_hash": "deadbeef0000",
        }
        verify_mod.append_history(good_skill, seeded, history_file)

        verdict = verify_mod.run_verify(
            good_skill, min_score=40.0, history_path=history_file,
            check_regression=True,
        )
        assert verdict["weight_source"] == "default"  # verify is always canonical
        assert "different weight model" in verdict["message"]
        assert verdict["exit_code"] == 0
        assert verdict["regression"] is False

    def test_different_skills_isolated(self, tmp_path, history_file):
        skill_a = tmp_path / "a" / "SKILL.md"
        skill_b = tmp_path / "b" / "SKILL.md"
        skill_a.parent.mkdir()
        skill_b.parent.mkdir()
        skill_a.write_text("---\nname: a\n---\n", encoding="utf-8")
        skill_b.write_text("---\nname: b\n---\n", encoding="utf-8")

        verify_mod.append_history(str(skill_a), {"composite": 60.0, "grade": "C", "dimensions": {}}, history_file)
        verify_mod.append_history(str(skill_b), {"composite": 90.0, "grade": "A", "dimensions": {}}, history_file)

        assert verify_mod.load_last_score(str(skill_a), history_file) == 60.0
        assert verify_mod.load_last_score(str(skill_b), history_file) == 90.0

    def test_creates_parent_dirs(self, tmp_path):
        deep_path = str(tmp_path / "a" / "b" / "c" / "history.jsonl")
        verify_mod.append_history(
            "/fake/SKILL.md",
            {"composite": 50.0, "grade": "D", "dimensions": {}},
            deep_path,
        )
        assert Path(deep_path).exists()

    def test_history_entry_has_timestamp(self, good_skill, history_file):
        verify_mod.append_history(
            good_skill,
            {"composite": 80.0, "grade": "B", "dimensions": {}},
            history_file,
        )
        line = Path(history_file).read_text(encoding="utf-8").strip()
        entry = json.loads(line)
        assert "timestamp" in entry
        # Timestamp should be today
        assert entry["timestamp"].startswith(time.strftime("%Y-%m-%d"))

    def test_corrupt_lines_skipped(self, good_skill, history_file):
        hp = Path(history_file)
        hp.parent.mkdir(parents=True, exist_ok=True)
        resolved = str(Path(good_skill).resolve())
        hp.write_text(
            "not json\n"
            f'{{"skill_path":"{resolved}","composite":77.0}}\n'
            "also broken\n",
            encoding="utf-8",
        )
        assert verify_mod.load_last_score(good_skill, history_file) == 77.0


# ---------------------------------------------------------------------------
# run_verify — threshold checks
# ---------------------------------------------------------------------------

@pytest.fixture
def weak_no_eval_skill(tmp_path):
    """A no-eval-suite skill whose measured dimensions are mediocre.

    Same coverage as good_skill (no eval suite → ~0.42), but lower per-measured
    quality, so it should fail effective_min = 75 * coverage while the good skill
    passes. Used to prove coverage-awareness discriminates on quality, not coverage.
    """
    content = '''---
name: weak
description: A skill.
---

# Weak

Stuff.
'''
    weak_dir = tmp_path / "weak"
    weak_dir.mkdir()
    skill_path = weak_dir / "SKILL.md"
    skill_path.write_text(content, encoding="utf-8")
    return str(skill_path)


@pytest.fixture
def eval_suite_full():
    """A minimal eval suite that lifts coverage toward ~1.0.

    Providing an eval suite credits the triggers/quality/edges dimensions, so
    weight_coverage approaches 1.0 and the skill is judged against ~full min_score.
    """
    return {
        "skill_name": "test-skill",
        "triggers": [
            {"id": "pos-1", "prompt": "Run automated quality checks on a skill file and verify scoring.", "should_trigger": True, "category": "positive"},
            {"id": "pos-2", "prompt": "Verify the skill quality scoring produces expected results.", "should_trigger": True, "category": "positive"},
            {"id": "neg-1", "prompt": "Create a brand new skill from scratch.", "should_trigger": False, "category": "negative"},
        ],
        "test_cases": [
            {"id": "tc-1", "prompt": "Run a quality check on a skill file.",
             "assertions": [{"type": "contains", "value": "score"}, {"type": "not_contains", "value": "TODO"}]},
            {"id": "tc-2", "prompt": "Review the dimension breakdown for a skill.",
             "assertions": [{"type": "contains", "value": "dimension"}]},
            {"id": "tc-3", "prompt": "Fix a weak dimension in a skill.",
             "assertions": [{"type": "contains", "value": "fix"}]},
        ],
        "edge_cases": [
            {"id": "ec-1", "prompt": "The SKILL.md file is missing entirely.",
             "expected_behavior": "Return exit code 2.",
             "assertions": [{"type": "contains", "value": "exit code 2"}]},
            {"id": "ec-2", "prompt": "Scoring crashes mid-run.",
             "expected_behavior": "Log the error and return exit code 2.",
             "assertions": [{"type": "contains", "value": "error"}]},
        ],
    }


class TestRunVerifyThreshold:
    def test_good_skill_passes_default(self, good_skill, history_file):
        # Coverage-aware: a strong no-eval-suite skill (composite ~33, coverage ~0.42)
        # clears effective_min = 75 * 0.42 ≈ 31.5, so the DEFAULT threshold is now
        # reachable without an eval suite.
        verdict = verify_mod.run_verify(
            good_skill, history_path=history_file,
        )
        assert verdict["exit_code"] == 0
        assert verdict["passed_threshold"] is True
        assert "PASS" in verdict["message"]

    def test_coverage_aware_good_no_eval_suite_passes_default(self, good_skill, history_file):
        """Strong no-eval-suite skill PASSES the default (75) via coverage scaling."""
        verdict = verify_mod.run_verify(
            good_skill, history_path=history_file,  # default min_score = 75.0
        )
        assert verdict["min_score"] == 75.0
        # Coverage is below 1.0 (no eval suite) so effective_min is scaled down.
        assert 0 < verdict["coverage"] < 1.0
        assert verdict["effective_min"] == pytest.approx(75.0 * verdict["coverage"])
        assert verdict["composite"] >= verdict["effective_min"]
        assert verdict["exit_code"] == 0
        assert verdict["passed_threshold"] is True

    def test_coverage_aware_weak_no_eval_suite_fails_default(self, weak_no_eval_skill, history_file):
        """Mediocre no-eval-suite skill FAILS the default despite coverage scaling."""
        verdict = verify_mod.run_verify(
            weak_no_eval_skill, history_path=history_file,  # default min_score = 75.0
        )
        assert 0 < verdict["coverage"] < 1.0
        assert verdict["effective_min"] == pytest.approx(75.0 * verdict["coverage"])
        assert verdict["composite"] < verdict["effective_min"]
        assert verdict["exit_code"] == 1
        assert verdict["passed_threshold"] is False
        assert "FAIL" in verdict["message"]

    def test_coverage_aware_eval_suite_judged_against_full(self, good_skill, eval_suite_full, history_file):
        """An eval-suite skill has higher coverage → judged against ~full min_score."""
        verdict = verify_mod.run_verify(
            good_skill, history_path=history_file, eval_suite=eval_suite_full,
        )
        # Adding an eval suite raises coverage above the no-eval-suite baseline (~0.42).
        no_eval = verify_mod.run_verify(good_skill, history_path=history_file)
        assert verdict["coverage"] > no_eval["coverage"]
        assert verdict["effective_min"] == pytest.approx(75.0 * verdict["coverage"])

    def test_bad_skill_fails_high_threshold(self, bad_skill, history_file):
        verdict = verify_mod.run_verify(
            bad_skill, min_score=90.0, history_path=history_file,
        )
        assert verdict["exit_code"] == 1
        assert verdict["passed_threshold"] is False
        assert "FAIL" in verdict["message"]

    def test_custom_min_score(self, good_skill, history_file):
        verdict = verify_mod.run_verify(
            good_skill, min_score=99.0, history_path=history_file,
        )
        # Good skill unlikely to hit 99
        assert verdict["min_score"] == 99.0

    def test_records_history_on_pass(self, good_skill, history_file):
        # Passes the default threshold via coverage scaling and records history.
        verify_mod.run_verify(
            good_skill, history_path=history_file,
        )
        assert Path(history_file).exists()
        content = Path(history_file).read_text(encoding="utf-8").strip()
        assert len(content.splitlines()) == 1

    def test_records_history_on_fail(self, bad_skill, history_file):
        verify_mod.run_verify(
            bad_skill, min_score=99.0, history_path=history_file,
        )
        assert Path(history_file).exists()


# ---------------------------------------------------------------------------
# run_verify — regression checks
# ---------------------------------------------------------------------------

class TestRunVerifyRegression:
    def test_no_previous_score_passes(self, good_skill, history_file):
        # Default threshold (75.0) is now reachable for a strong no-eval-suite
        # skill via coverage scaling (effective_min = 75 * ~0.42 ≈ 31.5 < ~33).
        verdict = verify_mod.run_verify(
            good_skill, check_regression=True,
            history_path=history_file,
        )
        assert verdict["exit_code"] == 0
        assert verdict["previous_score"] is None
        assert "no previous score" in verdict["message"]

    def test_score_improved_passes(self, good_skill, history_file):
        # Seed history with a low score
        verify_mod.append_history(
            good_skill,
            {"composite": 10.0, "grade": "F", "dimensions": {}},
            history_file,
        )
        # Default threshold cleared via coverage scaling, then improvement detected.
        verdict = verify_mod.run_verify(
            good_skill, check_regression=True,
            history_path=history_file,
        )
        assert verdict["exit_code"] == 0
        assert verdict["delta"] is not None
        assert verdict["delta"] > 0
        assert verdict["regression"] is False

    def test_score_regressed_fails(self, good_skill, history_file):
        # Seed history with a very high score that real scoring can't reach
        verify_mod.append_history(
            good_skill,
            {"composite": 999.0, "grade": "S", "dimensions": {}},
            history_file,
        )
        # Default threshold cleared via coverage scaling so the regression gate runs.
        verdict = verify_mod.run_verify(
            good_skill, check_regression=True,
            history_path=history_file,
        )
        assert verdict["exit_code"] == 1
        assert verdict["regression"] is True
        assert "REGRESSION" in verdict["message"]
        assert verdict["delta"] < 0

    def test_regression_check_off_ignores_drop(self, good_skill, history_file):
        verify_mod.append_history(
            good_skill,
            {"composite": 999.0, "grade": "S", "dimensions": {}},
            history_file,
        )
        # Default threshold cleared via coverage scaling; without --regression
        # the seeded score drop must be ignored.
        verdict = verify_mod.run_verify(
            good_skill, check_regression=False,
            history_path=history_file,
        )
        # Without --regression, score drop doesn't matter
        assert verdict["exit_code"] == 0

    def test_threshold_checked_before_regression(self, bad_skill, history_file):
        """If score < min_score, fail immediately without regression check."""
        verdict = verify_mod.run_verify(
            bad_skill, min_score=99.0, check_regression=True,
            history_path=history_file,
        )
        assert verdict["exit_code"] == 1
        assert "FAIL" in verdict["message"]
        # Regression check should not have run
        assert verdict["regression"] is False


# ---------------------------------------------------------------------------
# format_verdict
# ---------------------------------------------------------------------------

class TestFormatVerdict:
    def test_pass_message(self):
        verdict = {
            "message": "PASS: 82.5/100 [B] >= 75",
            "exit_code": 0,
            "dimensions": {},
        }
        output = verify_mod.format_verdict(verdict)
        assert "PASS" in output

    def test_fail_shows_weak_dimensions(self):
        verdict = {
            "message": "FAIL: 50.0/100 [D] < minimum 75",
            "exit_code": 1,
            "dimensions": {"structure": 30, "triggers": 90, "efficiency": 45},
        }
        output = verify_mod.format_verdict(verdict)
        assert "Weak dimensions" in output
        assert "structure" in output
        assert "efficiency" in output
        # triggers (90) should NOT appear in weak list
        assert "triggers" not in output.split("Weak")[1]

    def test_pass_no_weak_breakdown(self):
        verdict = {
            "message": "PASS: 90/100 [A] >= 75",
            "exit_code": 0,
            "dimensions": {"structure": 95, "triggers": 90},
        }
        output = verify_mod.format_verdict(verdict)
        assert "Weak" not in output


# ---------------------------------------------------------------------------
# Verdict dict structure
# ---------------------------------------------------------------------------

class TestVerdictStructure:
    def test_all_keys_present(self, good_skill, history_file):
        verdict = verify_mod.run_verify(
            good_skill, min_score=40.0, history_path=history_file,
        )
        expected_keys = {
            "skill_path", "composite", "grade", "dimensions",
            "min_score", "coverage", "effective_min",
            "passed_threshold", "exit_code", "message",
            "previous_score", "delta", "regression",
            "weight_source", "weights_hash",
        }
        assert set(verdict.keys()) == expected_keys

    def test_json_serializable(self, good_skill, history_file):
        verdict = verify_mod.run_verify(
            good_skill, min_score=40.0, history_path=history_file,
        )
        # Must not raise
        serialized = json.dumps(verdict)
        assert isinstance(serialized, str)
