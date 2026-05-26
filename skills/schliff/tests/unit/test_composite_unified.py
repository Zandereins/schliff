"""Guards for the unified composite (spec 2026-05-26-audit-followups §W1).

Pins three invariants permanently:
  1. Separation: a gamed skill must NOT reach/beat a clean skill at composite level.
  2. Unification: the same file scores identically via the CLI path and the evolve path
     (no conceptual dual-scale).
  3. Full-denominator: unmeasured dims are uncredited — a perfect-on-measured skill with
     missing discriminating dims cannot read as a full-coverage high score.
"""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from scoring.composite import compute_composite  # noqa: E402


def _scores(**dims):
    """Helper: build a per-dimension score dict; omit a dim to leave it unmeasured (-1)."""
    return {d: {"score": v} for d, v in dims.items()}


def test_full_denominator_uncredits_unmeasured():
    # All 7 canonical dims perfect EXCEPT quality+edges unmeasured (no eval suite).
    measured = _scores(structure=100, triggers=100, efficiency=100,
                        composability=100, clarity=100)  # quality, edges omitted
    result = compute_composite(measured)
    # quality(0.20)+edges(0.15)=0.35 of canonical weight is uncredited.
    # Perfect-on-measured therefore caps at ~65, NOT ~100.
    assert result["score"] <= 70, f"uncredited dims still credited: {result['score']}"
    # canonical coverage = 1.0 - quality(0.20) - edges(0.15) = 0.65 (<= 0.66 bound)
    assert result["weight_coverage"] <= 0.66
    assert result["total_dimensions"] == 7  # security excluded from headline


def test_full_coverage_unaffected():
    # All 7 dims measured and perfect -> 100 (full denominator == full coverage).
    full = _scores(structure=100, triggers=100, quality=100, edges=100,
                   efficiency=100, composability=100, clarity=100)
    result = compute_composite(full)
    assert result["score"] == 100.0
    assert result["weight_coverage"] == 1.0
    assert result["total_dimensions"] == 7


def test_security_excluded_from_headline():
    # Security present and terrible must NOT move the headline composite.
    base = _scores(structure=80, triggers=80, quality=80, edges=80,
                   efficiency=80, composability=80, clarity=80)
    without = compute_composite(dict(base))
    with_sec = compute_composite({**base, "security": {"score": 0}})
    assert without["score"] == with_sec["score"], "security leaked into headline"
    # but security is reported separately
    assert with_sec.get("security", {}).get("score") == 0


def test_separation_gamed_below_clean():
    """Real-file guard: a gamed skill must score strictly below the clean reference,
    under the no-eval-suite condition (the common case)."""
    from scoring import (score_structure, score_triggers, score_quality, score_edges,
                         score_efficiency, score_composability, score_clarity)
    bench_skills = Path(__file__).resolve().parents[3] / "benchmarks" / "anti-gaming" / "skills"

    def composite_of(path):
        s = {
            "structure": score_structure(str(path)),
            "triggers": score_triggers(str(path), None),
            "quality": score_quality(str(path), None),
            "edges": score_edges(str(path), None),
            "efficiency": score_efficiency(str(path)),
            "composability": score_composability(str(path)),
            "clarity": score_clarity(str(path)),
        }
        return compute_composite(s)["score"]

    import pytest
    existing = [g for g in ["keyword-stuffing.md", "inflated-headers.md", "fake-examples.md",
                            "bloated-preamble.md", "no-scope.md", "contradiction-skill.md"]
                if (bench_skills / g).exists()]
    if not existing:
        pytest.skip("no gamed fixtures present")

    clean = composite_of(bench_skills / "clean-reference.md")
    for gamed in existing:
        assert composite_of(bench_skills / gamed) < clean, f"{gamed} composite >= clean ({clean})"


def test_unification_cli_equals_evolve():
    """The same per-dimension scores must yield one headline composite regardless of
    whether security was also scored (CLI omits it, evolve includes it)."""
    dims = _scores(structure=82, triggers=78, quality=70, edges=66,
                   efficiency=88, composability=74, clarity=90)
    cli_path = compute_composite(dict(dims))                       # 7 dims (CLI)
    evolve_path = compute_composite({**dims, "security": {"score": 55}})  # +security (evolve)
    assert cli_path["score"] == evolve_path["score"], "dual-scale: CLI != evolve"
