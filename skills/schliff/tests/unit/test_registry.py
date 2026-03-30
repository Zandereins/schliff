"""Tests for the scorer registry."""
import pytest


def test_registry_has_all_existing_formats():
    """All 4 instruction file formats are registered."""
    from scoring.registry import SCORER_REGISTRY
    for fmt in ["skill.md", "claude.md", "cursorrules", "agents.md"]:
        assert fmt in SCORER_REGISTRY, f"Missing format: {fmt}"


def test_registry_scorers_match_existing():
    """All 4 formats have the same 8 standard scorers."""
    from scoring.registry import SCORER_REGISTRY
    expected = ["structure", "triggers", "quality", "edges",
                "efficiency", "composability", "clarity", "security"]
    for fmt in ["skill.md", "claude.md", "cursorrules", "agents.md"]:
        assert SCORER_REGISTRY[fmt] == expected, f"Scorers mismatch for {fmt}"


def test_weight_profiles_exist_for_all_formats():
    """Every format in SCORER_REGISTRY has a weight profile."""
    from scoring.registry import SCORER_REGISTRY, WEIGHT_PROFILES
    for fmt in SCORER_REGISTRY:
        assert fmt in WEIGHT_PROFILES, f"Missing weight profile for {fmt}"


def test_weight_profiles_keys_match_scorers():
    """Weight profile keys match scorer list for each format."""
    from scoring.registry import SCORER_REGISTRY, WEIGHT_PROFILES
    for fmt in SCORER_REGISTRY:
        scorer_set = set(SCORER_REGISTRY[fmt])
        weight_set = set(WEIGHT_PROFILES[fmt].keys())
        assert weight_set == scorer_set, (
            f"Weight/scorer mismatch for {fmt}: "
            f"extra weights={weight_set - scorer_set}, "
            f"missing weights={scorer_set - weight_set}"
        )


def test_weight_profiles_are_floats():
    """All weights are floats (not ints) — A2 fix verification."""
    from scoring.registry import WEIGHT_PROFILES
    for fmt, weights in WEIGHT_PROFILES.items():
        for dim, w in weights.items():
            assert isinstance(w, float), f"{fmt}.{dim} weight is {type(w).__name__}, expected float"


def test_clarity_is_explicit_weight():
    """clarity has an explicit weight in all profiles — A3 fix verification."""
    from scoring.registry import WEIGHT_PROFILES
    for fmt, weights in WEIGHT_PROFILES.items():
        assert "clarity" in weights, f"clarity missing from {fmt} weight profile"
        assert weights["clarity"] == 0.05, f"clarity weight for {fmt} is {weights['clarity']}, expected 0.05"


def test_security_is_explicit_weight():
    """security has an explicit weight in all profiles."""
    from scoring.registry import WEIGHT_PROFILES
    for fmt, weights in WEIGHT_PROFILES.items():
        assert "security" in weights, f"security missing from {fmt} weight profile"
        assert weights["security"] == 0.08, f"security weight for {fmt} is {weights['security']}, expected 0.08"


def test_get_scorers_with_alias():
    """Aliases resolve to the correct format."""
    from scoring.registry import get_scorers
    assert get_scorers("skill") == get_scorers("skill.md")
    assert get_scorers("claude") == get_scorers("claude.md")
    assert get_scorers("cursor") == get_scorers("cursorrules")
    assert get_scorers("agents") == get_scorers("agents.md")


def test_get_scorers_unknown_format_raises():
    """Unknown format raises ValueError."""
    from scoring.registry import get_scorers
    with pytest.raises(ValueError, match="Unknown format"):
        get_scorers("nonexistent")


def test_get_weights_returns_correct_profile():
    """get_weights returns the correct profile for known formats."""
    from scoring.registry import get_weights
    w = get_weights("skill.md")
    assert w["structure"] == 0.15
    assert w["triggers"] == 0.20
    assert w["clarity"] == 0.05
    assert w["security"] == 0.08


def test_get_weights_fallback():
    """Unknown format falls back to skill.md weights."""
    from scoring.registry import get_weights
    assert get_weights("unknown_format") == get_weights("skill.md")


def test_get_all_formats():
    """get_all_formats returns sorted list of registered formats."""
    from scoring.registry import get_all_formats
    formats = get_all_formats()
    assert formats == sorted(formats)
    assert "skill.md" in formats
    assert len(formats) >= 4


def test_get_format_choices():
    """get_format_choices includes both formats and aliases."""
    from scoring.registry import get_format_choices
    choices = get_format_choices()
    assert "skill.md" in choices
    assert "skill" in choices
    assert "cursor" in choices


def test_runtime_is_opt_in():
    """runtime is in OPT_IN_DIMENSIONS, not in default scorer lists."""
    from scoring.registry import OPT_IN_DIMENSIONS, SCORER_REGISTRY
    assert "runtime" in OPT_IN_DIMENSIONS
    for fmt, scorers in SCORER_REGISTRY.items():
        assert "runtime" not in scorers, f"runtime should not be in {fmt} default scorers"


def test_get_weights_with_alias():
    """get_weights() resolves aliases correctly."""
    from scoring.registry import get_weights
    assert get_weights("skill") == get_weights("skill.md")
    assert get_weights("claude") == get_weights("claude.md")
    assert get_weights("cursor") == get_weights("cursorrules")
    assert get_weights("agents") == get_weights("agents.md")


def test_get_weights_returns_copy():
    """get_weights() returns a new dict — mutations don't affect registry."""
    from scoring.registry import get_weights
    w1 = get_weights("skill.md")
    w1.pop("security", None)
    w1["evil"] = 999
    w2 = get_weights("skill.md")
    assert "security" in w2, "Registry was mutated by pop()"
    assert "evil" not in w2, "Registry was mutated by assignment"


def test_get_scorers_returns_copy():
    """get_scorers() returns a new list — mutations don't affect registry."""
    from scoring.registry import get_scorers
    s1 = get_scorers("skill.md")
    s1.append("evil")
    s2 = get_scorers("skill.md")
    assert "evil" not in s2, "Registry was mutated by append()"


def test_registry_format_isolation():
    """Formats have independent scorer lists and weight dicts."""
    from scoring.registry import SCORER_REGISTRY, WEIGHT_PROFILES
    # Scorer lists are independent objects
    assert SCORER_REGISTRY["skill.md"] is not SCORER_REGISTRY["claude.md"], (
        "skill.md and claude.md share the same list object"
    )
    # Weight dicts are independent objects
    assert WEIGHT_PROFILES["skill.md"] is not WEIGHT_PROFILES["claude.md"], (
        "skill.md and claude.md share the same dict object"
    )
    # Mutation of one format doesn't affect another
    SCORER_REGISTRY["skill.md"].append("_test_isolation")
    assert "_test_isolation" not in SCORER_REGISTRY["claude.md"]
    SCORER_REGISTRY["skill.md"].remove("_test_isolation")


def test_weight_profiles_sum_reasonable():
    """Weight profile sums are in acceptable range (0.95-1.10)."""
    from scoring.registry import WEIGHT_PROFILES
    for fmt, weights in WEIGHT_PROFILES.items():
        total = sum(weights.values())
        assert 0.95 <= total <= 1.10, (
            f"{fmt} weights sum to {total:.2f}, expected 0.95-1.10"
        )
