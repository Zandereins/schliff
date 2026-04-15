"""Tests for evolve.content — content utilities and dataclasses."""
import pytest
from evolve.content import (
    EvolutionConfig,
    EvolutionResult,
    GuardResult,
    content_hash,
    extract_markdown_content,
    grade_from_score,
    score_to_threshold,
)


class TestExtractMarkdownContent:
    def test_extracts_from_fences(self):
        response = "Here is the improved file:\n```markdown\n---\nname: test\n---\nContent here\n```\nDone."
        result = extract_markdown_content(response)
        assert result.startswith("---")
        assert "Content here" in result

    def test_no_fences_returns_stripped(self):
        response = "  Just raw content  "
        assert extract_markdown_content(response) == "Just raw content"

    def test_generic_code_fence(self):
        response = "```\ncontent\n```"
        assert extract_markdown_content(response) == "content"

    def test_empty_response(self):
        assert extract_markdown_content("") == ""

class TestContentHash:
    def test_deterministic(self):
        assert content_hash("hello") == content_hash("hello")

    def test_different_content_different_hash(self):
        assert content_hash("hello") != content_hash("world")

    def test_length_12(self):
        assert len(content_hash("anything")) == 12

class TestGradeFromScore:
    def test_grades(self):
        assert grade_from_score(95.0) == "S"
        assert grade_from_score(85.0) == "A"
        assert grade_from_score(75.0) == "B"
        assert grade_from_score(65.0) == "C"
        assert grade_from_score(50.0) == "D"
        assert grade_from_score(49.9) == "F"

    def test_boundary(self):
        assert grade_from_score(94.9) == "A"
        assert grade_from_score(100.0) == "S"
        assert grade_from_score(0.0) == "F"

class TestScoreToThreshold:
    def test_grade_strings(self):
        assert score_to_threshold("S") == 95.0
        assert score_to_threshold("A") == 85.0
        assert score_to_threshold("B") == 75.0
        assert score_to_threshold("C") == 65.0

    def test_numeric_string(self):
        assert score_to_threshold("80.0") == 80.0
        assert score_to_threshold("92") == 92.0

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            score_to_threshold("X")

    def test_case_insensitive(self):
        assert score_to_threshold("a") == 85.0
        assert score_to_threshold("s") == 95.0

class TestExtractMarkdownContentEdgeCases:
    def test_nested_code_fences(self):
        """LLM output with nested code blocks — parser matches first closing fence."""
        response = (
            "```markdown\n"
            "# Skill\n"
            "Here's an example:\n"
            "```python\n"
            "print('hello')\n"
            "```\n"
            "More text\n"
            "```\n"
        )
        result = extract_markdown_content(response)
        assert "# Skill" in result
        # Parser stops at first ``` — nested fences truncate content
        assert "print('hello')" in result

    def test_md_fence_variant(self):
        response = "```md\ncontent here\n```"
        assert extract_markdown_content(response) == "content here"

    def test_empty_fences(self):
        response = "```markdown\n\n```"
        assert extract_markdown_content(response) == ""

class TestContentHashEdgeCases:
    def test_empty_string(self):
        h = content_hash("")
        assert len(h) == 12

    def test_unicode_content(self):
        h = content_hash("Ünïcödé ✓ 日本語")
        assert len(h) == 12

class TestGradeEdgeCases:
    def test_negative_score(self):
        assert grade_from_score(-10) == "F"

    def test_score_above_100(self):
        assert grade_from_score(105) == "S"

class TestScoreToThresholdEdgeCases:
    def test_lowercase_grades(self):
        assert score_to_threshold("a") == 85.0
        assert score_to_threshold("s") == 95.0
        assert score_to_threshold("b") == 75.0

    def test_whitespace_padded(self):
        assert score_to_threshold("  A  ") == 85.0

    def test_grade_d(self):
        assert score_to_threshold("D") == 50.0

    def test_float_with_decimals(self):
        assert score_to_threshold("87.5") == 87.5


class TestDataclasses:
    def test_evolution_config_defaults(self):
        cfg = EvolutionConfig(skill_path="test.md")
        assert cfg.target_score == 85.0
        assert cfg.max_generations == 10
        assert cfg.budget_tokens == 50000
        assert cfg.strategy == "gradient"
        assert cfg.dry_run is False

    def test_evolution_result(self):
        r = EvolutionResult(
            initial_score=60.0, final_score=80.0,
            initial_grade="C", final_grade="B",
            generations=5, accepted=3, rejected=1,
            deterministic_patches=1, tokens_used=9000,
            cost_usd=0.03, stop_reason="target_reached",
        )
        assert r.final_score > r.initial_score

    def test_guard_result(self):
        gr = GuardResult(passed=True, violations=[])
        assert gr.passed
        assert gr.violations == []
