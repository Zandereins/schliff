"""Scorer Registry — single source of truth for scorer lists and weight profiles.

Defines which scorers run for each format and their relative weights.
All other code (build_scores, compute_composite) should derive from this registry
instead of maintaining separate hardcoded lists.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Scorer lists per format — which dimensions get scored
# ---------------------------------------------------------------------------

SCORER_REGISTRY: dict[str, list[str]] = {
    "skill.md": [
        "structure", "triggers", "quality", "edges",
        "efficiency", "composability", "clarity", "security",
        # opt-in:
        "runtime",
    ],
    "claude.md": [
        "structure", "triggers", "quality", "edges",
        "efficiency", "composability", "clarity", "security",
        "runtime",
    ],
    "cursorrules": [
        "structure", "triggers", "quality", "edges",
        "efficiency", "composability", "clarity", "security",
        "runtime",
    ],
    "agents.md": [
        "structure", "triggers", "quality", "edges",
        "efficiency", "composability", "clarity", "security",
        "runtime",
    ],
    "unknown": [
        "structure", "triggers", "quality", "edges",
        "efficiency", "composability", "clarity", "security",
        "runtime",
    ],
}

# ---------------------------------------------------------------------------
# Weight profiles — how to combine dimension scores into a composite
# ---------------------------------------------------------------------------

_INSTRUCTION_FILE_WEIGHTS: dict[str, float] = {
    "structure": 0.15,
    "triggers": 0.20,
    "quality": 0.20,
    "edges": 0.15,
    "efficiency": 0.10,
    "composability": 0.10,
    "clarity": 0.05,
    "security": 0.05,
}
# Total: 1.00

WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    "skill.md": _INSTRUCTION_FILE_WEIGHTS,
    "claude.md": _INSTRUCTION_FILE_WEIGHTS,
    "cursorrules": _INSTRUCTION_FILE_WEIGHTS,
    "agents.md": _INSTRUCTION_FILE_WEIGHTS,
    "unknown": _INSTRUCTION_FILE_WEIGHTS,
}

# Opt-in dimensions — not included in default scoring runs
OPT_IN_SCORERS: frozenset[str] = frozenset({"runtime", "security"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_scorers(fmt: str) -> list[str]:
    """Return the list of scorer dimension names for a given format.

    Falls back to 'unknown' format if the requested format is not registered.
    """
    return list(SCORER_REGISTRY.get(fmt, SCORER_REGISTRY["unknown"]))


def get_weights(fmt: str) -> dict[str, float]:
    """Return the weight profile for a given format.

    Falls back to 'unknown' format if the requested format is not registered.
    """
    return dict(WEIGHT_PROFILES.get(fmt, WEIGHT_PROFILES["unknown"]))
