"""Dimension guard — prevents score regression in individual dimensions."""
from __future__ import annotations

from evolve.content import GuardResult


def dimension_guard(old_scores: dict, new_scores: dict, threshold: float = 3.0) -> GuardResult:
    """Check that no dimension drops more than threshold points.

    Args:
        old_scores: Dict of dimension -> scorer result dict (with "score" key)
        new_scores: Dict of dimension -> scorer result dict (with "score" key)
        threshold: Maximum allowed drop per dimension

    Returns:
        GuardResult with passed=True if all dimensions within threshold.
    """
    violations = []
    for dim, old_result in old_scores.items():
        if not isinstance(old_result, dict):
            continue
        old_score = old_result.get("score", -1)
        if old_score < 0:
            continue  # not measured, skip
        new_result = new_scores.get(dim, {})
        if not isinstance(new_result, dict):
            violations.append(f"{dim}: {old_score:.1f} → missing/invalid")
            continue
        new_score = new_result.get("score", -1)
        if new_score < 0:
            violations.append(f"{dim}: {old_score:.1f} → unmeasured")
            continue
        drop = old_score - new_score
        if drop > threshold:
            violations.append(f"{dim}: {old_score:.1f} → {new_score:.1f} (dropped {drop:.1f})")
    return GuardResult(passed=len(violations) == 0, violations=violations)


def security_guard(old_scores: dict, new_scores: dict) -> GuardResult:
    """Stricter guard for security dimension: ANY drop > 0 = reject.

    From Security Review S4: "security dimension drop > 0 = REJECT"

    Only enforced when security dimension is present in old_scores
    (i.e., security scoring is included/enabled).
    """
    if "security" not in old_scores:
        return GuardResult(passed=True, violations=[])

    old_sec_result = old_scores["security"]
    if not isinstance(old_sec_result, dict):
        return GuardResult(passed=True, violations=[])

    old_sec = old_sec_result.get("score", -1)

    if old_sec < 0:
        return GuardResult(passed=True, violations=[])

    new_sec_result = new_scores.get("security", {})
    if not isinstance(new_sec_result, dict):
        return GuardResult(
            passed=False,
            violations=["security: was measured, now missing/invalid"],
        )

    new_sec = new_sec_result.get("score", -1)
    if new_sec < 0:
        return GuardResult(
            passed=False,
            violations=["security: was measured, now unmeasured"],
        )

    drop = old_sec - new_sec
    if drop > 0:
        return GuardResult(
            passed=False,
            violations=[
                f"security: {old_sec:.1f} → {new_sec:.1f} (any security drop is rejected)"
            ],
        )
    return GuardResult(passed=True, violations=[])
