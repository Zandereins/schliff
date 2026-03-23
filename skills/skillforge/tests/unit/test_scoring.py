"""Unit tests for the scoring package."""
import json
import tempfile
from pathlib import Path

import pytest

from scoring import (
    score_structure,
    score_triggers,
    score_efficiency,
    score_composability,
    score_coherence,
    score_quality,
    score_edges,
    compute_composite,
)
from scoring.patterns import (
    _RE_FRONTMATTER_NAME,
    _RE_FRONTMATTER_DESC,
    _RE_HEDGING,
    _RE_TODO,
)


# --- Fixtures ---

@pytest.fixture
def good_skill(tmp_path):
    """A well-formed SKILL.md that should score high."""
    content = '''---
name: test-skill
description: >
  A test skill for unit testing. Use when testing scoring functions.
  Do not use for production deployment or security scanning.
---

# Test Skill

Use this skill when you need to test scoring functions.

## Instructions

1. Read the input file
2. Run the scoring function
3. Verify the output matches expectations

## Examples

Example 1: Basic scoring
```bash
python3 scripts/score-skill.py test.md --json
```

Example 2: With eval suite
```bash
python3 scripts/score-skill.py test.md --eval-suite eval.json
```

## When NOT to Use

Do not use this skill for:
- Production deployment
- Security vulnerability scanning
- Database migrations
'''
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text(content)
    return str(skill_path)


@pytest.fixture
def bad_skill(tmp_path):
    """A poorly-formed SKILL.md that should score low."""
    content = '''no frontmatter here

TODO: add description
FIXME: add examples

you might want to consider maybe possibly doing something
you could try to perhaps attempt this
'''
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text(content)
    return str(skill_path)


@pytest.fixture
def minimal_skill(tmp_path):
    """Minimal valid SKILL.md."""
    content = '''---
name: minimal
description: A minimal skill
---

# Minimal Skill

Do the thing.
'''
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text(content)
    return str(skill_path)


@pytest.fixture
def eval_suite():
    """A basic eval suite for testing trigger and quality scoring."""
    return {
        "triggers": [
            {"prompt": "improve my skill quality", "should_trigger": True},
            {"prompt": "optimize this skill's triggers", "should_trigger": True},
            {"prompt": "analyze my skill for issues", "should_trigger": True},
            {"prompt": "deploy my web application", "should_trigger": False},
            {"prompt": "fix the CSS styling", "should_trigger": False},
        ],
        "test_cases": [
            {
                "id": "tc-1",
                "prompt": "analyze the skill",
                "assertions": [
                    {"type": "contains", "value": "score", "description": "mentions score"},
                    {"type": "pattern", "value": "\\d+/100", "description": "has numeric score"},
                    {"type": "excludes", "value": "TODO", "description": "no TODOs"},
                ],
            }
        ],
        "edge_cases": [
            {
                "id": "ec-1",
                "prompt": "empty input",
                "category": "missing_input",
                "expected_behavior": "Should ask for clarification",
                "assertions": [
                    {"type": "contains", "value": "?", "description": "asks a question"},
                ],
            }
        ],
    }


# --- score_structure tests ---

class TestScoreStructure:
    def test_good_skill_scores_high(self, good_skill):
        result = score_structure(good_skill)
        assert result["score"] >= 70
        assert isinstance(result["issues"], list)

    def test_bad_skill_scores_low(self, bad_skill):
        result = score_structure(bad_skill)
        assert result["score"] <= 40
        assert "no_frontmatter" in result["issues"]

    def test_missing_file_returns_zero(self):
        result = score_structure("/nonexistent/SKILL.md")
        assert result["score"] == 0
        assert "file_not_found" in result["issues"]

    def test_minimal_skill_scores_moderate(self, minimal_skill):
        result = score_structure(minimal_skill)
        assert 20 <= result["score"] <= 85

    def test_returns_dict_with_required_keys(self, good_skill):
        result = score_structure(good_skill)
        assert "score" in result
        assert "issues" in result
        assert "details" in result


# --- score_efficiency tests ---

class TestScoreEfficiency:
    def test_good_skill_has_decent_efficiency(self, good_skill):
        result = score_efficiency(good_skill)
        assert result["score"] >= 50

    def test_bad_skill_penalized_for_hedging(self, bad_skill):
        result = score_efficiency(bad_skill)
        assert result["score"] <= 60
        # Should detect hedging language
        details = result.get("details", {})
        assert details.get("hedge_count", 0) >= 1

    def test_missing_file_returns_zero(self):
        result = score_efficiency("/nonexistent/SKILL.md")
        assert result["score"] == 0


# --- score_composability tests ---

class TestScoreComposability:
    def test_good_skill_with_scope_boundaries(self, good_skill):
        result = score_composability(good_skill)
        # Good skill has "Use when" and "Do not use"
        assert result["score"] >= 40

    def test_bad_skill_no_scope(self, bad_skill):
        result = score_composability(bad_skill)
        assert "no_scope_boundaries" in result["issues"]


# --- score_triggers tests ---

class TestScoreTriggers:
    def test_with_eval_suite(self, good_skill, eval_suite):
        result = score_triggers(good_skill, eval_suite)
        assert result["score"] >= 0
        assert "details" in result
        assert result["details"]["total"] == 5

    def test_without_eval_suite(self, good_skill):
        result = score_triggers(good_skill, None)
        assert result["score"] == -1
        assert "no_trigger_eval_suite" in result["issues"]


# --- score_quality tests ---

class TestScoreQuality:
    def test_with_eval_suite(self, good_skill, eval_suite):
        result = score_quality(good_skill, eval_suite)
        assert result["score"] >= 0 or result["score"] == -1

    def test_without_eval_suite(self, good_skill):
        result = score_quality(good_skill, None)
        assert result["score"] == -1


# --- score_edges tests ---

class TestScoreEdges:
    def test_with_edge_cases(self, good_skill, eval_suite):
        result = score_edges(good_skill, eval_suite)
        assert result["score"] >= 0

    def test_without_eval_suite(self, good_skill):
        result = score_edges(good_skill, None)
        assert result["score"] == -1


# --- compute_composite tests ---

class TestComputeComposite:
    def test_basic_composite(self):
        scores = {
            "structure": {"score": 80},
            "triggers": {"score": 90},
            "efficiency": {"score": 70},
            "composability": {"score": 60},
            "quality": {"score": -1},  # unmeasured
            "edges": {"score": -1},    # unmeasured
        }
        result = compute_composite(scores)
        assert "score" in result
        assert 0 <= result["score"] <= 100
        assert result["measured_dimensions"] >= 4

    def test_all_unmeasured(self):
        scores = {
            "structure": {"score": -1},
            "triggers": {"score": -1},
        }
        result = compute_composite(scores)
        assert result["score"] == 0 or result["measured_dimensions"] == 0

    def test_perfect_scores(self):
        scores = {
            "structure": {"score": 100},
            "triggers": {"score": 100},
            "efficiency": {"score": 100},
            "composability": {"score": 100},
            "quality": {"score": 100},
            "edges": {"score": 100},
        }
        result = compute_composite(scores)
        assert result["score"] >= 95


# --- Pattern tests ---

class TestPatterns:
    def test_frontmatter_name_pattern(self):
        assert _RE_FRONTMATTER_NAME.search("name: my-skill")
        assert not _RE_FRONTMATTER_NAME.search("no name here")

    def test_frontmatter_desc_pattern(self):
        assert _RE_FRONTMATTER_DESC.search("description: something")
        assert not _RE_FRONTMATTER_DESC.search("no desc")

    def test_hedging_pattern(self):
        assert _RE_HEDGING.search("you might want to consider this")
        assert _RE_HEDGING.search("you could possibly try")
        assert not _RE_HEDGING.search("Run the command")

    def test_todo_pattern(self):
        assert _RE_TODO.search("TODO: fix this")
        assert _RE_TODO.search("FIXME: broken")
        assert not _RE_TODO.search("this is done")
