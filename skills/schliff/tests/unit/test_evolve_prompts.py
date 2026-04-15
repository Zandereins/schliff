"""Tests for evolve.prompts — LLM prompt templates."""
from evolve.prompts import (
    SYSTEM_PROMPT,
    build_dimension_prompt,
    build_gradient_prompt,
    build_holistic_prompt,
)


class TestSystemPrompt:
    def test_contains_rules(self):
        assert "RULES:" in SYSTEM_PROMPT
        assert "```markdown" in SYSTEM_PROMPT
        assert "deterministic scorer" in SYSTEM_PROMPT

class TestGradientPrompt:
    def test_includes_content_and_scores(self):
        prompt = build_gradient_prompt(
            content="# Test skill",
            score=62.3,
            grade="C",
            dim_scores={"structure": {"score": 70}, "triggers": {"score": 55}},
            gradients=[{"dimension": "triggers", "issue": "false_negatives:3",
                        "instruction": "Add keywords", "delta": 5.0}],
            target_score=85.0,
        )
        assert "62.3" in prompt
        assert "# Test skill" in prompt
        assert "structure: 70.0" in prompt
        assert "triggers" in prompt
        assert "85.0" in prompt

class TestHolisticPrompt:
    def test_shows_weakest_dimensions(self):
        prompt = build_holistic_prompt(
            content="# Test",
            score=60.0,
            grade="C",
            dim_scores={
                "structure": {"score": 90},
                "triggers": {"score": 40},
                "efficiency": {"score": 50},
                "quality": {"score": 80},
            },
            target_score=85.0,
        )
        assert "triggers" in prompt
        assert "efficiency" in prompt

class TestDimensionPrompt:
    def test_targets_specific_dimension(self):
        prompt = build_dimension_prompt(
            content="# Test",
            score=60.0,
            grade="C",
            dim_scores={"triggers": {"score": 40}},
            target_dimension="triggers",
            gradients=[{"dimension": "triggers", "issue": "false_negatives:2",
                        "instruction": "Add keywords"}],
        )
        assert "TARGET DIMENSION: triggers" in prompt
        assert "40.0" in prompt
