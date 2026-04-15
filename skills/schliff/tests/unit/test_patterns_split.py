"""Regression tests for the patterns.py -> patterns/ split.

Ensures backward compatibility: all names that were importable from
scoring.patterns before the split remain importable after.
"""
import re

import pytest

# Complete list of all public names from the original patterns.py
# Counted manually: 44 regex patterns + 1 function = 45 names
_ORIGINAL_PATTERN_NAMES = [
    # Structure
    "_RE_FRONTMATTER_NAME", "_RE_FRONTMATTER_DESC", "_RE_REAL_EXAMPLES",
    "_RE_CODE_BLOCKS", "_RE_HEADERS", "_RE_HEDGING", "_RE_REFS",
    "_RE_TODO", "_RE_SECTION_HEADER",
    # Efficiency
    "_RE_ACTIONABLE_LINES", "_RE_WHY_COUNT", "_RE_VERIFICATION_CMDS",
    "_RE_FILLER_PHRASES", "_RE_OBVIOUS_INSTRUCTIONS", "_RE_SCOPE_BOUNDARY",
    # Composability
    "_RE_POSITIVE_SCOPE", "_RE_NEGATIVE_SCOPE", "_RE_GLOBAL_STATE",
    "_RE_INPUT_SPEC", "_RE_OUTPUT_SPEC", "_RE_HANDOFF", "_RE_WHEN_NOT",
    "_RE_HARD_REQUIREMENTS", "_RE_ALTERNATIVES", "_RE_ERROR_BEHAVIOR",
    "_RE_IDEMPOTENCY", "_RE_DEPENDENCY_DECL", "_RE_NAMESPACE_ISOLATION",
    "_RE_VERSION_COMPAT",
    # Clarity
    "_RE_ALWAYS_PATTERNS", "_RE_NEVER_PATTERNS", "_RE_VAGUE_REF",
    "_RE_BACKTICK_REF", "_RE_SPECIFIC_REF", "_RE_AMBIGUOUS_PRONOUN",
    "_RE_RUN_PATTERN", "_RE_CONCEPTUAL", "_RE_CONCRETE_CMD",
    "_RE_CODE_BLOCK_START",
    # Triggers
    "_RE_CREATION_PATTERNS", "_RE_NEGATION_BOUNDARIES",
    "_RE_STRONG_DOMAIN_SIGNAL", "_RE_ANTI_DOMAIN_SIGNAL",
    # Diff
    "_RE_DIFF_SIGNAL", "_RE_DIFF_EXAMPLE", "_RE_DIFF_NOISE",
    # Coherence
    "_RE_IMPERATIVE_INSTRUCTION", "_RE_CODE_BLOCK_REGION",
    # Security
    "_RE_SEC_PROMPT_INJECTION", "_RE_SEC_INSTRUCTION_OVERRIDE",
    "_RE_SEC_DATA_EXFIL", "_RE_SEC_ENV_LEAK", "_RE_SEC_DANGEROUS_CMD",
    "_RE_SEC_BASE64_CMD", "_RE_SEC_ZERO_WIDTH", "_RE_SEC_HEX_ESCAPE",
    "_RE_SEC_OVERPERMISSION", "_RE_SEC_BOUNDARY_VIOLATION",
    # Function
    "_has_skill_domain_signal",
]


def test_patterns_backward_compat_import():
    """All original names importable from scoring.patterns after split."""
    import scoring.patterns as patterns_pkg
    missing = []
    for name in _ORIGINAL_PATTERN_NAMES:
        if not hasattr(patterns_pkg, name):
            missing.append(name)
    assert not missing, f"Names missing from scoring.patterns: {missing}"


def test_base_patterns_importable():
    """All base (format-agnostic) patterns importable from scoring.patterns.base."""
    from scoring.patterns import base
    # Spot-check key base patterns
    assert hasattr(base, "_RE_FILLER_PHRASES")
    assert hasattr(base, "_RE_SEC_PROMPT_INJECTION")
    assert hasattr(base, "_RE_DIFF_SIGNAL")
    assert hasattr(base, "_RE_ALWAYS_PATTERNS")


def test_skill_md_patterns_importable():
    """All SKILL.md-specific patterns importable from scoring.patterns.skill_md."""
    from scoring.patterns import skill_md
    assert hasattr(skill_md, "_RE_FRONTMATTER_NAME")
    assert hasattr(skill_md, "_RE_POSITIVE_SCOPE")
    assert hasattr(skill_md, "_has_skill_domain_signal")


def test_no_pattern_lost():
    """Total pattern count across base + skill_md >= original count."""
    from scoring.patterns import base, skill_md
    base_names = [n for n in dir(base) if n.startswith("_RE_") or n == "_has_skill_domain_signal"]
    skill_names = [n for n in dir(skill_md) if n.startswith("_RE_") or n == "_has_skill_domain_signal"]
    total = len(set(base_names + skill_names))
    assert total >= len(_ORIGINAL_PATTERN_NAMES), (
        f"Pattern count dropped: {total} < {len(_ORIGINAL_PATTERN_NAMES)}"
    )


def test_patterns_are_compiled_regex():
    """All _RE_* names are compiled regex pattern objects."""
    import scoring.patterns as patterns_pkg
    for name in _ORIGINAL_PATTERN_NAMES:
        if name.startswith("_RE_"):
            obj = getattr(patterns_pkg, name)
            assert isinstance(obj, re.Pattern), f"{name} is {type(obj)}, expected re.Pattern"


def test_domain_signal_function_works():
    """_has_skill_domain_signal returns expected multipliers."""
    from scoring.patterns import _has_skill_domain_signal
    assert _has_skill_domain_signal("improve my skill") == 1.8
    assert _has_skill_domain_signal("generic text") == 1.0
    assert _has_skill_domain_signal("python function .py") == 0.2


def test_score_regression_skill_md():
    """SKILL.md composite score unchanged after patterns split.

    Golden score: 99.0 (from docs/golden/v7.1.0-skill-score.json)
    """
    from pathlib import Path

    from scoring.composite import compute_composite
    from shared import build_scores, load_eval_suite

    skill_path = str(Path(__file__).resolve().parent.parent.parent / "SKILL.md")
    eval_suite = load_eval_suite(skill_path)
    scores = build_scores(skill_path, eval_suite=eval_suite)
    result = compute_composite(scores)
    assert result["score"] == pytest.approx(99.0, abs=0.1), (
        f"Score regression: expected ~99.0, got {result['score']}"
    )


def test_base_and_skill_md_no_name_collision():
    """base.__all__ and skill_md.__all__ have no overlapping names."""
    from scoring.patterns.base import __all__ as base_all
    from scoring.patterns.skill_md import __all__ as skill_all
    overlap = set(base_all) & set(skill_all)
    assert not overlap, f"Name collision between base and skill_md: {overlap}"


def test_pattern_flags_preserved():
    """Key patterns retain their regex flags after split."""
    import re

    from scoring.patterns import (
        _RE_ACTIONABLE_LINES,
        _RE_FILLER_PHRASES,
        _RE_FRONTMATTER_NAME,
        _RE_HEADERS,
        _RE_HEDGING,
    )
    assert _RE_HEADERS.flags & re.MULTILINE, "_RE_HEADERS missing MULTILINE"
    assert _RE_ACTIONABLE_LINES.flags & re.MULTILINE, "_RE_ACTIONABLE_LINES missing MULTILINE"
    assert _RE_FILLER_PHRASES.flags & re.IGNORECASE, "_RE_FILLER_PHRASES missing IGNORECASE"
    assert _RE_FRONTMATTER_NAME.flags & re.MULTILINE, "_RE_FRONTMATTER_NAME missing MULTILINE"
    assert _RE_HEDGING.flags & re.IGNORECASE, "_RE_HEDGING missing IGNORECASE"
