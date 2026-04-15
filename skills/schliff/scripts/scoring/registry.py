"""Scorer Registry — single source of truth for scorer lists and weight profiles.

Defines which scorers run for each format and their relative weights.
All other code (build_scores, compute_composite) should derive from this registry
instead of maintaining separate hardcoded lists.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Scorer lists per format — which dimensions get scored
# ---------------------------------------------------------------------------

_INSTRUCTION_FILE_SCORERS = [
    "structure", "triggers", "quality", "edges",
    "efficiency", "composability", "clarity", "security",
]

SCORER_REGISTRY: dict[str, list[str]] = {
    "skill.md": list(_INSTRUCTION_FILE_SCORERS),
    "claude.md": list(_INSTRUCTION_FILE_SCORERS),
    "cursorrules": list(_INSTRUCTION_FILE_SCORERS),
    "agents.md": list(_INSTRUCTION_FILE_SCORERS),
    "system_prompt": [
        "structure_prompt", "output_contract", "efficiency",
        "clarity", "security", "composability", "completeness",
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
    "skill.md": dict(_INSTRUCTION_FILE_WEIGHTS),
    "claude.md": dict(_INSTRUCTION_FILE_WEIGHTS),
    "cursorrules": dict(_INSTRUCTION_FILE_WEIGHTS),
    "agents.md": dict(_INSTRUCTION_FILE_WEIGHTS),
    "system_prompt": {
        "structure_prompt": 0.15, "output_contract": 0.15, "efficiency": 0.15,
        "clarity": 0.15, "security": 0.15, "composability": 0.10, "completeness": 0.15,
    },
}

# Short aliases for --format flag
FORMAT_ALIASES: dict[str, str] = {
    "skill": "skill.md",
    "claude": "claude.md",
    "cursor": "cursorrules",
    "agents": "agents.md",
    "system-prompt": "system_prompt",
    "system_prompt": "system_prompt",
}

# Opt-in dimensions — not included in default scoring runs
OPT_IN_SCORERS: frozenset[str] = frozenset({"runtime", "security"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_scorers(fmt: str) -> list[str]:
    """Return scorer list for a format. Resolves aliases.

    Falls back to skill.md scorers for unknown formats.
    """
    resolved = FORMAT_ALIASES.get(fmt, fmt)
    return list(SCORER_REGISTRY.get(resolved, SCORER_REGISTRY["skill.md"]))


def get_weights(fmt: str) -> dict[str, float]:
    """Return weight profile for a format. Resolves aliases.

    Falls back to skill.md weights for unknown formats (forward compat).
    """
    resolved = FORMAT_ALIASES.get(fmt, fmt)
    return dict(WEIGHT_PROFILES.get(resolved, WEIGHT_PROFILES["skill.md"]))


def get_all_formats() -> list[str]:
    """Return all registered format names (no aliases)."""
    return sorted(SCORER_REGISTRY.keys())


def get_format_choices() -> list[str]:
    """Return all valid --format choices (formats + aliases)."""
    return sorted(set(list(SCORER_REGISTRY.keys()) + list(FORMAT_ALIASES.keys())))
