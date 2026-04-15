"""Tests documenting and verifying registry/build_scores/composite alignment.

These tests prove the current divergence between the three sources of truth:
1. scoring.registry — canonical scorer lists and weight profiles
2. shared.build_scores() — hardcoded scorer lists
3. scoring.composite — hardcoded fallback weight dict
"""
import pytest

from scoring.registry import get_scorers, get_weights, SCORER_REGISTRY, WEIGHT_PROFILES, OPT_IN_SCORERS


class TestRegistryIntegrity:
    """Tests for the registry's own internal consistency."""

    def test_registry_weights_cover_all_scorers(self):
        """Every scorer in SCORER_REGISTRY must have a weight in WEIGHT_PROFILES."""
        for fmt, scorers in SCORER_REGISTRY.items():
            weights = WEIGHT_PROFILES.get(fmt, {})
            for scorer in scorers:
                if scorer in OPT_IN_SCORERS and scorer not in weights:
                    continue  # opt-in scorers like runtime may lack weights
                assert scorer in weights, (
                    f"Scorer '{scorer}' has no weight for format '{fmt}'"
                )

    def test_registry_weights_sum_close_to_one(self):
        """Weight profiles should sum approximately to 1.0."""
        for fmt, weights in WEIGHT_PROFILES.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.01, (
                f"Weights for '{fmt}' sum to {total}, expected ~1.0"
            )

    def test_get_scorers_returns_list(self):
        """get_scorers() must return a list for known formats."""
        for fmt in SCORER_REGISTRY:
            result = get_scorers(fmt)
            assert isinstance(result, list)
            assert len(result) > 0

    def test_get_scorers_unknown_format_falls_back(self):
        """get_scorers() for unknown format must fall back gracefully."""
        result = get_scorers("nonexistent_format")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_weights_returns_dict(self):
        """get_weights() must return a dict for known formats."""
        for fmt in WEIGHT_PROFILES:
            result = get_weights(fmt)
            assert isinstance(result, dict)
            assert len(result) > 0

    def test_get_weights_unknown_format_falls_back(self):
        """get_weights() for unknown format must fall back gracefully."""
        result = get_weights("nonexistent_format")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_get_scorers_returns_copy(self):
        """get_scorers() must return a copy, not a reference to the registry."""
        result = get_scorers("skill.md")
        result.append("hacked")
        assert "hacked" not in get_scorers("skill.md")

    def test_get_weights_returns_copy(self):
        """get_weights() must return a copy, not a reference to the registry."""
        result = get_weights("skill.md")
        result["hacked"] = 99.0
        assert "hacked" not in get_weights("skill.md")


class TestRegistryAlignment:
    """Tests verifying that build_scores, composite, and registry are aligned."""

    def test_build_scores_keys_match_registry(self, tmp_path):
        """build_scores() output keys should match registry scorer list (minus opt-in)."""
        from shared import build_scores

        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: test\ndescription: test skill\n---\n\n"
            "# Test\n\nDo things.\n"
        )

        scores = build_scores(str(skill), fmt="skill.md")
        registry_scorers = set(get_scorers("skill.md"))
        registry_scorers -= OPT_IN_SCORERS
        score_keys = set(scores.keys())
        assert score_keys == registry_scorers, (
            f"build_scores keys {score_keys} != registry {registry_scorers}"
        )

    def test_build_scores_with_security_matches_registry(self, tmp_path):
        """build_scores(include_security=True) includes security from registry."""
        from shared import build_scores

        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: test\ndescription: test skill\n---\n\n"
            "# Test\n\nDo things.\n"
        )

        scores = build_scores(str(skill), fmt="skill.md", include_security=True)
        assert "security" in scores

    def test_composite_uses_registry_weights(self):
        """compute_composite() weights come from the registry — no hardcoded fallbacks."""
        from scoring.composite import compute_composite

        registry_weights = get_weights("skill.md")
        scores = {dim: {"score": 50, "issues": [], "details": {}} for dim in registry_weights}
        result = compute_composite(scores)

        # All registry-weighted dimensions should be measured
        assert result["measured_dimensions"] == len(registry_weights)
        assert len(result["unmeasured"]) == 0
        assert abs(result["weight_coverage"] - 1.0) < 1e-6

    def test_composite_does_not_have_runtime_weight(self):
        """Runtime is opt-in and has no default weight in the registry."""
        registry_weights = get_weights("skill.md")
        assert "runtime" not in registry_weights

    def test_composite_has_clarity_and_security_weights(self):
        """Clarity and security are explicit in registry weights."""
        registry_weights = get_weights("skill.md")
        assert "clarity" in registry_weights
        assert "security" in registry_weights

    def test_composite_security_is_measured_when_scored(self):
        """Security scores flow through composite correctly via registry weights."""
        from scoring.composite import compute_composite

        scores = {
            "structure": {"score": 50, "issues": [], "details": {}},
            "triggers": {"score": 50, "issues": [], "details": {}},
            "quality": {"score": 50, "issues": [], "details": {}},
            "edges": {"score": 50, "issues": [], "details": {}},
            "efficiency": {"score": 50, "issues": [], "details": {}},
            "composability": {"score": 50, "issues": [], "details": {}},
            "security": {"score": 100, "issues": [], "details": {}},
        }
        result = compute_composite(scores)
        # Security is in registry weights, so it should be measured
        assert "security" not in result["unmeasured"]

    def test_all_registry_weighted_dims_measured_by_composite(self):
        """Every dimension with a registry weight must be recognized by composite."""
        from scoring.composite import compute_composite

        registry_weights = get_weights("skill.md")
        scores = {dim: {"score": 50, "issues": [], "details": {}} for dim in registry_weights}
        result = compute_composite(scores)

        for dim in registry_weights:
            assert dim not in result["unmeasured"], (
                f"Registry-weighted dimension '{dim}' is unmeasured by composite"
            )
