"""Token budget tracking for evolution sessions."""
from __future__ import annotations


class BudgetTracker:
    """Track token consumption against a budget.

    budget=0 means deterministic-only mode (no LLM calls allowed).
    """

    def __init__(self, budget_tokens: int = 50000):
        self.budget = budget_tokens
        self.used = 0
        self._history: list[tuple[int, str]] = []  # (tokens, description)

    def can_afford(self, estimated_tokens: int) -> bool:
        """Check if budget allows another LLM call."""
        if self.budget == 0:
            return False
        if estimated_tokens < 0:
            return False
        return self.used + estimated_tokens <= self.budget

    def record(self, tokens: int, description: str = "") -> None:
        """Record token usage from an LLM call."""
        if tokens < 0:
            tokens = 0
        self.used += tokens
        self._history.append((tokens, description))

    @property
    def remaining(self) -> int:
        return max(0, self.budget - self.used)

    @property
    def is_exhausted(self) -> bool:
        return self.budget > 0 and self.used >= self.budget

    @property
    def is_deterministic_only(self) -> bool:
        return self.budget == 0

    def estimate_cost_usd(
        self,
        input_price_per_1m: float = 3.0,
        output_price_per_1m: float = 15.0,
    ) -> float:
        """Rough cost estimate assuming 60/40 input/output split."""
        input_tokens = int(self.used * 0.6)
        output_tokens = int(self.used * 0.4)
        return (
            input_tokens * input_price_per_1m + output_tokens * output_price_per_1m
        ) / 1_000_000
