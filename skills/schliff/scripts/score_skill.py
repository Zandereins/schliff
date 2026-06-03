"""score_skill — Python import facade for the scoring package.

Enables `import score_skill` as before, backed by the scoring/ package.
"""
from scoring import (
    compute_composite,
    explain_score_change,
    score_clarity,
    score_composability,
    score_diff,
    score_edges,
    score_efficiency,
    score_quality,
    score_runtime,
    score_structure,
    score_triggers,
)
from shared import extract_description, invalidate_cache, read_skill_safe

__all__ = [
    "score_structure",
    "score_triggers",
    "score_efficiency",
    "score_composability",
    "score_quality",
    "score_edges",
    "score_runtime",
    "score_clarity",
    "score_diff",
    "explain_score_change",
    "compute_composite",
    "invalidate_cache",
    "read_skill_safe",
    "extract_description",
]
