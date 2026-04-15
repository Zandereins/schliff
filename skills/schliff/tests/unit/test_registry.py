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


class TestRegistryDivergence:
    """Tests that PROVE the current divergence between registry, build_scores, composite."""

    def test_build_scores_keys_match_registry(self, tmp_path):
        """build_scores() output keys should match registry scorer list for each format.

        EXPECTED TO FAIL until build_scores() is migrated to use the registry:
        - build_scores() omits 'security' (registry includes it)
        - build_scores() includes 'clarity' (registry also includes it)
        """
        from shared import build_scores

        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: test\ndescription: test skill\n---\n\n"
            "# Test\n\nDo things.\n"
        )

        scores = build_scores(str(skill), fmt="skill.md")
        registry_scorers = set(get_scorers("skill.md"))
        # Remove opt-in dimensions that are not always present
        registry_scorers -= OPT_IN_SCORERS
        score_keys = set(scores.keys())
        assert score_keys == registry_scorers, (
            f"build_scores keys {score_keys} != registry {registry_scorers}"
        )

    def test_composite_has_runtime_weight_but_registry_does_not(self):
        """Prove: composite hardcodes runtime weight=0.10 but registry has no runtime weight.

        This divergence means composite always reserves 10% weight for runtime
        even though the registry treats runtime as opt-in without a default weight.
        """
        from scoring.composite import compute_composite

        # Score all non-runtime dims — runtime is unmeasured
        scores = {
            "structure": {"score": 50, "issues": [], "details": {}},
            "triggers": {"score": 50, "issues": [], "details": {}},
            "quality": {"score": 50, "issues": [], "details": {}},
            "edges": {"score": 50, "issues": [], "details": {}},
            "efficiency": {"score": 50, "issues": [], "details": {}},
            "composability": {"score": 50, "issues": [], "details": {}},
        }
        result = compute_composite(scores)

        registry_weights = get_weights("skill.md")
        # Registry does NOT have runtime weight
        assert "runtime" not in registry_weights, (
            "Registry should not have runtime weight (it's opt-in)"
        )
        # But composite DOES have runtime in its unmeasured list (proves it expects runtime)
        assert "runtime" in result["unmeasured"], (
            "Composite should list runtime as unmeasured (it hardcodes runtime weight)"
        )

    def test_composite_lacks_security_weight_but_registry_has_it(self):
        """Prove: registry has security weight=0.05 but composite ignores security.

        This divergence means security scores from build_scores() are never
        included in the composite calculation.
        """
        from scoring.composite import compute_composite

        registry_weights = get_weights("skill.md")
        assert "security" in registry_weights, (
            "Registry should have security weight"
        )

        # Score with security included
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
        # Security is NOT in composite's weight dict, so it's ignored
        assert "security" not in result.get("confidence_notes", {}), (
            "Composite should not have security in confidence_notes (not in its weights)"
        )

    def test_composite_no_extra_weights_beyond_registry(self):
        """composite should not have weight for dimensions not in the registry weights.

        This tests that composite doesn't have 'runtime' weighted by default
        while the registry treats it as opt-in without a weight.
        """
        from scoring.composite import compute_composite

        # Score only registry-weighted (non-opt-in) dimensions
        registry_weights = get_weights("skill.md")
        non_optin = {k: v for k, v in registry_weights.items() if k not in OPT_IN_SCORERS}
        scores = {dim: {"score": 50, "issues": [], "details": {}} for dim in non_optin}

        result = compute_composite(scores)

        # All non-opt-in weighted dimensions should be measured
        for dim in non_optin:
            assert dim not in result["unmeasured"], (
                f"Registry-weighted dimension '{dim}' is unmeasured by composite"
            )
