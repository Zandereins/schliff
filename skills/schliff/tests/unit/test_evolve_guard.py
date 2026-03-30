"""Tests for evolve.guard — dimension guard and security guard."""
from evolve.guard import dimension_guard, security_guard


class TestDimensionGuard:
    def test_all_improved_passes(self):
        old = {"structure": {"score": 70}, "triggers": {"score": 60}}
        new = {"structure": {"score": 75}, "triggers": {"score": 65}}
        result = dimension_guard(old, new)
        assert result.passed
        assert result.violations == []

    def test_small_drop_within_threshold(self):
        old = {"structure": {"score": 70}, "triggers": {"score": 60}}
        new = {"structure": {"score": 68}, "triggers": {"score": 65}}
        result = dimension_guard(old, new, threshold=3.0)
        assert result.passed

    def test_large_drop_rejected(self):
        old = {"structure": {"score": 70}, "triggers": {"score": 60}}
        new = {"structure": {"score": 65}, "triggers": {"score": 65}}
        result = dimension_guard(old, new, threshold=3.0)
        assert not result.passed
        assert len(result.violations) == 1
        assert "structure" in result.violations[0]

    def test_unmeasured_old_skipped(self):
        old = {"structure": {"score": -1}, "triggers": {"score": 60}}
        new = {"structure": {"score": 50}, "triggers": {"score": 60}}
        result = dimension_guard(old, new)
        assert result.passed

    def test_unmeasured_new_is_violation(self):
        old = {"structure": {"score": 70}}
        new = {"structure": {"score": -1}}
        result = dimension_guard(old, new)
        assert not result.passed
        assert "unmeasured" in result.violations[0]

    def test_empty_scores_passes(self):
        result = dimension_guard({}, {})
        assert result.passed

    def test_custom_threshold(self):
        old = {"structure": {"score": 70}}
        new = {"structure": {"score": 67.5}}
        assert dimension_guard(old, new, threshold=2.0).passed is False
        assert dimension_guard(old, new, threshold=3.0).passed is True

    def test_multiple_violations(self):
        old = {"a": {"score": 80}, "b": {"score": 70}, "c": {"score": 60}}
        new = {"a": {"score": 70}, "b": {"score": 60}, "c": {"score": 65}}
        result = dimension_guard(old, new, threshold=5.0)
        assert not result.passed
        assert len(result.violations) == 2


class TestSecurityGuard:
    def test_security_improved_passes(self):
        old = {"security": {"score": 80}}
        new = {"security": {"score": 85}}
        result = security_guard(old, new)
        assert result.passed

    def test_security_unchanged_passes(self):
        old = {"security": {"score": 80}}
        new = {"security": {"score": 80}}
        result = security_guard(old, new)
        assert result.passed

    def test_any_security_drop_rejected(self):
        old = {"security": {"score": 80}}
        new = {"security": {"score": 79.9}}
        result = security_guard(old, new)
        assert not result.passed

    def test_security_not_measured_passes(self):
        old = {"security": {"score": -1}}
        new = {"security": {"score": 50}}
        result = security_guard(old, new)
        assert result.passed

    def test_security_missing_from_old(self):
        result = security_guard({}, {"security": {"score": 80}})
        assert result.passed

    def test_security_became_unmeasured_rejected(self):
        old = {"security": {"score": 80}}
        new = {"security": {"score": -1}}
        result = security_guard(old, new)
        assert not result.passed


class TestGuardBranchCoverage:
    def test_old_result_not_dict_skipped(self):
        """Non-dict values in old_scores should be silently skipped."""
        old = {"dim": "not_a_dict"}
        new = {"dim": {"score": 50}}
        result = dimension_guard(old, new)
        assert result.passed

    def test_new_result_not_dict_is_violation(self):
        """Non-dict values in new_scores should be a violation."""
        old = {"dim": {"score": 70}}
        new = {"dim": "invalid"}
        result = dimension_guard(old, new)
        assert not result.passed
        assert "missing/invalid" in result.violations[0]


class TestSecurityGuardBranchCoverage:
    def test_old_not_dict_passes(self):
        old = {"security": "not_dict"}
        new = {"security": {"score": 80}}
        result = security_guard(old, new)
        assert result.passed

    def test_new_not_dict_rejected(self):
        old = {"security": {"score": 80}}
        new = {"security": "broken"}
        result = security_guard(old, new)
        assert not result.passed
