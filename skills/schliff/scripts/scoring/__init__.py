"""Schliff Scoring Package — public API.

Each dimension is scored in its own module. Import everything from here
for backward compatibility with code that used the monolithic score-skill.py.
"""
from scoring.clarity import score_clarity
from scoring.coherence import (
    score_coherence,  # Note: returns {bonus, details} not {score, issues, details} — used internally by quality.py
)
from scoring.completeness import score_completeness
from scoring.composability import score_composability
from scoring.composite import compute_composite
from scoring.diff import explain_score_change, score_diff
from scoring.edges import score_edges
from scoring.efficiency import score_efficiency
from scoring.output_contract import score_output_contract
from scoring.quality import score_quality
from scoring.runtime import score_runtime
from scoring.structure import score_structure
from scoring.structure_prompt import score_structure_prompt
from scoring.triggers import score_triggers

__all__ = [
    "score_structure",
    "score_triggers",
    "score_efficiency",
    "score_composability",
    "score_coherence",
    "score_quality",
    "score_edges",
    "score_runtime",
    "score_clarity",
    "score_diff",
    "explain_score_change",
    "compute_composite",
    "score_structure_prompt",
    "score_output_contract",
    "score_completeness",
]
