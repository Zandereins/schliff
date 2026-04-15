"""EMA-based plateau detection for evolution convergence."""
from __future__ import annotations


class PlateauDetector:
    """Detect when score improvements have stagnated.

    Uses Exponential Moving Average of score deltas.
    Triggers escape strategies: strategy switch -> temperature bump -> stop.
    """

    def __init__(
        self,
        window: int = 5,
        min_improvement: float = 0.5,
        alpha: float = 0.3,
        max_consecutive_rejections: int = 10,
    ):
        self.window = window
        self.min_improvement = min_improvement
        self.alpha = alpha
        self.max_consecutive_rejections = max_consecutive_rejections
        self.ema_delta: float = 0.0
        self.stale_count: int = 0
        self.consecutive_rejections: int = 0
        self.previous: float | None = None
        self._escape_level: int = 0  # 0=none, 1=strategy_switch, 2=temp_bump, 3=stop

    def record_rejection(self) -> None:
        """Record a rejected generation. Consecutive rejections trigger plateau."""
        self.consecutive_rejections += 1
        if self.consecutive_rejections >= self.max_consecutive_rejections:
            self.stale_count = self.window  # force plateau state

    def update(self, score: float) -> None:
        """Update with accepted score. Resets rejection counter."""
        self.consecutive_rejections = 0  # acceptance breaks rejection streak
        if self.previous is not None:
            delta = score - self.previous
            self.ema_delta = self.alpha * delta + (1 - self.alpha) * self.ema_delta
            if self.ema_delta < self.min_improvement:
                self.stale_count += 1
            else:
                self.stale_count = 0
                self._escape_level = 0  # reset escape on real improvement
        self.previous = score

    @property
    def is_plateau(self) -> bool:
        return self.stale_count >= self.window

    def get_escape_strategy(self) -> str | None:
        """Get the next escape strategy to try, or None if should stop.

        Escape sequence:
          1. Switch strategy (gradient -> holistic) -- try 2 more gens
          2. Temperature bump (0.3 -> 0.6) -- try 2 more gens
          3. None -- plateau is real, stop
        """
        if not self.is_plateau:
            return None

        self._escape_level += 1
        self.stale_count = 0  # reset for escape attempt

        if self._escape_level == 1:
            return "strategy_switch"
        elif self._escape_level == 2:
            return "temperature_bump"
        else:
            return None  # give up

    def reset(self) -> None:
        """Full reset for a new session."""
        self.ema_delta = 0.0
        self.stale_count = 0
        self.consecutive_rejections = 0
        self.previous = None
        self._escape_level = 0
