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
    # AGENTS.md gets its own literal (NOT a mutation of the shared list) so the
    # operational_coverage dimension runs for agents.md only and never leaks into
    # skill.md/claude.md/cursorrules (byte-identity). See
    # docs/specs/agents-md-operational-coverage.md §5.
    "agents.md": [*_INSTRUCTION_FILE_SCORERS, "operational_coverage"],
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
    # AGENTS.md is project context for coding agents, not a reusable skill. Its
    # headline is the 3-dim operational profile: structure (0.4) + operational
    # coverage (0.4) + efficiency (0.2). operational_coverage measures whether the
    # doc actually equips a coding agent (runnable setup/build/test commands +
    # code-style/PR/gotcha guidance) and demotes efficiency, a gameable density
    # proxy. Must be an explicit literal. See
    # docs/specs/agents-md-operational-coverage.md.
    "agents.md": {"structure": 0.4, "operational_coverage": 0.4, "efficiency": 0.2},
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

# Dimensions excluded from the HEADLINE composite per format (reported as separate signals
# instead of being folded into the headline number). For the skill.md family, security is an
# opt-in side signal (weight 0.05, off by default). For system_prompt, security is a CORE
# scored dimension (weight 0.15) and MUST remain in the headline. runtime is never in the
# headline (it has no profile weight and is an opt-in side signal).
_HEADLINE_EXCLUDED_INSTRUCTION = frozenset({"security", "runtime"})
HEADLINE_EXCLUDED: dict[str, frozenset] = {
    "skill.md": _HEADLINE_EXCLUDED_INSTRUCTION,
    "claude.md": _HEADLINE_EXCLUDED_INSTRUCTION,
    "cursorrules": _HEADLINE_EXCLUDED_INSTRUCTION,
    # AGENTS.md: the eval-gated dims (triggers/quality/edges) are inapplicable to a
    # project-context file and would otherwise cap the headline + trigger a nonsensical
    # "add an eval suite" warning; composability is mis-fit SKILL semantics and clarity is
    # saturated. All five leave the denominator (exclude, not weight-0 — weight-0 keeps the
    # warning). The scorers still run as side signals. See the spec.
    "agents.md": _HEADLINE_EXCLUDED_INSTRUCTION
    | frozenset({"triggers", "quality", "edges", "composability", "clarity"}),
    "system_prompt": frozenset({"runtime"}),  # security is a core system_prompt dimension
}


def resolve_format(fmt: str) -> str:
    """Canonicalize a format name, mapping any `--format` alias to its real name.

    Every lookup below resolves aliases individually. Callers that BRANCH on the
    format string must resolve it first — a raw `fmt == "system_prompt"` compare
    silently takes the wrong path for the public `system-prompt` alias, which is
    how `security` (a core system_prompt dimension) went missing from an explicitly
    formatted score while detection kept it. Unknown names pass through unchanged
    so the existing per-format fallbacks still apply.
    """
    return FORMAT_ALIASES.get(fmt, fmt)


def get_headline_excluded(fmt: str) -> frozenset:
    """Return the dims excluded from the headline composite for a format (resolves aliases).

    Falls back to the instruction-file exclusion set for unknown formats.
    """
    return HEADLINE_EXCLUDED.get(resolve_format(fmt), _HEADLINE_EXCLUDED_INSTRUCTION)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_scorers(fmt: str) -> list[str]:
    """Return scorer list for a format. Resolves aliases.

    Falls back to skill.md scorers for unknown formats.
    """
    return list(SCORER_REGISTRY.get(resolve_format(fmt), SCORER_REGISTRY["skill.md"]))


def get_weights(fmt: str) -> dict[str, float]:
    """Return weight profile for a format. Resolves aliases.

    Falls back to skill.md weights for unknown formats (forward compat).
    """
    return dict(WEIGHT_PROFILES.get(resolve_format(fmt), WEIGHT_PROFILES["skill.md"]))


def get_all_formats() -> list[str]:
    """Return all registered format names (no aliases)."""
    return sorted(SCORER_REGISTRY.keys())


def get_format_choices() -> list[str]:
    """Return all valid --format choices (formats + aliases)."""
    return sorted(set(list(SCORER_REGISTRY.keys()) + list(FORMAT_ALIASES.keys())))
