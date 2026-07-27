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
| Dual-scale composite (magnitude 38 vs 44.9) | **STALE** (the 6.1.0 cap artifact is gone) | Old cap is dead code (`scoring/security.py:231`, never called) |
| Dual-scale composite (**conceptual**) | **REAL** | Same file → two numbers: CLI/doctor/bench use 7 dims (`cli.py:114`), evolve uses 8 dims with security (`evolve/engine.py:50`). `composite.py:116` renormalizes over *measured* weight, so the denominator differs by dim-set. A measurement instrument must give one reading per input. |
| Anti-gaming: gamed ≥ clean at composite | **REAL — same root cause as conceptual dual-scale** | `composite.py:116` renormalize-over-measured drops `quality`(0.20)+`edges`(0.15)=35% discriminating weight when no eval suite → composite from gameable surface dims only. `benchmarks/anti-gaming/run.py` has no clean-control, only asserts per-dim `<80`, never composite separation |
| Version drift 6.1.0 vs 7.2.0 | **REAL** | `.claude-plugin/plugin.json:3` = `6.1.0`; no `__version__` single-source |
| "60-70% rule-based patches" | **UNSUBSTANTIATED** | 7 assertion sites, no measurement; gradient catalog ~56% high-confidence |
| Episodic memory test | **REAL gap** | `episodic_store.py` impl present (TF-IDF+cosine, flock, atomic rename); no pytest file, only `_run_self_test` CLI flag |
| 7-vs-8 dims / "4/8 measured" | **Mostly FIXED** | Registry single-source, security opt-in; residual: `total_count` cosmetic shows "7/8" |
| pytest not default runner | **Mostly FIXED** | testpaths+CI, 1131 tests green; residual: `make test` runs bash, no pre-commit |

## Requirements

### W1 — Unified composite + anti-gaming separation (TDD, core)

**Root cause (one line, two symptoms).** `composite.py:116` computes `total / weight_sum`,
renormalizing over the *measured* weight. This single choice produces BOTH: (1) conceptual
dual-scale — different measured dim-sets → different denominators → different numbers for the
same file; (2) the anti-gaming hole — unmeasured discriminating dims (`quality`+`edges`) are
silently dropped, so without an eval suite the composite is computed from gameable surface dims
only. One correct aggregation definition fixes both.

**Unified composite definition (decided — AI-evals best practice, Husain/Shankar):**

1. **Canonical composite = the 7 default dims** (security/runtime excluded), weights renormalized
   to sum 1.0. Every entrypoint (CLI, evolve, doctor, bench) computes this identically.
2. **Full-denominator aggregation (Path B): unmeasured = uncredited, not failed.**
   `composite = Σ(s·w for measured) / Σ(w for ALL canonical dims)`. No renormalization-credit for
   dims that were never evaluated. A structurally-perfect skill with no eval suite reads ~65 = "your
   ceiling is your coverage until you verify the rest." Rationale: (a) you don't get credit for what
   you didn't measure (core doctrine); (b) the number means one thing at any coverage (comparable);
   (c) right incentive — to score high you must write an eval suite (serves the v8 eval-adapter goal);
   (d) structurally caps the gamed-no-eval-suite illusion; (e) one formula, no arbitrary ceiling knob.
3. **Coverage is a first-class, inseparable qualifier**, not buried metadata. Headline reads e.g.
   `verified 65/100 (coverage 65% — 35% unverified; add an eval suite to lift the ceiling)`. This is
   the framing that makes "uncredited ≠ failed" true to the user.
4. **Security/runtime = separate signal + gate**, never folded into the headline composite. Removes
   the security-on/off divergence at the source and treats safety as first-class (v8 safety pillar).
5. **Per-dimension scores stay visible** — the real decision/error-analysis surface (doctrine: don't
   optimize a single aggregate; read the failure-mode vector).

**W1a — Guards (write first, expect red).**

- Add a genuine clean-reference skill to `benchmarks/anti-gaming/skills/`.
- **Guard 1 (separation):** every gamed skill's composite MUST be `< clean_composite` under the
  no-eval-suite condition. Real gate (non-zero exit) + pytest wrapper.
- **Guard 2 (unification / no dual-scale):** for a fixture file, CLI-headline composite ==
  evolve-headline composite (now both 7-dim canonical). Pins the unification permanently.
- Construct a representative gamed/clean pair (the audit's exact 78/76.5 files are unavailable).
  **Honest constraint:** if a constructed pair does not reproduce gamed ≥ clean on 7.2.0, that is
  itself a finding — the guards still pin the invariants as regression nets. Do NOT claim a
  reproduction not observed.

**W1b — Fix until green (two orthogonal levers).**

- **Lever 1 — aggregation:** implement the unified full-denominator composite (def. 1-4 above).
  Fixes dual-scale entirely and removes the misleading-high-magnitude half of anti-gaming.
- **Lever 2 — surface-dim gaming penalty:** make `gamed_composite < clean_composite` at *equal*
  coverage (the denominator change alone does not reorder a same-coverage pair). Exact lever
  (e.g. trigger keyword-density / vocabulary-diversity signal on measured dims) decided only after
  reproducing the inversion in W1a.

**Impact / blast radius (the safety accounting).**

- Full-denominator rescales no-eval-suite composites downward (~×coverage). Affects: deterministic
  golden-score fixtures, doc example numbers, and **threshold semantics** (`fail if score<70` in the
  GitHub Action / pre-commit) — a documented scale change at the v8 major boundary; CHANGELOG must
  call it out as breaking.
- **NOT affected (verified):** the failure-mode calibration corpus (`LABELS.md`) labels *binary per
  failure-mode dimension*, it is not composite-scored — so the LLM-judge calibration is largely
  orthogonal to this rescale. Re-baselining now (corpus in Phase-1) is cheapest.
- Re-baseline all golden scores + regenerate anti-gaming/doc numbers in the same commit; document
  the shift for the parallel calibration session. This is the one workstream touching
  `scoring/composite.py` / `registry.py`; coordinate before merge.

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

- Remove dead `get_composite_cap()` (`scoring/security.py:231`) and its test reference. (If W1's
  security-as-gate work needs a cap, that is a *new* gate function, not this dead one.)
- `total_count`/coverage reporting falls out naturally once W1 makes the canonical headline set the
  7 dims (security separated): a default run reports "7/7". Verify no "7/8" residue remains.

## Technical decisions

- **Unified composite = full-denominator over 7 canonical dims, security/runtime separated**
  (Path B). Decided as the AI-evals best practice: no credit for unmeasured dims, one comparable
  number, coverage first-class, eval-suite-positive incentive. See W1.
- **TDD for W1.** Guards (red) before fix (green). The guards are the success criteria.
- **Scale change is a documented breaking change**, owned at the v8 major boundary; CHANGELOG entry
  + threshold-semantics note. Golden scores re-baselined in the same commit, with a note for the
  parallel calibration session. No silent score changes.
- **Atomic commits per workstream.** Order: W1 → W6 → W2/W3/W4/W5 (latter four independent).
- **Stay clear of in-flight worktrees** (phase-1c/3b/3c own MCP scorer modules + badges). W1/W6
  touch `composite.py`/`registry.py`/`security.py`, untouched by those branches but indirectly
  relevant to the calibration session — flag at merge.

## Open questions

1. **Lever-2 reproduction:** Does 7.2.0 still exhibit gamed ≥ clean at equal coverage with a
   constructed pair? Resolved empirically in W1a before committing to the surface-penalty lever.
2. **Surface-penalty lever choice:** which measured-dim signal (trigger keyword-density,
   vocabulary diversity, cross-section repetition) reorders the pair. Decided against the
   reproduced numbers so it is calibrated, not arbitrary.
3. **Blast radius enumeration:** which fixtures/docs/threshold configs encode no-eval-suite
   composites that the full-denominator change moves. Enumerated before the W1b commit.
4. **Coverage in the headline string vs structured field only:** how loudly coverage travels with
   the number in each surface (CLI, doctor table, badge, action output). Settled per-surface in W1b.

## Success criteria

- **Anti-gaming gate:** every gamed composite `<` clean composite; pytest-wrapped, green.
- **Unification gate:** CLI-headline composite == evolve-headline composite for a fixture file
  (no dual-scale); pytest-wrapped, green.
- **Coverage honesty:** a no-eval-suite score reports its coverage inseparably; a perfect-structural
  no-eval-suite skill cannot read as a full-coverage high score.
- `measure_patch_ratio.py` runs; all 7 sites cite the measured figure + methodology.
- Version consistency test green; `plugin.json` = 7.2.0.
- `test_episodic_store.py` green; covers persistence, locking, atomic write, ranking.
- `make test` runs pytest; full suite green (≥1131, plus new tests), golden scores re-baselined.
- Dead `get_composite_cap()` gone; default run reports "7/7"; CHANGELOG documents the scale change.
