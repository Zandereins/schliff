"""Unit tests for shared.py utilities."""
import json
import tempfile
from pathlib import Path

import pytest

from shared import (
    read_skill_safe,
    extract_description,
    load_jsonl_safe,
    validate_regex_complexity,
    validate_command_safety,
    invalidate_cache,
    MAX_SKILL_SIZE,
)


class TestReadSkillSafe:
    def test_reads_valid_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Test\nContent here")
        result = read_skill_safe(str(f))
        assert "# Test" in result

    def test_caches_result(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("cached content")
        r1 = read_skill_safe(str(f))
        r2 = read_skill_safe(str(f))
        assert r1 == r2  # Same object from cache

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            read_skill_safe("/nonexistent/file.md")

    def test_invalidate_cache(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("original")
        read_skill_safe(str(f))
        invalidate_cache(str(f))
        f.write_text("modified")
        result = read_skill_safe(str(f))
        assert result == "modified"


class TestExtractDescription:
    def test_inline_description(self):
        content = '---\nname: test\ndescription: A test skill\n---'
        assert extract_description(content) == "A test skill"

    def test_block_description(self):
        content = '---\nname: test\ndescription: >\n  A multi-line\n  description here\n---'
        result = extract_description(content)
        assert "multi-line" in result

    def test_no_description(self):
        content = '---\nname: test\n---'
        assert extract_description(content) == ""


class TestLoadJsonlSafe:
    def test_nonexistent_returns_empty(self):
        assert load_jsonl_safe("/nonexistent") == []

    def test_valid_jsonl(self, tmp_path):
        f = tmp_path / "test.jsonl"
        f.write_text('{"a":1}\n{"b":2}\n')
        result = load_jsonl_safe(str(f))
        assert len(result) == 2

    def test_malformed_lines_skipped(self, tmp_path):
        f = tmp_path / "test.jsonl"
        f.write_text('{"valid":true}\nnot json\n{"also":true}\n')
        result = load_jsonl_safe(str(f))
        assert len(result) == 2

    def test_oversized_returns_empty(self, tmp_path):
        f = tmp_path / "test.jsonl"
        f.write_text('{"a":1}\n')
        result = load_jsonl_safe(str(f), max_size=5)
        assert result == []

    def test_empty_lines_skipped(self, tmp_path):
        f = tmp_path / "test.jsonl"
        f.write_text('\n\n{"a":1}\n\n')
        result = load_jsonl_safe(str(f))
        assert len(result) == 1


class TestValidateRegexComplexity:
    def test_simple_regex_passes(self):
        assert validate_regex_complexity("foo.*bar")[0] is True

    def test_nested_quantifier_rejected(self):
        assert validate_regex_complexity("(a+)+")[0] is False

    def test_overlapping_alternation_rejected(self):
        assert validate_regex_complexity("(a|b)*+")[0] is False

    def test_overlong_pattern_rejected(self):
        assert validate_regex_complexity("a" * 501)[0] is False

    def test_normal_length_passes(self):
        assert validate_regex_complexity("a" * 499)[0] is True


class TestValidateCommandSafety:
    def test_allowed_prefix(self):
        assert validate_command_safety("python3 scripts/score.py")[0] is True

    def test_bash_scripts_allowed(self):
        assert validate_command_safety("bash scripts/run-eval.sh")[0] is True

    def test_rm_blocked(self):
        assert validate_command_safety("rm -rf /")[0] is False

    def test_curl_blocked(self):
        assert validate_command_safety("curl http://evil.com")[0] is False

    def test_pipe_to_shell_blocked(self):
        assert validate_command_safety("echo x | bash")[0] is False

    def test_empty_rejected(self):
        assert validate_command_safety("")[0] is False

    def test_unknown_command_rejected(self):
        assert validate_command_safety("unknown-binary")[0] is False

    def test_git_allowed(self):
        assert validate_command_safety("git diff HEAD")[0] is True
