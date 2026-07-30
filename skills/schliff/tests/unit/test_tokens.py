"""Tests for token budget estimation in formats.py."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

# Add scripts directory to path so we can import scoring.formats
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from scoring.formats import (
    FORMAT_TOKEN_BUDGETS,
    check_token_budget,
    estimate_tokens,
)


class TestEstimateTokens:
    """Tests for the estimate_tokens function."""

    def test_known_string(self) -> None:
        # 20 chars -> 5 tokens
        assert estimate_tokens("a" * 20) == 5

    def test_empty_string(self) -> None:
        assert estimate_tokens("") == 0

    def test_short_string(self) -> None:
        # 3 chars -> 0 tokens (integer division)
        assert estimate_tokens("abc") == 0

    def test_exact_multiple(self) -> None:
        assert estimate_tokens("a" * 100) == 25


class TestFormatTokenBudgets:
    """Tests for the FORMAT_TOKEN_BUDGETS constant."""

    def test_has_all_expected_keys(self) -> None:
        expected = {"skill.md", "claude.md", "cursorrules", "agents.md", "system_prompt", "unknown"}
        assert set(FORMAT_TOKEN_BUDGETS.keys()) == expected

    def test_values_are_positive_ints(self) -> None:
        for fmt, budget in FORMAT_TOKEN_BUDGETS.items():
            assert isinstance(budget, int), f"{fmt} budget is not int"
            assert budget > 0, f"{fmt} budget is not positive"


#: Docs that hand-maintain a copy of FORMAT_TOKEN_BUDGETS as a markdown table.
_BUDGET_DOCS = ("docs/SCORING.md", "docs/ARCHITECTURE.md")
_REPO_ROOT = Path(__file__).resolve().parents[4]
_TABLE_ROW = re.compile(r"^\|\s*([A-Za-z0-9_.-]+)\s*\|\s*(\d+)\s*\|\s*$", re.M)


def _documented_budgets(doc: str) -> dict[str, int]:
    """Budget rows from the section headed '... token budgets' in `doc`."""
    text = (_REPO_ROOT / doc).read_text(encoding="utf-8")
    heading = re.search(r"^#+ .*token budgets.*$", text, re.M | re.I)
    assert heading, f"{doc} has no token-budget section to check"
    section = text[heading.end():]
    nxt = re.search(r"^#+ |^---\s*$", section, re.M)
    if nxt:
        section = section[: nxt.start()]
    return {m.group(1): int(m.group(2)) for m in _TABLE_ROW.finditer(section)}


@pytest.mark.parametrize("doc", _BUDGET_DOCS)
def test_docs_budget_table_matches_the_code(doc: str) -> None:
    """These tables are hand-copied from FORMAT_TOKEN_BUDGETS and nothing gated them.

    Recalibrating `skill.md` left both docs stating the old number; markdownlint checks
    form, not content, so a doc claiming what the code does not do shipped unnoticed.
    """
    documented = _documented_budgets(doc)
    assert documented, f"{doc}: parsed no budget rows — the table moved or changed shape"
    for fmt, value in documented.items():
        assert fmt in FORMAT_TOKEN_BUDGETS, f"{doc} documents unknown format {fmt!r}"
        assert value == FORMAT_TOKEN_BUDGETS[fmt], (
            f"{doc} says {fmt} is {value}, code says {FORMAT_TOKEN_BUDGETS[fmt]}"
        )
    # `unknown` is the internal fallback, not a format a user selects, so it is the one
    # entry the docs deliberately omit. Everything else must be listed.
    missing = set(FORMAT_TOKEN_BUDGETS) - set(documented) - {"unknown"}
    assert not missing, f"{doc} does not document these formats: {sorted(missing)}"


class TestCheckTokenBudget:
    """Tests for the check_token_budget function.

    These pin the *mechanism* — the severity bands and the ratio — so the sizes below
    are derived from whatever `skill.md` is budgeted at rather than restated. They used
    to hardcode 1000 and all broke together when that constant was recalibrated against
    measured data, which is a test telling you about the table rather than the function.
    """

    def _content_of(self, tokens: int) -> str:
        """Content that `estimate_tokens` reports as exactly `tokens`.

        The chars-per-token ratio is derived from `estimate_tokens` rather than restated:
        its own docstring says real tokenizers vary, and a restated 4 would silently
        mis-size this content if the estimator ever changed — the band assertions below
        would then measure the wrong ratios without going red. The result is checked
        against the estimator so a bad derivation fails loudly instead.
        """
        probe = "x" * 4096
        chars_per_token = len(probe) // estimate_tokens(probe)
        content = "x" * (tokens * chars_per_token)
        assert estimate_tokens(content) == tokens, "content sizing derivation is off"
        return content

    def _content_at(self, fraction: float) -> str:
        """Content sized at `fraction` of the skill.md budget."""
        return self._content_of(int(FORMAT_TOKEN_BUDGETS["skill.md"] * fraction))

    def test_within_budget_small_content(self) -> None:
        content = "x" * 100  # 25 tokens, far below any plausible budget
        result = check_token_budget(content, "skill.md")
        assert result["within_budget"] is True
        assert result["tokens"] == 25
        assert result["budget"] == FORMAT_TOKEN_BUDGETS["skill.md"]
        assert result["severity"] == "ok"

    def test_over_budget(self) -> None:
        """A second format, so the bands are not only exercised through skill.md."""
        budget = FORMAT_TOKEN_BUDGETS["cursorrules"]
        content = self._content_of(budget * 4)
        result = check_token_budget(content, "cursorrules")
        assert result["within_budget"] is False
        assert result["tokens"] == budget * 4
        assert result["budget"] == budget
        assert result["severity"] == "over"

    def test_severity_ok(self) -> None:
        result = check_token_budget(self._content_at(0.10), "skill.md")
        assert result["severity"] == "ok"
        assert result["ratio"] < 0.8

    def test_severity_warning(self) -> None:
        result = check_token_budget(self._content_at(0.90), "skill.md")
        assert result["severity"] == "warning"
        assert 0.8 <= result["ratio"] <= 1.0

    def test_severity_over(self) -> None:
        result = check_token_budget(self._content_at(1.50), "skill.md")
        assert result["severity"] == "over"
        assert result["ratio"] > 1.0

    def test_unknown_format_uses_default_budget(self) -> None:
        content = "x" * 100
        result = check_token_budget(content, "nonexistent_format")
        assert result["budget"] == FORMAT_TOKEN_BUDGETS["unknown"]

    def test_ratio_calculation(self) -> None:
        """Exactly at budget is ratio 1.0 and still within — `over` starts above it."""
        result = check_token_budget(self._content_at(1.0), "skill.md")
        assert result["ratio"] == 1.0
        assert result["within_budget"] is True

    def test_return_keys(self) -> None:
        result = check_token_budget("hello", "skill.md")
        assert set(result.keys()) == {"tokens", "budget", "within_budget", "ratio", "severity"}
