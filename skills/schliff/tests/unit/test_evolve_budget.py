"""Tests for evolve.budget — token budget tracking."""
from evolve.budget import BudgetTracker


class TestBudgetTracker:
    def test_initial_state(self):
        bt = BudgetTracker(50000)
        assert bt.remaining == 50000
        assert bt.used == 0
        assert not bt.is_exhausted
        assert not bt.is_deterministic_only

    def test_can_afford(self):
        bt = BudgetTracker(10000)
        assert bt.can_afford(5000)
        assert bt.can_afford(10000)
        assert not bt.can_afford(10001)

    def test_record_usage(self):
        bt = BudgetTracker(10000)
        bt.record(3000, "gen 1")
        assert bt.used == 3000
        assert bt.remaining == 7000

    def test_exhaustion(self):
        bt = BudgetTracker(5000)
        bt.record(5000, "gen 1")
        assert bt.is_exhausted
        assert bt.remaining == 0
        assert not bt.can_afford(1)

    def test_zero_budget_is_deterministic(self):
        bt = BudgetTracker(0)
        assert bt.is_deterministic_only
        assert not bt.can_afford(0)  # even 0 tokens not affordable in det mode
        assert not bt.can_afford(1)

    def test_cost_estimate(self):
        bt = BudgetTracker(50000)
        bt.record(10000, "gen 1")
        cost = bt.estimate_cost_usd()
        assert cost > 0
        assert isinstance(cost, float)

    def test_remaining_never_negative(self):
        bt = BudgetTracker(100)
        bt.record(200, "over budget")
        assert bt.remaining == 0

    def test_negative_budget_treated_as_deterministic(self):
        bt = BudgetTracker(-1)
        assert not bt.can_afford(0)

    def test_cost_estimate_zero_usage(self):
        bt = BudgetTracker(50000)
        assert bt.estimate_cost_usd() == 0.0

    def test_history_tracking(self):
        bt = BudgetTracker(10000)
        bt.record(1000, "gen 1")
        bt.record(2000, "gen 2")
        assert len(bt._history) == 2
        assert bt._history[0] == (1000, "gen 1")
