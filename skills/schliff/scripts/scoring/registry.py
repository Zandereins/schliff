"""Scorer Registry — format-to-scorer mapping and weight profiles.

Single source of truth for which scorers run per format and their weights.
Phase 1a: instruction file formats only. Phase 1b/1c add system_prompt, mcp_tool.
"""
from __future__ import annotations

# Shared scorer list and weight profile for all instruction-file formats
_INSTRUCTION_FILE_SCORERS = [
    "structure", "triggers", "quality", "edges",
    "efficiency", "composability", "clarity", "security",
]

# NOTE: weights sum to 1.03 — existing renormalization in composite.py handles this
# clarity is EXPLICIT here (was dynamically injected before — A3 fix)
# runtime is opt-in (not in default weights — A4 fix)
_INSTRUCTION_FILE_WEIGHTS = {
    "structure": 0.15, "triggers": 0.20, "quality": 0.20,
    "edges": 0.15, "efficiency": 0.10, "composability": 0.10,
    "clarity": 0.05, "security": 0.08,
}

# Which scorers run for each format
SCORER_REGISTRY: dict[str, list[str]] = {
    "skill.md": list(_INSTRUCTION_FILE_SCORERS),
    "claude.md": list(_INSTRUCTION_FILE_SCORERS),
    "cursorrules": list(_INSTRUCTION_FILE_SCORERS),
    "agents.md": list(_INSTRUCTION_FILE_SCORERS),
    # Phase 1b:
    "system_prompt": [
        "structure_prompt", "output_contract", "efficiency",
        "clarity", "security", "composability", "completeness",
    ],
    # Phase 1c:
    # "mcp_tool": [
    #     "schema_quality", "trigger_alignment", "efficiency",
    #     "clarity", "security", "composability",
    # ],
}

# Weight profiles per format — FLOATS matching existing code in composite.py
WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    "skill.md": dict(_INSTRUCTION_FILE_WEIGHTS),
    "claude.md": dict(_INSTRUCTION_FILE_WEIGHTS),
    "cursorrules": dict(_INSTRUCTION_FILE_WEIGHTS),
    "agents.md": dict(_INSTRUCTION_FILE_WEIGHTS),
    # Phase 1b:
    "system_prompt": {
        "structure_prompt": 0.15, "output_contract": 0.15, "efficiency": 0.15,
        "clarity": 0.15, "security": 0.15, "composability": 0.10, "completeness": 0.15,
    },
    # Phase 1c:
    # "mcp_tool": {
    #     "schema_quality": 0.25, "trigger_alignment": 0.20, "efficiency": 0.15,
    #     "clarity": 0.15, "security": 0.15, "composability": 0.10,
    # },
}

# Short aliases for --format flag
FORMAT_ALIASES: dict[str, str] = {
    "skill": "skill.md",
    "claude": "claude.md",
    "cursor": "cursorrules",
    "agents": "agents.md",
    "system-prompt": "system_prompt",
    "system_prompt": "system_prompt",
    # "mcp-tool": "mcp_tool",
    # "mcp_tool": "mcp_tool",
}

# Opt-in dimensions (not included in default weight profiles)
OPT_IN_DIMENSIONS: set[str] = {"runtime"}


def get_scorers(fmt: str) -> list[str]:
    """Return scorer list for a format. Resolves aliases.

    Raises ValueError for unknown formats.
    """
    resolved = FORMAT_ALIASES.get(fmt, fmt)
    if resolved not in SCORER_REGISTRY:
        raise ValueError(
            f"Unknown format: {fmt!r}. "
            f"Valid formats: {', '.join(sorted(SCORER_REGISTRY))}. "
            f"Valid aliases: {', '.join(sorted(FORMAT_ALIASES))}."
        )
    return list(SCORER_REGISTRY[resolved])


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
