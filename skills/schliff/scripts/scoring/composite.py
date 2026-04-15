"""Compute weighted composite score with confidence indicator.

Returns both the score and metadata about how many dimensions
were actually measured, so users know how trustworthy the number is.
"""
import json
import math
from typing import Optional
from pathlib import Path

_calibrated_weights_cache: Optional[dict] = None
_calibrated_weights_mtime: float = 0.0
_calibrated_weights_path: str = ""


def _load_calibrated_weights() -> Optional[dict]:
    """Load auto-calibrated weights from ~/.schliff/meta/calibrated-weights.json.

    Uses module-level cache with mtime invalidation to avoid repeated disk reads.
    """
    global _calibrated_weights_cache, _calibrated_weights_mtime, _calibrated_weights_path
    path = Path.home() / ".schliff" / "meta" / "calibrated-weights.json"
    path_str = str(path)

    if not path.exists():
        _calibrated_weights_cache = None
        return None

    current_mtime = path.stat().st_mtime

    if (_calibrated_weights_cache is not None
            and path_str == _calibrated_weights_path
            and current_mtime == _calibrated_weights_mtime):
        return _calibrated_weights_cache

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in data.values()):
            _calibrated_weights_cache = data
            _calibrated_weights_mtime = current_mtime
            _calibrated_weights_path = path_str
            return data
    except (json.JSONDecodeError, OSError):
        pass
    _calibrated_weights_cache = None
    return None


def compute_composite(scores: dict, custom_weights: Optional[dict] = None,
                      fmt: Optional[str] = None) -> dict:
    """Compute weighted composite score with confidence indicator.

    Returns both the score and metadata about how many dimensions
    were actually measured, so users know how trustworthy the number is.

    Args:
        scores: Per-dimension score dicts from the individual scorers.
        custom_weights: Optional dict of dimension_name -> float weight.
            Values are normalized to sum to 1.0. Example:
            {"structure": 0.3, "triggers": 0.4, "efficiency": 0.3}
        fmt: Optional format identifier. When provided, weights are loaded
            from the scorer registry. Defaults to "skill.md" weights.
    """
    from scoring.registry import get_weights

    weights = get_weights(fmt if fmt is not None else "skill.md")

    # Apply custom weights if provided (highest priority)
    # Custom weights OVERRIDE defaults for specified keys but keep unspecified dimensions.
    # When custom_weights are active, opt-in dimensions (security, clarity) are excluded
    # unless the user explicitly includes them in custom_weights.
    if custom_weights:
        # When custom weights are provided, only keep dimensions that the user
        # explicitly included. Dimensions not in custom_weights but present in
        # the registry defaults are kept (they form the baseline). However,
        # "supplementary" dimensions (clarity, security) that were traditionally
        # handled specially are excluded unless explicitly in custom_weights.
        _SUPPLEMENTARY = {"clarity", "security"}
        for dim in list(weights):
            if dim in _SUPPLEMENTARY and dim not in custom_weights:
                del weights[dim]
        # Reject negative weights
        for k, v in custom_weights.items():
            if k in weights and isinstance(v, (int, float)) and math.isfinite(v) and v >= 0:
                weights[k] = v
        # Normalize all weights to sum to 1.0
        total_w = sum(weights.values())
        if total_w > 0:
            weights = {k: v / total_w for k, v in weights.items()}
    else:
        # Try auto-calibrated weights (second priority)
        calibrated = _load_calibrated_weights()
        if calibrated:
            calibrated_filtered = {k: v for k, v in calibrated.items() if k in weights}
            if calibrated_filtered:
                for k, v in calibrated_filtered.items():
                    weights[k] = v
                total_w = sum(weights.values())
                if total_w > 0:
                    weights = {k: v / total_w for k, v in weights.items()}

    total = 0.0
    weight_sum = 0.0
    measured = []
    unmeasured = []

    for dim, weight in weights.items():
        s = scores.get(dim, {}).get("score", -1)
        if s >= 0:
            total += s * weight
            weight_sum += weight
            measured.append(dim)
        else:
            unmeasured.append(dim)

    composite = round(total / weight_sum, 1) if weight_sum > 0 else 0.0

    # Confidence: what fraction of total weight is actually measured
    confidence = round(weight_sum, 2)
    measured_count = len(measured)
    total_count = len(weights)

    warnings = []
    # Only warn about non-opt-in unmeasured dimensions (runtime, security are opt-in)
    from scoring.registry import OPT_IN_SCORERS
    warn_unmeasured = [d for d in unmeasured if d not in OPT_IN_SCORERS]
    if warn_unmeasured:
        prefix = "Only " if measured_count <= 2 else ""
        suffix = " Score is unreliable —" if measured_count <= 2 else ""
        warnings.append(
            f"{prefix}{measured_count}/{total_count} dimensions measured "
            f"(weight coverage: {confidence:.0%}).{suffix} "
            f"{'u' if measured_count <= 2 else 'U'}nmeasured: {', '.join(warn_unmeasured)}"
        )

    # Confidence notes: explain what each dimension can and cannot tell you
    confidence_notes = {
        "structure": "Measures file organization (frontmatter, headers, length, references). "
                     "Cannot assess whether instructions are correct or effective.",
        "triggers": "Measures keyword overlap between description and eval prompts using TF-IDF heuristic. "
                     "Cannot predict actual Claude triggering behavior — that requires runtime evaluation.",
        "quality": "Measures eval suite coverage (assertion types, feature breadth). "
                    "Cannot assess whether following the skill produces correct output.",
        "edges": "Measures edge case definitions in the eval suite. "
                  "Cannot verify the skill handles edge cases correctly at runtime.",
        "efficiency": "Measures information density (signal-to-noise ratio in text). "
                      "Cannot assess whether the content is actually useful to Claude.",
        "composability": "Measures scope boundaries and handoff declarations. "
                         "Cannot verify the skill works correctly alongside other skills.",
        "clarity": "Measures contradiction, vague reference, and ambiguity patterns. "
                   "Cannot assess whether instructions are clear to Claude in practice.",
        "security": "Measures security anti-patterns (hardcoded secrets, injection vectors, "
                     "unsafe operations). Cannot assess runtime security posture.",
    }

    # Determine score type based on what was measured
    has_runtime = "runtime" in measured
    score_type = "structural+runtime" if has_runtime else "structural"

    return {
        "score": composite,
        "score_type": score_type,
        "measured_dimensions": measured_count,
        "total_dimensions": total_count,
        "weight_coverage": confidence,
        "unmeasured": unmeasured,
        "warnings": warnings,
        "confidence_notes": {k: v for k, v in confidence_notes.items() if k in measured},
    }
