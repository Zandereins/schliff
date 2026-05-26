# Audit Follow-ups — Design Spec

**Branch:** `schliff-v8/audit-followups` (off `feat/v8-product-completion-sprint` @ bc8269e)
**Date:** 2026-05-26
**Status:** Approved (design), pending implementation plan

## Goal

Resolve the *verified-real* findings from an external audit of schliff (run by a downstream
project, "Jarvis", that wants to inherit schliff's episodic-memory + autonomous-loop +
anti-gaming engines). The audit ran against an **installed 6.1.0**; the repo is at **7.2.0**.
Four read-only research passes separated real findings from stale ones. This spec fixes the
real ones and substantiates one unproven claim.

## Context — verified delta (7.2.0)

| Audit finding | Verdict in 7.2.0 | Evidence |
|---|---|---|
| Dual-scale composite bug (38 vs 44.9) | **STALE/FIXED** | Single normalized `compute_composite` (`scoring/composite.py:107-116`); old cap is dead code (`scoring/security.py:231`, never called) |
| Anti-gaming: gamed ≥ clean at composite | **REAL** | `composite.py:116` drops unmeasured dims + renormalizes; without eval suite quality(0.20)+edges(0.15)=35% discriminating weight vanishes. `benchmarks/anti-gaming/run.py` has no clean-control, only asserts per-dim `<80`, never composite separation |
| Version drift 6.1.0 vs 7.2.0 | **REAL** | `.claude-plugin/plugin.json:3` = `6.1.0`; no `__version__` single-source |
| "60-70% rule-based patches" | **UNSUBSTANTIATED** | 7 assertion sites, no measurement; gradient catalog ~56% high-confidence |
| Episodic memory test | **REAL gap** | `episodic_store.py` impl present (TF-IDF+cosine, flock, atomic rename); no pytest file, only `_run_self_test` CLI flag |
| 7-vs-8 dims / "4/8 measured" | **Mostly FIXED** | Registry single-source, security opt-in; residual: `total_count` cosmetic shows "7/8" |
| pytest not default runner | **Mostly FIXED** | testpaths+CI, 1131 tests green; residual: `make test` runs bash, no pre-commit |

## Requirements

### W1 — Anti-gaming composite integrity (TDD, core)

**Problem.** When no eval suite is present (the common case), the substance-bearing dims
`quality` (0.20) and `edges` (0.15) return `-1` and are dropped from the composite, which
renormalizes over the remaining gameable surface dims. A keyword-stuffed skill can therefore
match or beat a clean one at composite level. The anti-gaming benchmark does not guard against
this (no clean control, no composite-separation assertion).

**W1a — Guard (write first, expect red).**
- Add a genuine clean-reference skill to `benchmarks/anti-gaming/skills/`.
- Add a benchmark assertion: under the no-eval-suite condition (as `run.py` already scores),
  every gamed skill's composite MUST be `< clean_composite`. Make it a real gate (non-zero
  exit on failure) and wrap it in a pytest test so it runs in the suite.
- Construct a representative gamed/clean pair (the audit's exact 78/76.5 files are not
  available). **Honest constraint:** if 7.2.0 already separates the pair (better than 6.1.0),
  that is itself a finding — the guard still has value as a regression net, and W1b's formula
  change is reduced to the coverage-honesty lever only. Do NOT claim a reproduction not observed.

**W1b — Fix until green (two levers).**
- **(a) Coverage-confidence cap** in `composite.py`: when the discriminating dims
  (`quality`+`edges`) are unmeasured, the composite cannot exceed a coverage-derived ceiling.
  Addresses cross-artifact comparability (a 0.65-coverage 78 must not read as trustworthy as a
  full-coverage 78). Lowers gamed and clean equally — does NOT by itself reorder a same-coverage
  pair.
- **(b) Surface-dim penalty** sufficient to make `gamed_composite < clean_composite` at equal
  coverage. The exact lever (e.g., trigger keyword-density / vocabulary-diversity signal on the
  measured dims) is decided only after reproducing the inversion in W1a.

**Impact.** Lever (a) shifts no-eval-suite scores downward. Must: re-baseline golden-score
fixtures, update anti-gaming benchmark numbers in docs, and **document the score shift explicitly**
so the parallel failure-mode calibration session can absorb it. This is the one workstream that
touches `scoring/composite.py`; coordinate before merge.

### W2 — Substantiate the "60-70%" claim

- Add `scripts/measure_patch_ratio.py`: count gradients in `text_gradient.py` by `confidence`
  (deterministic/auto-appliable vs LLM), compute the real ratio. Canonical, re-runnable source.
- Correct all 7 assertion sites (README ×2, `SKILL.md`, `docs/ARCHITECTURE.md`, 2 specs,
  `auto-improve.py` docstring) to the **measured** figure with a footnote pointing to the script.

### W3 — Version single-source

- Add `__version__` to `skills/schliff/__init__.py` as the source of truth.
- Bump `.claude-plugin/plugin.json` `6.1.0` → `7.2.0`.
- Add a pytest test asserting version consistency across `pyproject.toml`, `plugin.json`,
  and `__version__` (prevents future drift).

### W4 — Episodic-memory unit test

- Add `skills/schliff/tests/unit/test_episodic_store.py`: store/recall, cross-process
  persistence, flock path, atomic rename, size-cap eviction, TF-IDF cosine ranking. Build on the
  behaviours the existing `_run_self_test` already exercises.

### W5 — pytest as default runner

- `make test` invokes pytest (alongside, not replacing, existing integration scripts).
- Optional minimal `.pre-commit-config.yaml` with a pytest hook. No restructuring of existing
  integration tests.

### W6 — Housekeeping (composite-coherent with W1)

- Remove dead `get_composite_cap()` (`scoring/security.py:231`) and its test reference.
- Fix cosmetic `total_count` so a default run reports "7/7" not "7/8" (exclude unmeasured opt-in
  dims from the denominator). Implement coherently with W1's coverage logic.

## Technical decisions

- **TDD for W1.** Guard (red) before fix (green). The guard is the success criterion.
- **No silent score changes.** Any composite shift is documented + golden scores re-baselined in
  the same commit, with a note for the calibration session.
- **Atomic commits per workstream.** Order: W1 → W6 → W2/W3/W4/W5 (latter four independent).
- **Stay clear of in-flight worktrees** (phase-1c/3b/3c own MCP scorer modules + badges). W1/W6
  touch `composite.py`/`security.py`, untouched by those branches but indirectly relevant to the
  calibration session — flag at merge.

## Open questions

1. **W1b reproduction:** Does 7.2.0 still exhibit gamed ≥ clean with a constructed pair? Resolved
   empirically in W1a before committing to lever (b).
2. **Coverage-cap shape:** Hard ceiling vs proportional discount when discriminating dims absent.
   Decided against the reproduced numbers so the cap is calibrated, not arbitrary.
3. **Golden-score blast radius:** How many fixtures/docs encode no-eval-suite composites that W1b(a)
   will move. Enumerated before the W1b commit.

## Success criteria

- `benchmarks/anti-gaming` gate: every gamed composite `<` clean composite; pytest-wrapped, green.
- `measure_patch_ratio.py` runs; all 7 sites cite the measured figure + methodology.
- Version consistency test green; `plugin.json` = 7.2.0.
- `test_episodic_store.py` green; covers persistence, locking, atomic write, ranking.
- `make test` runs pytest; full suite green (≥1131, plus new tests).
- Dead `get_composite_cap()` gone; default run reports "7/7".
