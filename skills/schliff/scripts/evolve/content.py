"""Content extraction, hashing, and manipulation utilities for the Evolution Engine."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Content utilities
# ---------------------------------------------------------------------------

def extract_markdown_content(llm_response: str) -> str:
    """Extract content from ```markdown fences in LLM output.

    Handles nested code fences by requiring the closing fence to be at line start.
    If no fences found, return the raw response stripped.
    """
    # Try markdown/md fences first — closing fence must be at start of line
    pattern = r"```(?:markdown|md)\s*\n(.*?)^```\s*$"
    match = re.search(pattern, llm_response, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    # Generic fences — closing fence at start of line
    generic = r"^```\s*\n(.*?)^```\s*$"
    match = re.search(generic, llm_response, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return llm_response.strip()


def content_hash(content: str) -> str:
    """SHA-256 hex digest (first 12 chars) for dedup/lineage."""
    return hashlib.sha256(content.encode(errors="replace")).hexdigest()[:12]


def grade_from_score(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 95:
        return "S"
    if score >= 85:
        return "A"
    if score >= 75:
        return "B"
    if score >= 65:
        return "C"
    if score >= 50:
        return "D"
    return "F"


_GRADE_THRESHOLDS: dict[str, float] = {
    "S": 95.0,
    "A": 85.0,
    "B": 75.0,
    "C": 65.0,
    "D": 50.0,
}


def score_to_threshold(target: str) -> float:
    """Convert grade string or numeric string to threshold float.

    Accepts letter grades (S/A/B/C/D) or numeric strings like "90.0".
    Raises ValueError for unknown grades.
    """
    upper = target.strip().upper()
    if upper in _GRADE_THRESHOLDS:
        return _GRADE_THRESHOLDS[upper]
    try:
        return float(target)
    except ValueError:
        raise ValueError(f"Unknown grade or invalid number: {target!r}")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class EvolutionConfig:
    skill_path: str
    target_score: float = 85.0
    max_generations: int = 10
    budget_tokens: int = 50_000
    min_improvement: float = 0.5
    strategy: str = "gradient"
    dimension: str | None = None
    model: str | None = None
    provider: str | None = None
    dry_run: bool = False
    json_output: bool = False
    lineage_dir: str = "~/.schliff/lineage"
    no_snapshots: bool = False
    fmt: str | None = None


@dataclass
class EvolutionResult:
    initial_score: float
    final_score: float
    initial_grade: str
    final_grade: str
    generations: int
    accepted: int
    rejected: int
    deterministic_patches: int
    tokens_used: int
    cost_usd: float
    stop_reason: str  # target_reached, budget_exhausted, plateau, max_generations, dry_run
    lineage_path: str | None = None


@dataclass
class GuardResult:
    passed: bool
    violations: list[str] = field(default_factory=list)
