"""Tests for scoring/edges.py error / malformed-input branches (TST-010).

Covers branches at edges.py lines 32, 41, 45, 76, 78, 82, 88-92, 101-105:
- eval_suite without 'edge_cases' key -> score -1
- eval_suite with empty edge_cases list -> score -1
- edge cases missing 'category' field -> graceful, no crash
- edge case 'category' is a non-string type (int) -> graceful
- edge case 'expected_behavior' as non-string (int) -> partial credit
- edge case 'assertions' missing/empty -> partial credit, no crash
- 1-case / 3-case / 4-case breakpoint scoring
"""
import pytest

from scoring.edges import score_edges


# ---------------------------------------------------------------------------
# Guard branches (lines 27-32)
# ---------------------------------------------------------------------------

def test_no_eval_suite_returns_skip():
    result = score_edges("dummy.md", None)
    assert result["score"] == -1
    assert "no_eval_suite_edge_cases" in result["issues"]


def test_eval_suite_without_edge_cases_key_returns_skip():
    result = score_edges("dummy.md", {"test_cases": []})
    assert result["score"] == -1
    assert "no_eval_suite_edge_cases" in result["issues"]


def test_empty_edge_cases_returns_skip():
    """Empty list triggers the empty_edge_cases path (line 32)."""
    result = score_edges("dummy.md", {"edge_cases": []})
    assert result["score"] == -1
    assert "empty_edge_cases" in result["issues"]


# ---------------------------------------------------------------------------
# Malformed 'category' handling
# ---------------------------------------------------------------------------

def test_edge_case_without_category_field_does_not_crash():
    """Edge cases without a 'category' key must not crash the scorer."""
    suite = {
        "edge_cases": [
            {"expected_behavior": "graceful", "assertions": [{"type": "x"}]},
            {"expected_behavior": "graceful", "assertions": [{"type": "y"}]},
        ]
    }
    result = score_edges("dummy.md", suite)
    assert isinstance(result, dict)
    assert isinstance(result["score"], int)
    # No known categories covered -> no_known_categories issue
    assert "no_known_categories" in result["issues"]
    assert result["details"]["known_categories_covered"] == []


def test_edge_case_category_as_integer_does_not_crash():
    """A non-string category value (int) must not crash .startswith() logic.

    HOST-004: the scorer must robustly ignore non-string category entries so
    malformed user-authored eval-suites cannot wedge `schliff score`.
    """
    suite = {
        "edge_cases": [
            {
                "category": 42,  # malformed — int instead of string
                "expected_behavior": "graceful",
                "assertions": [{"type": "x"}],
            }
        ]
    }
    # Must not raise. The non-string category is skipped, so it counts as
    # no known-category coverage.
    result = score_edges("dummy.md", suite)
    assert isinstance(result, dict)
    assert isinstance(result["score"], int)
    # 42 is not a string, so it never entered the category set -> no
    # known-category coverage credited.
    assert result["details"]["known_categories_covered"] == []
    assert "no_known_categories" in result["issues"]
    # Sorted categories list must be JSON-serializable (no TypeError from
    # comparing int and str).
    assert isinstance(result["details"]["categories"], list)


# ---------------------------------------------------------------------------
# Malformed 'expected_behavior' handling
# ---------------------------------------------------------------------------

def test_expected_behavior_as_integer_is_truthy(tmp_path):
    """An int expected_behavior is truthy in Python, so it counts toward the
    with_behavior bucket. The scorer must not crash and must produce a dict."""
    suite = {
        "edge_cases": [
            {
                "category": "minimal_input",
                "expected_behavior": 1,  # malformed but truthy
                "assertions": [{"type": "x"}],
            }
        ]
    }
    result = score_edges("dummy.md", suite)
    assert isinstance(result, dict)
    assert isinstance(result["score"], int)
    # One edge case -> 10 pts; 1 known category -> 8 pts;
    # expected_behavior truthy on all -> 20 pts; assertions present -> 20 pts
    assert result["details"]["with_expected_behavior"] == 1


def test_expected_behavior_zero_is_missing():
    """expected_behavior=0 is falsy -> treated as missing -> no_expected_behaviors."""
    suite = {
        "edge_cases": [
            {
                "category": "minimal_input",
                "expected_behavior": 0,
                "assertions": [{"type": "x"}],
            }
        ]
    }
    result = score_edges("dummy.md", suite)
    assert isinstance(result, dict)
    assert result["details"]["with_expected_behavior"] == 0
    assert "no_expected_behaviors" in result["issues"]


# ---------------------------------------------------------------------------
# Malformed 'assertions' handling
# ---------------------------------------------------------------------------

def test_assertions_missing_does_not_crash():
    """No 'assertions' key at all -> graceful, with_assertions=0."""
    suite = {
        "edge_cases": [
            {"category": "minimal_input", "expected_behavior": "graceful"},
        ]
    }
    result = score_edges("dummy.md", suite)
    assert isinstance(result, dict)
    assert result["details"]["with_assertions"] == 0
    assert "no_edge_assertions" in result["issues"]


def test_assertions_empty_list_does_not_crash():
    """Empty 'assertions' list -> with_assertions=0, score 0 on that axis, no crash."""
    suite = {
        "edge_cases": [
            {
                "category": "minimal_input",
                "expected_behavior": "graceful",
                "assertions": [],
            }
        ]
    }
    result = score_edges("dummy.md", suite)
    assert isinstance(result, dict)
    assert result["details"]["with_assertions"] == 0
    assert "no_edge_assertions" in result["issues"]


# ---------------------------------------------------------------------------
# Count breakpoints (lines 38-45)
# ---------------------------------------------------------------------------

def test_one_edge_case_scores_partial():
    """1 edge case -> 10 pts count bucket."""
    suite = {
        "edge_cases": [
            {
                "category": "minimal_input",
                "expected_behavior": "graceful",
                "assertions": [{"type": "x"}],
            }
        ]
    }
    result = score_edges("dummy.md", suite)
    # 10 (count) + 8 (1 known cat) + 20 (behavior) + 20 (assertions) = 58
    assert result["score"] == 58


def test_three_edge_cases_scores_mid():
    """3 edge cases -> 20 pts count bucket."""
    suite = {
        "edge_cases": [
            {
                "category": c,
                "expected_behavior": "graceful",
                "assertions": [{"type": "x"}],
            }
            for c in ["minimal_input", "invalid_path", "scale_extreme"]
        ]
    }
    result = score_edges("dummy.md", suite)
    # 20 (count) + 22 (3 known cats) + 20 + 20 = 82
    assert result["score"] == 82


def test_five_edge_cases_four_categories_scores_high():
    """5+ edge cases and 4+ known categories hit both top breakpoints."""
    cats = [
        "minimal_input",
        "invalid_path",
        "scale_extreme",
        "malformed_input",
        "unicode",
    ]
    suite = {
        "edge_cases": [
            {
                "category": c,
                "expected_behavior": "graceful",
                "assertions": [{"type": "x"}],
            }
            for c in cats
        ]
    }
    result = score_edges("dummy.md", suite)
    # 30 + 30 + 20 + 20 = 100
    assert result["score"] == 100
