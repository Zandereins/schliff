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


def test_partial_coverage_warning_is_an_invitation():
    # First-run UX: an eval-suite-less skill must read as guidance, not punishment.
    measured = _scores(structure=95, efficiency=90, composability=88, clarity=100)
    result = compute_composite(measured)
    assert result["warnings"], "partial coverage must surface guidance"
    w = result["warnings"][0]
    # Actionable + names the path the renderer keys on for the info glyph.
    assert "/schliff:init" in w and "eval suite" in w.lower()
    # No punitive vocabulary that frames a missing eval suite as failure.
    for banned in ("uncredited", "ceiling", "Only ", "Unverified"):
        assert banned not in w, f"punitive wording leaked back in: {banned!r}"
    # Still honest about the cap (the number, once).
    assert f"{result['weight_coverage']:.0%}" in w


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
    bench_skills = Path(__file__).resolve().parents[4] / "benchmarks" / "anti-gaming" / "skills"

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


def test_system_prompt_keeps_security_in_headline():
    """For system_prompt, security is a CORE dim (weight 0.15) and must stay in the headline;
    coverage must reflect it (not falsely report 1.0 when security is unmeasured)."""
    # All system_prompt dims measured EXCEPT security -> coverage < 1.0 (security weight not credited)
    sp = {d: {"score": 100} for d in
          ["structure_prompt", "output_contract", "efficiency", "clarity", "composability", "completeness"]}
    r = compute_composite(sp, fmt="system_prompt")
    assert r["weight_coverage"] < 1.0, "system_prompt security weight wrongly excluded from basis"
    # And when security IS measured, it participates in the headline: security=0 must score
    # strictly below security=100 (it's in the basis, not a side signal). Both reach full
    # coverage, so the headline delta is the proof that security is folded into the number.
    r_sec0 = compute_composite({**sp, "security": {"score": 0}}, fmt="system_prompt")
    r_sec100 = compute_composite({**sp, "security": {"score": 100}}, fmt="system_prompt")
    assert r_sec0["score"] < r_sec100["score"], "security must move the system_prompt headline"
    assert r_sec100["weight_coverage"] == 1.0 and r_sec0["weight_coverage"] == 1.0


def test_spread_keyword_stuffing_penalized(tmp_path):
    """Spread keyword stuffing (one term repeated across many distinct lines) must be
    caught as low-information padding by the MEASURED efficiency dimension, so it
    lowers the composite. (Triggers is uncredited without an eval suite, so a penalty
    there cannot move the composite — it must land in a measured dim.)"""
    from scoring import score_efficiency
    stuffed = tmp_path / "stuffed.md"
    body = "\n".join(f"Deployment step {i}: run the deployment." for i in range(40))
    stuffed.write_text(
        f"---\nname: x\ndescription: deployment tool.\n---\n# X\n## Steps\n{body}\n",
        encoding="utf-8")
    result = score_efficiency(str(stuffed))
    assert result["score"] < 80, f"keyword stuffing not penalized: {result['score']}"
    assert any("keyword_stuffing" in str(i) for i in result["issues"])


def test_clean_body_not_stuffing_penalized(tmp_path):
    """Negative control: a domain-focused skill that legitimately repeats its subject
    term ~9 times across 60+ varied prose tokens must NOT be flagged as stuffed,
    so the penalty does not regress real-world skills.

    This fixture deliberately exceeds _STUFF_MIN_PROSE_TOKENS (40) so the threshold
    logic actually runs — the original fixture (~36 meaningful tokens) short-circuited
    before reaching the dominance check, making the test vacuous.
    """
    from scoring import score_efficiency
    clean = tmp_path / "clean.md"
    # Body has ~86 meaningful tokens; "deployment" appears 9 times (10.5% dominance),
    # which is below the 12% _STUFF_DOMINANCE threshold — must NOT trigger stuffing.
    body = (
        "A deployment skill that guides teams through safe rollout practices. "
        "Before starting a deployment, verify the target environment is healthy "
        "and all tests have passed. Each deployment should begin with smoke checks "
        "against a staging replica. If the deployment fails its smoke checks, roll "
        "back automatically and record the cause in the incident log. Stagger rollout "
        "across availability zones so that a single bad deployment cannot bring down "
        "the entire fleet. Document the deployment window in your team calendar, notify "
        "the on-call engineer before you begin, and keep the deployment log for "
        "compliance audit. A canary deployment reduces blast radius by routing a "
        "fraction of traffic first, then widens once metrics look stable. Monitor "
        "error rates closely after each deployment and compare them with the baseline "
        "from last week before declaring success."
    )
    clean.write_text(
        f"---\nname: deploy\ndescription: Use when rolling out a new version safely.\n---\n"
        f"# Deploy\n## When to use\nUse before releasing to production.\n"
        f"## Steps\n{body}\n",
        encoding="utf-8")
    result = score_efficiency(str(clean))
    assert not any("keyword_stuffing" in str(i) for i in result["issues"]), \
        f"clean body wrongly flagged: {result['issues']}"
    assert result["score"] >= 70, \
        f"legitimate domain skill scored too low: {result['score']}"


def test_anti_gaming_benchmark_gate():
    import subprocess
    repo = Path(__file__).resolve().parents[4]  # unit→tests→schliff→skills→repo root
    proc = subprocess.run(["/usr/bin/python3", "benchmarks/anti-gaming/run.py"],
                          cwd=str(repo), capture_output=True, text=True)
    assert proc.returncode == 0, f"anti-gaming separation failed:\n{proc.stdout}"


def test_the_anti_gaming_gate_fails_on_an_incomplete_corpus(monkeypatch, capsys):
    """"No vector gamed" and "no vector measured" must not both be exit 0.

    The gate above asserts only ``returncode == 0``. Measured on f202bc1, before
    this: renaming ONE skill file left the run at exit 0 while the headline
    quietly dropped from 7/7 to 6/7 — the strongest vector stopped being tested
    and CI stayed green. A rename is the most ordinary edit there is, and a gate
    that can silently stop measuring makes every earlier green unprovable.

    This is the unit half; the subprocess test above covers the real corpus.
    """
    import pytest

    repo = Path(__file__).resolve().parents[4]
    bench_dir = str(repo / "benchmarks" / "anti-gaming")
    if bench_dir not in sys.path:
        sys.path.insert(0, bench_dir)
    import run as bench

    monkeypatch.setattr(sys, "argv", ["run.py"])
    monkeypatch.setattr(
        bench, "run_benchmarks",
        lambda: [{"file": "renamed-away.md", "error": "File not found: renamed-away.md"}])

    with pytest.raises(SystemExit) as exc:
        bench.main()

    assert exc.value.code == 1, "an unmeasured vector must not pass as a clean run"
    out = capsys.readouterr().out
    assert "CORPUS INCOMPLETE" in out, out[-400:]
    assert "renamed-away.md" in out, "the report must name what it did not measure"


def test_evolve_score_file_matches_cli(tmp_path):
    """evolve._score_file must return the same headline composite as the CLI path."""
    import importlib
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\nname: demo\ndescription: Use when demoing the evolve scoring path for parity tests.\n---\n"
        "# Demo\n## When to use\nUse for parity testing.\n## Steps\n1. Do the thing.\n",
        encoding="utf-8",
    )
    engine = importlib.import_module("evolve.engine")
    from shared import build_scores
    _, evolve_composite = engine._score_file(str(skill))
    cli_composite = compute_composite(build_scores(str(skill)))["score"]  # CLI: no security
    assert evolve_composite == cli_composite


def test_default_run_reports_seven_of_seven():
    full = {d: {"score": 90} for d in
            ["structure", "triggers", "quality", "edges", "efficiency", "composability", "clarity"]}
    r = compute_composite(full)
    assert r["measured_dimensions"] == 7 and r["total_dimensions"] == 7
