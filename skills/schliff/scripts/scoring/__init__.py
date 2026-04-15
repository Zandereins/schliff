"""Schliff Scoring Package — public API.

Each dimension is scored in its own module. Import everything from here
for backward compatibility with code that used the monolithic score-skill.py.
"""
from scoring.structure import score_structure
from scoring.triggers import score_triggers
from scoring.efficiency import score_efficiency
from scoring.composability import score_composability
from scoring.coherence import score_coherence  # Note: returns {bonus, details} not {score, issues, details} — used internally by quality.py
from scoring.quality import score_quality
from scoring.edges import score_edges
from scoring.runtime import score_runtime
from scoring.clarity import score_clarity
from scoring.diff import score_diff, explain_score_change
from scoring.composite import compute_composite
from scoring.structure_prompt import score_structure_prompt
from scoring.output_contract import score_output_contract
from scoring.completeness import score_completeness
