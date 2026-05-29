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


# Security is a separate advisory gate, never folded into the headline composite.
SECURITY_GATE = 70


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

    Uses a full-denominator model: unmeasured dims are uncredited (contribute 0
    but stay in the basis), so a skill's score ceiling equals its coverage. The
    canonical headline basis is format-aware via get_headline_excluded — for the
    skill.md family security+runtime are excluded, for system_prompt only runtime
    is (security is a core 0.15 dim that stays in the headline). Security and
    runtime are also reported as separate signals in `signals`/`security`.

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
    from scoring.registry import get_weights, get_headline_excluded

    weights = get_weights(fmt if fmt is not None else "skill.md")
    explicit = set(custom_weights or {})

    # Stage 1: apply weight OVERRIDES (custom or auto-calibrated) RAW — do NOT renormalize
    # here. The canonical basis (Stage 2, below) is the single normalization point, applied
    # after dimension exclusion; renormalizing now would double-normalize and shift scores.
    if custom_weights:
        _SUPPLEMENTARY = {"clarity", "security"}
        for dim in list(weights):
            if dim in _SUPPLEMENTARY and dim not in custom_weights:
                del weights[dim]
        for k, v in custom_weights.items():
            if k in weights and isinstance(v, (int, float)) and math.isfinite(v) and v >= 0:
                weights[k] = v
    else:
        calibrated = _load_calibrated_weights()
        if calibrated:
            for k, v in calibrated.items():
                if k in weights:
                    weights[k] = v

    # Stage 2 — canonical headline basis (the single normalization point): format-aware. Dims
    # excluded per get_headline_excluded are NEVER
    # folded into the headline composite unless the caller explicitly weighted them via
    # custom_weights. For skill.md family, security+runtime are excluded (security is an opt-in
    # 0.05 side signal). For system_prompt, security is a CORE 0.15 dim and stays in the headline;
    # only runtime is excluded. This is the single basis used by every entrypoint -> no dual-scale.
    excluded = get_headline_excluded(fmt if fmt is not None else "skill.md")
    canonical = {d: w for d, w in weights.items()
                 if d not in excluded or d in explicit}
    basis = sum(canonical.values())
    if basis > 0:
        canonical = {d: w / basis for d, w in canonical.items()}  # renormalize to 1.0

    # Full-denominator aggregation. canonical weights already sum to 1.0 (Stage 2 renorm),
    # so the composite is simply Σ(score·weight) over MEASURED dims — there is no separate
    # division step. Unmeasured dims contribute 0 and are never added back, so a skill's
    # ceiling equals its coverage until the missing dims are verified.
    total = 0.0
    measured_w = 0.0
    measured = []
    unmeasured = []
    for dim, weight in canonical.items():
        s = scores.get(dim, {}).get("score", -1)
        if s >= 0:
            total += s * weight
            measured_w += weight
            measured.append(dim)
        else:
            unmeasured.append(dim)

    composite = round(total, 1)            # canonical weights sum to 1.0, so total IS the composite
    coverage = round(measured_w, 2)
    measured_count = len(measured)
    total_count = len(canonical)

    warnings = []
    if basis == 0:
        warnings.append("No weighted dimensions to score.")
    elif unmeasured:
        warnings.append(
            f"Scored {measured_count}/{total_count} dimensions — the score "
            f"can't exceed {coverage:.0%} until the rest are measured. "
            f"Run /schliff:init to add an eval suite and score: "
            f"{', '.join(unmeasured)}."
        )

    # Security/runtime: reported as SEPARATE signals, never in the headline composite.
    signals = {}
    for opt in ("security", "runtime"):
        sv = scores.get(opt, {}).get("score", -1)
        if sv is not None and sv >= 0:
            signals[opt] = ({
                "score": sv,
                "status": "pass" if sv >= SECURITY_GATE else "flag",
            } if opt == "security" else {"score": sv})

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
    }

    has_runtime = "runtime" in signals
    score_type = "structural+runtime" if has_runtime else "structural"

    return {
        "score": composite,
        "score_type": score_type,
        "measured_dimensions": measured_count,
        "total_dimensions": total_count,
        "weight_coverage": coverage,
        "unmeasured": unmeasured,
        "warnings": warnings,
        "signals": signals,
        "security": signals.get("security", {}),
        "confidence_notes": {k: v for k, v in confidence_notes.items() if k in measured},
    }
