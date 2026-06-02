#!/usr/bin/env python3
"""Schliff Verify — CI exit-code wrapper for skill scoring.

Scores a SKILL.md, compares against a threshold or previous score,
and exits with an appropriate code for CI/CD pipelines.

Exit codes:
    0 = pass (score >= threshold, no regression)
    1 = fail (score < threshold or regression detected)
    2 = error (file not found, scorer crash)

Usage:
    schliff verify path/to/SKILL.md                    # exit 0 if >= 75
    schliff verify path/to/SKILL.md --min-score 85     # custom threshold
    schliff verify path/to/SKILL.md --regression       # exit 1 if score dropped
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from terminal_art import score_to_grade

# History file: one JSON object per line
_DEFAULT_HISTORY = ".schliff/history.jsonl"
_DEFAULT_MIN_SCORE = 75.0


def _score_skill(skill_path: str, eval_suite: Optional[dict] = None) -> dict:
    """Run the full scorer on a skill. Returns composite dict + per-dim scores.

    Reuses the same scoring functions as `schliff score`.
    """
    from scoring import (
        score_structure, score_triggers, score_efficiency,
        score_composability, score_quality, score_edges,
        score_runtime, score_clarity, compute_composite,
    )

    scores = {
        "structure": score_structure(skill_path),
        "triggers": score_triggers(skill_path, eval_suite),
        "quality": score_quality(skill_path, eval_suite),
        "edges": score_edges(skill_path, eval_suite),
        "efficiency": score_efficiency(skill_path),
        "composability": score_composability(skill_path),
        "clarity": score_clarity(skill_path),
        "runtime": score_runtime(skill_path, eval_suite, enabled=False),
    }

    composite = compute_composite(scores)

    return {
        "composite": composite["score"],
        "grade": score_to_grade(composite["score"]),
        "dimensions": {k: v["score"] for k, v in scores.items()},
        "warnings": composite["warnings"],
        "score_type": composite.get("score_type", "structural"),
        "weight_coverage": composite.get("weight_coverage", 0.0),
    }


def load_last_score(skill_path: str, history_path: str = _DEFAULT_HISTORY) -> Optional[float]:
    """Load the most recent composite score for a skill from history.

    Reads the file backwards (last line first) to find the latest entry
    matching the given skill path. Returns None if no history exists.
    """
    entry = load_last_entry(skill_path, history_path)
    if entry is None:
        return None
    return entry[0]


def load_last_entry(
    skill_path: str, history_path: str = _DEFAULT_HISTORY
) -> Optional[tuple]:
    """Load the latest (composite, weight_coverage) for a skill from history.

    Returns a (composite, coverage) tuple, where coverage is None for legacy
    entries written before weight_coverage was recorded. Returns None if no
    matching history exists. Comparing coverage-normalized scores lets the
    regression gate judge per-measured-dimension quality rather than raw
    composites, which are capped at each run's weight coverage.
    """
    hp = Path(history_path)
    if not hp.exists():
        return None

    # Normalize for comparison
    norm_path = str(Path(skill_path).resolve())

    try:
        lines = hp.read_text(encoding="utf-8").strip().splitlines()
    except OSError:
        return None

    # Search from newest to oldest
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            val = entry.get("composite")
            if val is None:
                continue
            entry_path = entry.get("skill_path", "")
            if str(Path(entry_path).resolve()) == norm_path:
                cov = entry.get("weight_coverage")
                cov = float(cov) if cov is not None else None
                return (float(val), cov)
        except (json.JSONDecodeError, ValueError, TypeError, OSError):
            continue
    return None


def append_history(
    skill_path: str,
    result: dict,
    history_path: str = _DEFAULT_HISTORY,
) -> None:
    """Append a score entry to the history file.

    Uses fcntl.flock for safe concurrent writes from parallel CI jobs.
    """
    hp = Path(history_path)
    hp.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "skill_path": str(Path(skill_path).resolve()),
        "composite": result["composite"],
        "grade": result["grade"],
        "dimensions": result["dimensions"],
        "weight_coverage": result.get("weight_coverage"),
    }

    line = json.dumps(entry, separators=(",", ":")) + "\n"
    try:
        import fcntl
        with open(hp, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(line)
            # Lock released on close
    except (ImportError, OSError):
        # fcntl unavailable on Windows — fall back to unlocked append
        with open(hp, "a", encoding="utf-8") as f:
            f.write(line)


def run_verify(
    skill_path: str,
    min_score: float = _DEFAULT_MIN_SCORE,
    check_regression: bool = False,
    history_path: str = _DEFAULT_HISTORY,
    eval_suite: Optional[dict] = None,
) -> dict:
    """Run verify logic. Returns a result dict with verdict and exit_code.

    Exit codes: 0 = pass, 1 = fail/regression, 2 = error.
    Does NOT call sys.exit — caller decides what to do with exit_code.
    """
    _error_verdict = {
        "skill_path": skill_path, "composite": 0.0, "grade": "F",
        "dimensions": {}, "min_score": min_score,
        "coverage": 0.0, "effective_min": min_score,
        "passed_threshold": False, "exit_code": 2, "message": "",
        "previous_score": None, "delta": None, "regression": False,
    }

    if not Path(skill_path).exists():
        _error_verdict["message"] = f"ERROR: file not found: {skill_path}"
        return _error_verdict

    try:
        result = _score_skill(skill_path, eval_suite)
    except Exception as e:
        _error_verdict["message"] = f"ERROR: scoring failed: {e}"
        return _error_verdict
    composite = result["composite"]
    grade = result["grade"]

    # Coverage-aware threshold: a skill without an eval suite has unmeasured
    # dimensions, so its composite is capped at its weight coverage. Scaling the
    # threshold by coverage judges the per-measured-dimension quality
    # (composite / coverage) against min_score. An eval-suite skill reaches
    # coverage→1.0 and is held to the full min_score across all dimensions.
    coverage = float(result.get("weight_coverage", 0.0))
    if coverage <= 0:
        # No measured dimensions — nothing to credit. Keep the full bar so we
        # never pass an unscoreable skill (and never divide by zero downstream).
        effective_min = min_score
    else:
        effective_min = round(min_score * coverage, 1)

    verdict: dict = {
        "skill_path": skill_path,
        "composite": composite,
        "grade": grade,
        "dimensions": result["dimensions"],
        "min_score": min_score,
        "coverage": coverage,
        "effective_min": effective_min,
        "passed_threshold": composite >= effective_min,
        "exit_code": 0,
        "message": "",
        "previous_score": None,
        "delta": None,
        "regression": False,
    }

    # Threshold check (coverage-aware)
    if composite < effective_min:
        verdict["exit_code"] = 1
        verdict["message"] = (
            f"FAIL: {composite}/100 [{grade}] < effective minimum {effective_min} "
            f"(min {min_score} x coverage {coverage:.0%})"
        )
        # Still record history even on failure
        append_history(skill_path, result, history_path)
        return verdict

    # Regression check
    if check_regression:
        prev_entry = load_last_entry(skill_path, history_path)
        previous = prev_entry[0] if prev_entry is not None else None
        verdict["previous_score"] = previous
        if previous is not None:
            # Raw composites are capped at each run's weight coverage, so a run
            # with a different eval-suite-presence regime is not comparable to a
            # prior raw composite. Compare per-measured-dimension quality
            # (composite / coverage) when both coverages are known; fall back to
            # raw deltas for legacy entries lacking a recorded coverage.
            prev_coverage = prev_entry[1]
            if prev_coverage is not None and prev_coverage > 0 and coverage > 0:
                norm_current = composite / coverage
                norm_previous = previous / prev_coverage
                delta = round(norm_current - norm_previous, 1)
            else:
                delta = round(composite - previous, 1)
            verdict["delta"] = delta
            if delta < 0:
                verdict["regression"] = True
                verdict["exit_code"] = 1
                verdict["message"] = (
                    f"REGRESSION: {previous} -> {composite} ({delta:+.1f})"
                )
                append_history(skill_path, result, history_path)
                return verdict
            else:
                verdict["message"] = (
                    f"PASS: {previous} -> {composite} ({delta:+.1f}) [{grade}]"
                )
        else:
            verdict["message"] = (
                f"PASS: {composite}/100 [{grade}] (no previous score)"
            )
    else:
        verdict["message"] = (
            f"PASS: {composite}/100 [{grade}] >= effective minimum {effective_min} "
            f"(min {min_score} x coverage {coverage:.0%})"
        )

    # Record to history
    append_history(skill_path, result, history_path)
    return verdict


def format_verdict(verdict: dict) -> str:
    """Format verdict for human-readable terminal output."""
    lines = [verdict["message"]]

    # Show dimension breakdown on failure or regression
    if verdict["exit_code"] != 0:
        dims = verdict.get("dimensions", {})
        weak = {k: v for k, v in dims.items() if isinstance(v, (int, float)) and 0 <= v < 70}
        if weak:
            lines.append("  Weak dimensions:")
            for dim, score in sorted(weak.items(), key=lambda x: x[1]):
                lines.append(f"    {dim}: {score:.0f}/100")

    return "\n".join(lines)
