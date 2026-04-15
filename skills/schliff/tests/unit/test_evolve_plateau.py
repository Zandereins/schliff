"""Tests for evolve.plateau — EMA plateau detection."""
from evolve.plateau import PlateauDetector


class TestPlateauDetector:
    def test_no_plateau_with_improvement(self):
        pd = PlateauDetector(window=3, min_improvement=0.5)
        for score in [60, 65, 70, 75, 80]:
            pd.update(score)
        assert not pd.is_plateau

    def test_plateau_on_stagnation(self):
        pd = PlateauDetector(window=3, min_improvement=0.5)
        pd.update(70.0)
        for _ in range(5):
            pd.update(70.1)  # tiny improvement, below min_improvement
        assert pd.is_plateau

    def test_escape_strategy_sequence(self):
        pd = PlateauDetector(window=2, min_improvement=1.0)
        pd.update(70.0)
        pd.update(70.0)
        pd.update(70.0)  # now stale_count=2, window=2 → plateau

        assert pd.is_plateau
        escape1 = pd.get_escape_strategy()
        assert escape1 == "strategy_switch"

        # After escape, stale_count is reset, needs to re-plateau
        pd.update(70.0)
        pd.update(70.0)
        assert pd.is_plateau
        escape2 = pd.get_escape_strategy()
        assert escape2 == "temperature_bump"

        pd.update(70.0)
        pd.update(70.0)
        assert pd.is_plateau
        escape3 = pd.get_escape_strategy()
        assert escape3 is None  # give up

    def test_real_improvement_resets_escape(self):
        pd = PlateauDetector(window=2, min_improvement=0.5)
        pd.update(70.0)
        pd.update(70.0)
        pd.update(70.0)
        assert pd.is_plateau
        pd.get_escape_strategy()  # strategy_switch

        # Real improvement resets escape level
        pd.update(80.0)
        pd.update(85.0)
        # Should not be plateau anymore
        assert not pd.is_plateau

    def test_first_update_no_crash(self):
        pd = PlateauDetector()
        pd.update(50.0)  # first update, no previous
        assert not pd.is_plateau

    def test_reset(self):
        pd = PlateauDetector(window=2)
        pd.update(70.0)
        pd.update(70.0)
        pd.update(70.0)
        pd.reset()
        assert not pd.is_plateau
        assert pd.previous is None

    def test_record_rejection_increments_counter(self):
        pd = PlateauDetector(window=3)
        pd.update(70.0)  # initial
        pd.record_rejection()
        assert pd.consecutive_rejections == 1

    def test_consecutive_rejections_trigger_plateau(self):
        pd = PlateauDetector(window=3, max_consecutive_rejections=5)
        pd.update(70.0)
        for _ in range(5):
            pd.record_rejection()
        assert pd.is_plateau

    def test_acceptance_resets_rejection_counter(self):
        pd = PlateauDetector(window=3, max_consecutive_rejections=10)
        pd.update(70.0)
        for _ in range(5):
            pd.record_rejection()
        pd.update(75.0)  # acceptance
        assert pd.consecutive_rejections == 0

    def test_rejection_plateau_uses_escape_sequence(self):
        pd = PlateauDetector(window=2, max_consecutive_rejections=3)
        pd.update(70.0)
        for _ in range(3):
            pd.record_rejection()
        assert pd.is_plateau
        escape = pd.get_escape_strategy()
        assert escape == "strategy_switch"

    def test_reset_clears_rejections(self):
        pd = PlateauDetector()
        pd.update(70.0)
        pd.record_rejection()
        pd.reset()
        assert pd.consecutive_rejections == 0
