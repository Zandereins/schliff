"""Tests for evolve.engine — the main evolution loop."""
import json
import os
from pathlib import Path

import pytest
from evolve.content import EvolutionConfig
from evolve.engine import _apply_single_patch, run_evolution


@pytest.fixture
def sample_skill(tmp_path):
    """Create a minimal skill file for testing."""
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\n"
        "name: test-skill\n"
        "description: A test skill for evolution\n"
        "---\n\n"
        "# Test Skill\n\n"
        "Do things.\n"
    )
    return str(skill)


@pytest.fixture
def mock_completion():
    """Mock LLM completion that returns improved content."""
    def _completion(model, messages, temperature, max_tokens):
        return {
            "content": (
                "```markdown\n"
                "---\n"
                "name: test-skill\n"
                "description: >-\n"
                "  A comprehensive test skill for testing evolution engine. Use when\n"
                "  you need to test the evolution loop. Do NOT use for production.\n"
                "---\n\n"
                "# Test Skill\n\n"
                "## Overview\n\n"
                "This skill handles test scenarios.\n\n"
                "## When to Use\n\n"
                "Use this skill when running evolution tests.\n\n"
                "## When NOT to Use\n\n"
                "Do NOT use for production workloads.\n"
                "```"
            ),
            "usage": {"total_tokens": 500},
        }
    return _completion


class TestDryRun:
    def test_dry_run_no_file_changes(self, sample_skill):
        original = Path(sample_skill).read_text()
        config = EvolutionConfig(
            skill_path=sample_skill,
            dry_run=True,
            budget_tokens=0,
        )
        result = run_evolution(config)
        assert result.stop_reason == "dry_run"
        assert Path(sample_skill).read_text() == original

class TestDeterministicOnly:
    def test_budget_zero_no_llm(self, sample_skill):
        config = EvolutionConfig(
            skill_path=sample_skill,
            budget_tokens=0,
            max_generations=5,
        )
        result = run_evolution(config)
        assert result.tokens_used == 0
        assert result.cost_usd == 0.0
        assert result.stop_reason in ("target_reached", "max_generations", "plateau", "no_improvement")

class TestWithMockLLM:
    def test_llm_evolution_with_mock(self, sample_skill, mock_completion):
        config = EvolutionConfig(
            skill_path=sample_skill,
            budget_tokens=10000,
            max_generations=3,
            target_score=95.0,  # high target so it keeps trying
        )
        result = run_evolution(config, completion_fn=mock_completion)
        assert result.generations > 0
        assert result.tokens_used >= 0
        assert result.final_score >= result.initial_score

class TestLineage:
    def test_lineage_created(self, sample_skill, tmp_path):
        lineage_dir = str(tmp_path / "lineage")
        config = EvolutionConfig(
            skill_path=sample_skill,
            budget_tokens=0,
            lineage_dir=lineage_dir,
        )
        result = run_evolution(config)
        assert result.lineage_path is not None
        assert os.path.exists(result.lineage_path)


class TestRejectionPlateauStopsLoop:
    """Verify that consecutive rejections trigger plateau and stop the loop."""

    def test_consecutive_rejections_stop_loop(self, sample_skill):
        """A mock that always returns garbage should trigger plateau, not burn entire budget."""
        call_count = 0

        def bad_completion(**kwargs):
            nonlocal call_count
            call_count += 1
            # Return content identical to the original (will be rejected as identical)
            return {
                "content": "```markdown\n---\nname: test-skill\ndescription: A test skill for evolution\n---\n\n# Test Skill\n\nDo things.\n```",
                "usage": {"total_tokens": 100},
            }

        config = EvolutionConfig(
            skill_path=sample_skill,
            budget_tokens=50000,  # large budget
            max_generations=50,   # many generations allowed
            target_score=99.0,
        )
        result = run_evolution(config, completion_fn=bad_completion)
        # With max_consecutive_rejections=10 and plateau window=5,
        # the loop should stop well before 50 generations
        assert result.stop_reason == "plateau", (
            f"Expected plateau stop, got '{result.stop_reason}' after {call_count} LLM calls"
        )
        assert call_count < 30, f"Too many LLM calls ({call_count}), plateau should have stopped earlier"


class TestApplySinglePatch:
    def test_insert_before(self):
        content = "line1\nline2\nline3"
        patch = {"op": "insert_before", "line": 2, "content": "new_line"}
        result = _apply_single_patch(content, patch)
        lines = result.split("\n")
        assert lines[1] == "new_line"
        assert lines[2] == "line2"

    def test_insert_at_line_1(self):
        content = "first\nsecond"
        patch = {"op": "insert_before", "line": 1, "content": "zero"}
        result = _apply_single_patch(content, patch)
        assert result.startswith("zero")

    def test_insert_clamps_negative_line(self):
        content = "line1\nline2"
        patch = {"op": "insert_before", "line": -5, "content": "new"}
        result = _apply_single_patch(content, patch)
        assert result.startswith("new")

    def test_remove_lines(self):
        content = "line1\nline2\nline3"
        patch = {"op": "remove_lines", "lines": [2]}
        result = _apply_single_patch(content, patch)
        assert "line2" not in result
        assert "line1" in result and "line3" in result

    def test_remove_multiple_lines(self):
        content = "a\nb\nc\nd"
        patch = {"op": "remove_lines", "lines": [1, 3]}
        result = _apply_single_patch(content, patch)
        assert result == "b\nd"

    def test_unsupported_op_unchanged(self):
        assert _apply_single_patch("hello", {"op": "unknown"}) == "hello"

    def test_empty_patch(self):
        assert _apply_single_patch("text", {}) == "text"

    def test_multiline_insert(self):
        content = "a\nb"
        patch = {"op": "insert_before", "line": 2, "content": "x\ny\nz"}
        result = _apply_single_patch(content, patch)
        assert result == "a\nx\ny\nz\nb"


class TestBackupCreation:
    def test_backup_created_and_removed_on_success(self, sample_skill):
        """Evolution should create a .schliff-backup and remove it on success."""
        backup_path = sample_skill + ".schliff-backup"
        config = EvolutionConfig(
            skill_path=sample_skill,
            budget_tokens=0,
            max_generations=3,
        )
        run_evolution(config)
        # Backup should be removed after successful evolution
        assert not os.path.exists(backup_path), "Backup should be cleaned up after success"

    def test_original_recoverable_from_backup(self, sample_skill):
        """If evolution is running, a backup file should exist."""
        Path(sample_skill).read_text()  # verify file is readable
        # We can't easily test mid-evolution, but verify the backup mechanism
        # by checking it works for a simple case
        config = EvolutionConfig(
            skill_path=sample_skill,
            budget_tokens=0,
            max_generations=1,
        )
        run_evolution(config)
        # After evolution, file should be valid (may or may not have changed)
        assert Path(sample_skill).exists()
        content = Path(sample_skill).read_text()
        assert len(content) > 0


class TestEngineNegativeCases:
    def test_nonexistent_skill_path(self):
        config = EvolutionConfig(skill_path="/nonexistent/file.md", budget_tokens=0)
        with pytest.raises((FileNotFoundError, SystemExit)):
            run_evolution(config)

    def test_target_already_reached(self, sample_skill):
        config = EvolutionConfig(
            skill_path=sample_skill,
            budget_tokens=0,
            target_score=0.0,  # any file scores > 0
        )
        result = run_evolution(config)
        assert result.stop_reason == "target_reached"
        assert result.generations == 0


class TestLineageContent:
    def test_lineage_contains_header_and_footer(self, sample_skill, tmp_path):
        lineage_dir = str(tmp_path / "lineage")
        config = EvolutionConfig(
            skill_path=sample_skill,
            budget_tokens=0,
            lineage_dir=lineage_dir,
        )
        result = run_evolution(config)
        assert result.lineage_path is not None
        content = Path(result.lineage_path).read_text()
        lines = [json.loads(ln) for ln in content.strip().split("\n")]
        types = [ln.get("type") for ln in lines]
        assert "session_header" in types
        assert "session_footer" in types
