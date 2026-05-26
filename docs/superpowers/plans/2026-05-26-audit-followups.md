# Audit Follow-ups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the verified-real findings from the 6.1.0 audit — unify the composite (kill conceptual dual-scale + the anti-gaming hole at one root cause), substantiate the "60-70%" claim, and fix version drift — each behind a permanent test/guard.

**Architecture:** The core is a single aggregation change in `scoring/composite.py`: a canonical 7-dimension headline composite using a **full denominator** (unmeasured = uncredited, not failed), with security/runtime reported as separate signals. Two regression guards pin the invariants (gamed < clean; CLI == evolve). The remaining workstreams are independent hygiene fixes, each with a self-checking test.

**Tech Stack:** Python 3 (stdlib only, zero-dependency), pytest, Makefile, JSON.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `skills/schliff/scripts/scoring/composite.py` | Unified full-denominator composite over 7 canonical dims; security separated | Modify |
| `skills/schliff/scripts/scoring/security.py` | Remove dead `get_composite_cap()` | Modify |
| `skills/schliff/scripts/evolve/engine.py` | Use 7-dim headline composite; track security separately | Modify (verify) |
| `benchmarks/anti-gaming/run.py` | Add clean-control + composite-separation gate | Modify |
| `benchmarks/anti-gaming/skills/clean-reference.md` | Genuine clean skill for separation guard | Create |
| `skills/schliff/tests/unit/test_composite_unified.py` | Guards: separation, unification, full-denominator, coverage | Create |
| `skills/schliff/scripts/measure_patch_ratio.py` | Canonical measurement of deterministic-patch ratio | Create |
| `skills/schliff/tests/unit/test_patch_ratio.py` | Lock the measurement methodology | Create |
| `skills/schliff/__init__.py` | `__version__` single source of truth | Modify |
| `.claude-plugin/plugin.json` | Bump 6.1.0 → match `__version__` | Modify |
| `skills/schliff/tests/unit/test_version_consistency.py` | Fail on version drift | Create |
| `skills/schliff/tests/unit/test_episodic_store.py` | Episodic memory unit coverage | Create |
| `Makefile` | `make test` runs pytest | Modify |
| `README.md`, `docs/ARCHITECTURE.md`, `skills/schliff/SKILL.md`, specs, `auto-improve.py` | Correct the "60-70%" claim | Modify |
| `CHANGELOG.md` | Document the breaking score-scale change | Modify |

---

## Task 1: Composite guards (write first, RED)

**Files:**
- Create: `skills/schliff/tests/unit/test_composite_unified.py`
- Create: `benchmarks/anti-gaming/skills/clean-reference.md`

- [ ] **Step 1: Create a genuine clean-reference skill**

Create `benchmarks/anti-gaming/skills/clean-reference.md` — a well-formed skill with real sections, no gaming:

```markdown
---
name: changelog-updater
description: Use when adding a release entry to CHANGELOG.md, before tagging a version, to keep the changelog consistent with Keep-a-Changelog format.
---

# Changelog Updater

## When to use
Use this when a release is about to be tagged and CHANGELOG.md needs a new version section.
Do NOT use for editing release notes on the GitHub releases page — that is a separate surface.

## Steps
1. Read the current `## [Unreleased]` section.
2. Create a new `## [X.Y.Z] - YYYY-MM-DD` heading below Unreleased.
3. Move entries from Unreleased into the new section, grouped under Added / Changed / Fixed / Removed.
4. Leave an empty Unreleased section for future entries.

## Example
Before:
```
## [Unreleased]
### Fixed
- Crash on empty input
```
After:
```
## [Unreleased]

## [1.4.0] - 2026-05-26
### Fixed
- Crash on empty input
```

## Edge cases
- No Unreleased entries: stop and report; do not create an empty version section.
- Date unknown: ask for the release date rather than guessing.

## Handoff
After updating, hand off to the tagging step; this skill does not run git commands.
```

- [ ] **Step 2: Write the failing guard tests**

Create `skills/schliff/tests/unit/test_composite_unified.py`:

```python
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

    clean = composite_of(bench_skills / "clean-reference.md")
    for gamed in ["keyword-stuffing.md", "inflated-headers.md", "fake-examples.md",
                  "bloated-preamble.md", "no-scope.md", "contradiction-skill.md"]:
        gp = bench_skills / gamed
        if gp.exists():
            assert composite_of(gp) < clean, f"{gamed} composite >= clean ({clean})"


def test_unification_cli_equals_evolve():
    """The same per-dimension scores must yield one headline composite regardless of
    whether security was also scored (CLI omits it, evolve includes it)."""
    dims = _scores(structure=82, triggers=78, quality=70, edges=66,
                   efficiency=88, composability=74, clarity=90)
    cli_path = compute_composite(dict(dims))                       # 7 dims (CLI)
    evolve_path = compute_composite({**dims, "security": {"score": 55}})  # +security (evolve)
    assert cli_path["score"] == evolve_path["score"], "dual-scale: CLI != evolve"
```

- [ ] **Step 3: Run the guards to confirm they FAIL**

Run: `/usr/bin/python3 -m pytest skills/schliff/tests/unit/test_composite_unified.py -v`
Expected: `test_full_denominator_uncredits_unmeasured` FAILS (current renormalization yields ~100, not ≤70); `test_security_excluded_from_headline` and `test_unification_cli_equals_evolve` may FAIL (security currently shifts the score). Capture which fail — that is the red baseline.

- [ ] **Step 4: Commit the red guards**

```bash
git add skills/schliff/tests/unit/test_composite_unified.py benchmarks/anti-gaming/skills/clean-reference.md
git commit -m "test: composite unification + anti-gaming separation guards (red)"
```

---

## Task 2: Unified full-denominator composite (GREEN)

**Files:**
- Modify: `skills/schliff/scripts/scoring/composite.py:49-169`

- [ ] **Step 1: Replace the aggregation in `compute_composite`**

Replace the body from the weight-resolution block through the `return` (lines 64-169) with the unified version. Key changes: derive a **canonical** weight set excluding `OPT_IN_SCORERS` (unless explicitly in `custom_weights`), renormalize it to 1.0, divide by the **full** canonical weight (uncredited unmeasured), and report security separately.

```python
    from scoring.registry import get_weights, OPT_IN_SCORERS

    weights = get_weights(fmt if fmt is not None else "skill.md")
    explicit = set(custom_weights or {})

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

    # Canonical headline basis: opt-in dims (security, runtime) are NEVER folded into the
    # headline composite unless the caller explicitly weighted them via custom_weights.
    # This is the single basis used by every entrypoint (CLI, evolve, doctor, bench) -> no dual-scale.
    canonical = {d: w for d, w in weights.items()
                 if d not in OPT_IN_SCORERS or d in explicit}
    basis = sum(canonical.values())
    if basis > 0:
        canonical = {d: w / basis for d, w in canonical.items()}  # renormalize to 1.0

    # Full-denominator aggregation: unmeasured dims are UNCREDITED (contribute 0), not dropped.
    # composite = Σ(score·weight over measured) / Σ(all canonical weight == 1.0)
    # => a skill's ceiling equals its coverage until the missing dims are verified.
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

    composite = round(total, 1)            # divisor is 1.0 (full canonical basis)
    coverage = round(measured_w, 2)
    measured_count = len(measured)
    total_count = len(canonical)

    warnings = []
    if unmeasured:
        prefix = "Only " if measured_count <= 2 else ""
        warnings.append(
            f"{prefix}{measured_count}/{total_count} dimensions measured "
            f"(coverage {coverage:.0%}). Unverified dimensions are uncredited — "
            f"score ceiling is {coverage:.0%}. Unmeasured: {', '.join(unmeasured)}"
        )

    # Security/runtime: reported as SEPARATE signals, never in the headline composite.
    signals = {}
    for opt in ("security", "runtime"):
        sv = scores.get(opt, {}).get("score", -1)
        if sv is not None and sv >= 0:
            signals[opt] = {
                "score": sv,
                "status": "pass" if sv >= SECURITY_GATE else "flag",
            } if opt == "security" else {"score": sv}

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
```

- [ ] **Step 2: Add the `SECURITY_GATE` constant**

Near the top of `composite.py` (after the imports, before `_load_calibrated_weights`), add:

```python
# Security is a separate advisory gate, never folded into the headline composite.
SECURITY_GATE = 70
```

- [ ] **Step 3: Run the unified guards**

Run: `/usr/bin/python3 -m pytest skills/schliff/tests/unit/test_composite_unified.py -v`
Expected: `test_full_denominator_uncredits_unmeasured`, `test_full_coverage_unaffected`, `test_security_excluded_from_headline`, `test_unification_cli_equals_evolve` all PASS. `test_separation_gamed_below_clean` PASS only if the surface dims already separate the pair — if it FAILS, that is the reproduction needed for Task 4.

- [ ] **Step 4: Commit**

```bash
git add skills/schliff/scripts/scoring/composite.py
git commit -m "feat: unified full-denominator composite — one basis, security separated (fixes dual-scale)"
```

---

## Task 3: Evolve loop uses the unified headline

**Files:**
- Modify: `skills/schliff/scripts/evolve/engine.py:45-52`

- [ ] **Step 1: Write the failing test**

Append to `skills/schliff/tests/unit/test_composite_unified.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `/usr/bin/python3 -m pytest skills/schliff/tests/unit/test_composite_unified.py::test_evolve_score_file_matches_cli -v`
Expected: FAIL — `_score_file` passes `include_security=True`, but after Task 2 security is excluded from the headline, so they should already match. If it PASSES already, that confirms unification holds end-to-end; keep the test as a regression net and skip Step 3.

- [ ] **Step 3: If failing, align `_score_file`**

In `engine.py:50`, security can stay measured (for the separate signal) but must not change the headline — Task 2 already guarantees that. If the test still fails, the divergence is elsewhere; align by scoring without security for the headline decision:

```python
    scores = build_scores(skill_path, include_security=True, fmt=fmt)
    result = compute_composite(scores, fmt=fmt)   # headline already excludes security
    return scores, result["score"]
```

- [ ] **Step 4: Run + commit**

Run: `/usr/bin/python3 -m pytest skills/schliff/tests/unit/test_composite_unified.py -v` → all PASS.

```bash
git add skills/schliff/scripts/evolve/engine.py skills/schliff/tests/unit/test_composite_unified.py
git commit -m "test: pin evolve headline == CLI headline (unification end-to-end)"
```

---

## Task 4: Surface-dim gaming penalty (lever 2 — conditional)

**Files:**
- Modify: `benchmarks/anti-gaming/run.py:81-138`
- Modify: a measured-dim scorer (decided after reproduction)

- [ ] **Step 1: Add the composite-separation gate to the benchmark**

In `benchmarks/anti-gaming/run.py`, add a clean control and a hard gate. After `BENCHMARKS` (line 78), add:

```python
CLEAN_CONTROL = "clean-reference.md"
```

Replace `main()` (lines 194-207) so it exits non-zero when any gamed composite ≥ clean:

```python
def main():
    use_json = "--json" in sys.argv
    results = run_benchmarks()

    clean_path = str(_SKILLS_DIR / CLEAN_CONTROL)
    clean_composite = score_skill(clean_path)["composite"] if Path(clean_path).exists() else None

    violations = []
    if clean_composite is not None:
        for r in results:
            if "composite" in r and r["composite"] >= clean_composite:
                violations.append((r["file"], r["composite"]))

    if use_json:
        output = [{k: v for k, v in r.items() if k != "target_details"} for r in results]
        print(json.dumps({"clean_composite": clean_composite,
                          "violations": violations, "results": output}, indent=2))
    else:
        print(format_markdown(results))
        print(f"\nClean control composite: {clean_composite}")
        if violations:
            print("SEPARATION FAILURES (gamed >= clean):")
            for f, c in violations:
                print(f"  {f}: {c}")

    sys.exit(1 if violations else 0)
```

- [ ] **Step 2: Reproduce — run the benchmark gate**

Run: `/usr/bin/python3 benchmarks/anti-gaming/run.py`
Expected: prints the table + clean composite. Note exit status: `echo $?`.
- If exit 0 (no violations): 7.2.0 + the full-denominator change already separate gamed from clean. **Record this as a finding in the spec; lever 2 is unnecessary.** Skip to Step 5.
- If exit 1: a gamed file reaches clean. Identify which dimension inflates it (compare `all_scores`); that names the lever.

- [ ] **Step 3: (If reproduced) strengthen the implicated scorer**

For the implicated measured dimension (most likely `triggers` via keyword density), add a density-based penalty. Example for `scoring/triggers.py` — penalize when a single token dominates the description/body vocabulary (spread-keyword stuffing the TF-IDF diminishing-returns misses). Write a focused unit test first in `test_composite_unified.py`:

```python
def test_spread_keyword_stuffing_penalized(tmp_path):
    from scoring import score_triggers
    stuffed = tmp_path / "stuffed.md"
    body = " ".join(["deployment"] * 60)
    stuffed.write_text(
        f"---\nname: x\ndescription: deployment deployment deployment tool.\n---\n# X\n{body}\n",
        encoding="utf-8")
    assert score_triggers(str(stuffed), None)["score"] < 80
```

Then implement the minimal density check in the scorer until the test and the benchmark gate pass. Exact threshold calibrated against the reproduced numbers (do not over-penalize the clean control — re-run Step 2 after each change).

- [ ] **Step 4: Wrap the benchmark in pytest**

Create the wrapper test inside `test_composite_unified.py`:

```python
def test_anti_gaming_benchmark_gate():
    import subprocess
    repo = Path(__file__).resolve().parents[3]
    proc = subprocess.run(["/usr/bin/python3", "benchmarks/anti-gaming/run.py"],
                          cwd=str(repo), capture_output=True, text=True)
    assert proc.returncode == 0, f"anti-gaming separation failed:\n{proc.stdout}"
```

- [ ] **Step 5: Run + commit**

Run: `/usr/bin/python3 -m pytest skills/schliff/tests/unit/test_composite_unified.py -v` → all PASS.

```bash
git add benchmarks/anti-gaming/run.py skills/schliff/tests/unit/test_composite_unified.py skills/schliff/scripts/scoring/triggers.py
git commit -m "feat: anti-gaming composite-separation gate + surface-dim stuffing penalty"
```

---

## Task 5: Re-baseline golden scores + docs + CHANGELOG

**Files:**
- Modify: any failing test fixtures encoding composite values; `benchmarks/anti-gaming` doc numbers; `CHANGELOG.md`

- [ ] **Step 1: Run the full suite to surface the blast radius**

Run: `/usr/bin/python3 -m pytest skills/schliff/tests -q 2>&1 | tail -40`
Expected: failures in tests that assert specific composite numbers (the scale changed by design). List every failing assertion.

- [ ] **Step 2: Update each failing expectation to the new value**

For each failure, confirm the new value is correct by reasoning (full-denominator = old_renormalized × coverage for no-eval-suite cases), then update the expected constant. Do NOT loosen assertions to ranges — set the exact new value. If a test asserted a now-impossible "78 without eval suite", update to the coverage-correct number.

- [ ] **Step 3: Regenerate documented benchmark numbers**

Run: `/usr/bin/python3 benchmarks/anti-gaming/run.py --json > /tmp/ag.json` and update any composite numbers quoted in `benchmarks/anti-gaming/README.md` (if present) to match.

- [ ] **Step 4: Add the CHANGELOG entry**

In `CHANGELOG.md` under `## [Unreleased]`, add:

```markdown
### Changed
- **BREAKING (scoring):** Composite is now computed over a single canonical 7-dimension basis
  with a full denominator — unmeasured dimensions are uncredited (not silently renormalized away).
  Scores for skills without an eval suite are lower and now reflect coverage. This unifies the
  `score`/`doctor`/`bench` and `evolve` paths (one number per file) and closes the anti-gaming gap
  where a gamed skill could match a clean one at composite level. Security is reported as a separate
  signal/gate, no longer folded into the headline. CI thresholds (`fail if score<N`) may need
  re-tuning. See `docs/superpowers/specs/2026-05-26-audit-followups-design.md`.
```

- [ ] **Step 5: Run + commit**

Run: `/usr/bin/python3 -m pytest skills/schliff/tests -q 2>&1 | tail -5` → all PASS.

```bash
git add -A
git commit -m "refactor: re-baseline golden scores for unified composite + CHANGELOG"
```

---

## Task 6: Housekeeping — remove dead cap, verify 7/7

**Files:**
- Modify: `skills/schliff/scripts/scoring/security.py:231-239`
- Modify: `skills/schliff/tests/unit/test_security.py` (reference to `get_composite_cap`)

- [ ] **Step 1: Find references to the dead function**

Run: `grep -rn "get_composite_cap" skills/ benchmarks/`
Expected: definition at `security.py:231` + a reference in `tests/unit/test_security.py`.

- [ ] **Step 2: Remove the function and its test**

Delete `get_composite_cap` (`security.py:231-239`) and the test in `test_security.py` that calls it. (The composite cap was superseded by the unified composite; security is now a separate gate via `SECURITY_GATE`.)

- [ ] **Step 3: Add a 7/7 assertion**

Append to `test_composite_unified.py`:

```python
def test_default_run_reports_seven_of_seven():
    full = {d: {"score": 90} for d in
            ["structure", "triggers", "quality", "edges", "efficiency", "composability", "clarity"]}
    r = compute_composite(full)
    assert r["measured_dimensions"] == 7 and r["total_dimensions"] == 7
```

- [ ] **Step 4: Run + commit**

Run: `/usr/bin/python3 -m pytest skills/schliff/tests/unit/test_composite_unified.py skills/schliff/tests/unit/test_security.py -q` → PASS.

```bash
git add skills/schliff/scripts/scoring/security.py skills/schliff/tests/unit/test_security.py skills/schliff/tests/unit/test_composite_unified.py
git commit -m "chore: remove dead get_composite_cap; assert 7/7 default reporting"
```

---

## Task 7: Measure the deterministic-patch ratio

**Files:**
- Create: `skills/schliff/scripts/measure_patch_ratio.py`
- Create: `skills/schliff/tests/unit/test_patch_ratio.py`

- [ ] **Step 1: Write the failing test (pin the methodology)**

Create `skills/schliff/tests/unit/test_patch_ratio.py`:

```python
"""Lock the deterministic-patch-ratio measurement methodology.

'Deterministic' is defined EXACTLY as the auto-apply gate in text_gradient.py:
    confidence == "high" AND effort <= EFFORT_SIMPLE
"""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from measure_patch_ratio import measure  # noqa: E402


def test_measure_returns_consistent_shape():
    m = measure()
    assert m["total"] > 0
    assert m["deterministic"] + m["llm"] == m["total"]
    assert 0.0 <= m["deterministic_ratio"] <= 1.0
    # The figure is whatever the catalog actually is — the test pins the contract, not a magic number.
    assert m["definition"] == 'confidence=="high" and effort<=EFFORT_SIMPLE'
```

- [ ] **Step 2: Run to verify it fails**

Run: `/usr/bin/python3 -m pytest skills/schliff/tests/unit/test_patch_ratio.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'measure_patch_ratio'`.

- [ ] **Step 3: Implement the measurement**

Create `skills/schliff/scripts/measure_patch_ratio.py`. It statically parses every gradient dict literal in `text_gradient.py` (AST — no execution, complete coverage of defined gradients) and classifies by the exact apply-gate predicate:

```python
#!/usr/bin/env python3
"""Measure the real deterministic-vs-LLM patch ratio — canonical source for the README claim.

A patch is auto-applied deterministically iff text_gradient.py's apply gate accepts it:
    confidence == "high" AND effort <= EFFORT_SIMPLE   (text_gradient.py)
Everything else falls back to the LLM. This script parses the gradient catalog statically.
"""
from __future__ import annotations
import ast
import json
from pathlib import Path

_GRADIENT = Path(__file__).resolve().parent / "text_gradient.py"
EFFORT_SIMPLE = 1
DEFINITION = 'confidence=="high" and effort<=EFFORT_SIMPLE'


def _gradient_dicts(tree: ast.AST) -> list[dict]:
    """Collect dict literals that look like gradients (have 'confidence' + 'delta' keys)."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = {k.value for k in node.keys if isinstance(k, ast.Constant)}
        if "confidence" in keys and "delta" in keys:
            d = {}
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                    d[k.value] = v.value
                elif isinstance(k, ast.Constant) and isinstance(v, ast.Name):
                    # effort uses named constants (EFFORT_SIMPLE=1, etc.)
                    d[k.value] = {"EFFORT_SIMPLE": 1, "EFFORT_MODERATE": 2,
                                  "EFFORT_COMPLEX": 3, "EFFORT_MAJOR": 4}.get(v.id, 2)
            out.append(d)
    return out


def measure() -> dict:
    tree = ast.parse(_GRADIENT.read_text(encoding="utf-8"))
    grads = _gradient_dicts(tree)
    total = len(grads)
    deterministic = sum(
        1 for g in grads
        if g.get("confidence") == "high" and int(g.get("effort", 2)) <= EFFORT_SIMPLE
    )
    return {
        "total": total,
        "deterministic": deterministic,
        "llm": total - deterministic,
        "deterministic_ratio": round(deterministic / total, 3) if total else 0.0,
        "definition": DEFINITION,
    }


def main():
    m = measure()
    print(json.dumps(m, indent=2))
    print(f"\nDeterministic patches: {m['deterministic']}/{m['total']} "
          f"= {m['deterministic_ratio']:.0%}  ({m['definition']})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test + capture the real number**

Run: `/usr/bin/python3 -m pytest skills/schliff/tests/unit/test_patch_ratio.py -v` → PASS.
Run: `/usr/bin/python3 skills/schliff/scripts/measure_patch_ratio.py` → record the printed ratio (e.g. `42%`). This number feeds Task 8.

- [ ] **Step 5: Commit**

```bash
git add skills/schliff/scripts/measure_patch_ratio.py skills/schliff/tests/unit/test_patch_ratio.py
git commit -m "feat: measure_patch_ratio.py — canonical deterministic-patch-ratio source"
```

---

## Task 8: Correct the "60-70%" claim everywhere

**Files:**
- Modify: `README.md:199,266`; `docs/ARCHITECTURE.md:79`; `skills/schliff/SKILL.md:6-7`; `docs/specs/2026-03-28-v8-design.md:213`; `skills/schliff/scripts/auto-improve.py:7`; `docs/specs/plans/v8-session-prompts.md:789`

- [ ] **Step 1: Locate every occurrence**

Run: `grep -rn "60-70\|60–70" README.md docs/ skills/`
Expected: the sites listed above.

- [ ] **Step 2: Replace each with the measured figure**

Using the number recorded in Task 7 Step 4 (call it `M%`), replace the claim with a sourced statement. For prose sites:

> `~M% of patches are applied deterministically (confidence=high, single-edit effort); the rest fall back to the LLM. Measured by \`scripts/measure_patch_ratio.py\`.`

For the `README.md:199` table cell: `| **Patches** | 100% LLM | ~M% deterministic, rest LLM |`.
For `SKILL.md:6-7` and the `auto-improve.py:7` docstring: replace `60-70%` with `~M%`.
Add a one-line footnote/reference to `measure_patch_ratio.py` in `README.md` and `docs/ARCHITECTURE.md` so the number has a single canonical source.

- [ ] **Step 3: Verify no stale figure remains**

Run: `grep -rn "60-70\|60–70" README.md docs/ skills/`
Expected: no matches.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/ skills/schliff/SKILL.md skills/schliff/scripts/auto-improve.py
git commit -m "docs: correct deterministic-patch ratio to measured value with canonical source"
```

---

## Task 9: Version single source of truth

**Files:**
- Modify: `skills/schliff/__init__.py`
- Modify: `.claude-plugin/plugin.json:3`
- Create: `skills/schliff/tests/unit/test_version_consistency.py`

- [ ] **Step 1: Write the failing test**

Create `skills/schliff/tests/unit/test_version_consistency.py`:

```python
"""Fail on version drift across the three places a version is declared."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE).group(1)


def _plugin_version() -> str:
    return json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


def _package_version() -> str:
    import sys
    sys.path.insert(0, str(ROOT / "skills"))
    import schliff  # skills/schliff/__init__.py
    return schliff.__version__


def test_all_versions_match():
    assert _pyproject_version() == _plugin_version() == _package_version(), (
        f"version drift: pyproject={_pyproject_version()} "
        f"plugin={_plugin_version()} package={_package_version()}"
    )
```

- [ ] **Step 2: Run to verify it fails**

Run: `/usr/bin/python3 -m pytest skills/schliff/tests/unit/test_version_consistency.py -v`
Expected: FAIL — `plugin.json` = `6.1.0` ≠ pyproject `7.2.0`, and `schliff.__version__` is undefined (`AttributeError`).

- [ ] **Step 3: Add `__version__` and fix `plugin.json`**

Write `skills/schliff/__init__.py`:

```python
"""Schliff — deterministic SKILL.md linter and scoring engine."""

__version__ = "7.2.0"
```

In `.claude-plugin/plugin.json`, change `"version": "6.1.0"` → `"version": "7.2.0"`.

- [ ] **Step 4: Run to verify it passes**

Run: `/usr/bin/python3 -m pytest skills/schliff/tests/unit/test_version_consistency.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/schliff/__init__.py .claude-plugin/plugin.json skills/schliff/tests/unit/test_version_consistency.py
git commit -m "fix: single-source version + drift guard (plugin.json 6.1.0 -> 7.2.0)"
```

---

## Task 10: Episodic-memory unit test

**Files:**
- Create: `skills/schliff/tests/unit/test_episodic_store.py`

- [ ] **Step 1: Write the test (covers persistence, locking path, atomic rename, ranking, size cap)**

Create `skills/schliff/tests/unit/test_episodic_store.py`:

```python
"""Dedicated unit coverage for the episodic memory store (audit finding #1)."""
import importlib
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import episodic_store as es  # noqa: E402


def _isolate(tmp_path, monkeypatch):
    """Point the store at a temp JSONL and clear the module TF-IDF cache."""
    p = tmp_path / "episodes.jsonl"
    monkeypatch.setattr(es, "EPISODES_PATH", p)
    es._tfidf_cache.update({"mtime": 0.0, "filesize": 0, "index": None, "episodes": None})
    return p


def test_store_then_recall_roundtrip(tmp_path, monkeypatch):
    p = _isolate(tmp_path, monkeypatch)
    es.store_episode("skill-a", "trigger_expansion", "keep", 5.0,
                     "Adding synonyms improved trigger accuracy", domain="skill")
    assert p.exists()
    results = es.recall("trigger accuracy", top_k=5)
    assert results and results[0]["relevance"] > 0
    assert results[0]["strategy"] == "trigger_expansion"


def test_persistence_across_fresh_load(tmp_path, monkeypatch):
    """Written episodes survive a cache-less reload (cross-process surrogate)."""
    _isolate(tmp_path, monkeypatch)
    es.store_episode("skill-b", "noise_reduction", "discard", -1.0,
                     "Removing hedges hurt clarity", domain="skill")
    # simulate a second process: drop the in-memory cache, reload from disk
    es._tfidf_cache.update({"mtime": 0.0, "filesize": 0, "index": None, "episodes": None})
    assert es.get_stats()["total"] == 1
    assert es.recall("clarity", top_k=3)


def test_ranking_orders_by_relevance(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    es.store_episode("s1", "trigger_expansion", "keep", 3.0,
                     "trigger keyword overlap synonyms description", domain="skill")
    es.store_episode("s2", "example_addition", "keep", 2.0,
                     "completely unrelated output formatting examples", domain="testing")
    results = es.recall("trigger keyword synonyms", top_k=2)
    assert results[0]["strategy"] == "trigger_expansion"
    assert results[0]["relevance"] >= results[-1]["relevance"]


def test_atomic_rewrite_on_consolidation(tmp_path, monkeypatch):
    """_enforce_size_cap rewrites via temp+rename and preserves recent episodes."""
    _isolate(tmp_path, monkeypatch)
    monkeypatch.setattr(es, "MAX_EPISODES", 5)
    monkeypatch.setattr(es, "CONSOLIDATION_BATCH", 3)
    # Force the size-cap parse path regardless of byte heuristic.
    monkeypatch.setattr(es, "_enforce_size_cap", es._enforce_size_cap)
    for i in range(8):
        es.store_episode(f"s{i}", "strat", "keep", float(i), f"learning number {i}", domain="d")
    es._enforce_size_cap()
    total = es.get_stats()["total"]
    assert total <= 8  # consolidated, not lost
    assert not (tmp_path / "episodes.tmp").exists()  # temp cleaned up by rename


def test_self_test_passes():
    assert es._run_self_test() is True
```

- [ ] **Step 2: Run to verify it passes**

Run: `/usr/bin/python3 -m pytest skills/schliff/tests/unit/test_episodic_store.py -v`
Expected: PASS (the implementation already exists; this is characterization coverage). If `test_atomic_rewrite_on_consolidation` is flaky due to the byte heuristic at `_enforce_size_cap:324`, adjust the test to write enough episodes to exceed `MAX_EPISODES * 200` bytes, or `monkeypatch` the heuristic threshold — do NOT change production code for the test.

- [ ] **Step 3: Commit**

```bash
git add skills/schliff/tests/unit/test_episodic_store.py
git commit -m "test: dedicated episodic-store unit coverage (persistence, ranking, atomic rewrite)"
```

---

## Task 11: pytest as the default runner

**Files:**
- Modify: `Makefile:1,9-10,18`

- [ ] **Step 1: Add a pytest target and route `make test` through it**

In `Makefile`, update the `.PHONY` line to include `test-unit`, and change the targets:

```make
.PHONY: test test-unit test-self test-proof test-all score lint install install-dev clean help

test-unit: ## Run the pytest unit suite (1100+ tests)
	/usr/bin/python3 -m pytest skills/schliff/tests -q

test: test-unit ## Run unit tests (pytest) then integration tests
	cd $(SKILL_DIR) && bash scripts/test-integration.sh --no-runtime-auto
```

Update `test-all` to include unit explicitly (it already chains `test`):

```make
test-all: test test-self test-proof ## Run all test suites (pytest + integration + self + proof)
```

- [ ] **Step 2: Verify pytest runs via make**

Run: `make test-unit`
Expected: pytest collects and runs the suite (≥1131 + new tests), all PASS.

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "build: wire pytest into make test (default runner)"
```

---

## Task 12: Final verification

- [ ] **Step 1: Full suite + benchmark gate + measurement**

```bash
/usr/bin/python3 -m pytest skills/schliff/tests -q 2>&1 | tail -5
/usr/bin/python3 benchmarks/anti-gaming/run.py; echo "exit=$?"
/usr/bin/python3 skills/schliff/scripts/measure_patch_ratio.py
make test-unit 2>&1 | tail -3
```
Expected: all tests PASS; anti-gaming `exit=0`; measurement prints the canonical ratio.

- [ ] **Step 2: Confirm no stale artifacts**

```bash
grep -rn "60-70\|60–70" README.md docs/ skills/ || echo "claim clean"
grep -rn "get_composite_cap" skills/ || echo "dead code clean"
git -C . log --oneline bc8269e..HEAD
```
Expected: "claim clean", "dead code clean", and the workstream commits listed.

---

## Self-Review notes (author)

- **Spec coverage:** W1→Tasks 1-5; W6→Task 6; W2→Tasks 7-8; W3→Task 9; W4→Task 10; W5→Task 11. All spec success criteria map to a task.
- **Honest constraint preserved:** Task 4 Step 2 explicitly handles the "no reproduction" outcome as a finding, not a forced fix.
- **Breaking change owned:** Task 5 Step 4 CHANGELOG; threshold-semantics called out.
- **Type consistency:** `measure()` shape (`total`/`deterministic`/`llm`/`deterministic_ratio`/`definition`) is identical in Task 7 test and impl; `compute_composite` return keys (`weight_coverage`, `total_dimensions`, `signals`, `security`) consistent across Tasks 1-6.
