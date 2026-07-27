# ADR-0002: Calibration-Set Protocol — Solo Iterative Labelling

- **Status:** Accepted
- **Date:** 2026-04-27
- **Decision-Driver:** Franz Paul (benevolent dictator)
- **Sprint:** v8.0 14-day sprint (2026-04-28 to 2026-05-11)
- **Related:** [Spec](../specs/2026-04-27-v8-product-completion.md) §4-P3, ADR-0001, ADR-0005

## Context

A calibration set (human-graded ground truth) is required to align the LLM-Judge layer. Three open questions: who labels, how big, what scale.

Two protocols were considered. The "build-then-label" plan called for 200 items labelled upfront with a pre-defined 1–5 Likert rubric across all dimensions, ideally with two annotators for inter-rater reliability. The alternative — adopted here — is "label-then-iterate": start small, grow the holdout as failure-mode coding (ADR-0001) reveals which dimensions actually need judging, and re-grade as criteria drift.

The practitioner-mainstream evidence converged decisively against the upfront plan. Hamel Husain's evals-faq is explicit on both axes: on annotators, the "Annotators" section endorses a single benevolent dictator for small-to-medium products and warns that multi-labeller setups produce "overhead without signal" at this scale; on scale, the "Binary vs Likert" section argues that 1–5 Likert evals dilute signal and that pass/fail with written critique is the practitioner default. Shankar et al. (EvalGen, UIST 2024) ran their entire user study at n=16 graded items per participant and qualitatively documented criteria drift (Shankar EvalGen §7.3.1, no specific percentage published in source) during grading — a "label 200 upfront" budget is wasted if a meaningful fraction of the criteria change after the first 30 items.

## Decision

1. **Labeller of record:** Franz, solo. Benevolent-dictator pattern; subagents may pre-stage but not grade.
2. **Phase 0 starter set:** **30 items** (per ADR-0001 update) co-labelled during failure-mode coding. No separate label pass.
3. **Iterative growth:** holdout grows iteratively to **100–150 items** during Judge-iteration (Phase P3), added in batches of ~20 as new failure modes are discovered or judge weak spots surface.
4. **Scale:** **binary pass/fail with mandatory written critique field**. No 1–5 Likert anywhere in v8.0.
5. **Re-grade pass:** after Judge v0 is wired, all prior grades are re-reviewed once to absorb criteria drift (per EvalGen §7.3.1, qualitatively documented; no specific percentage published in source). Drift > 20% on any dimension triggers a Judge v1 redesign before metrics ship.

## Consequences

**Positive:**

- Calibration cost stays inside one sprint; no labelling sweatshop phase.
- Binary scale forces taxonomy clarity (any "it depends" item exposes a missing failure mode rather than hiding inside a 3-of-5).
- Re-grade pass institutionalises drift handling instead of pretending drift does not happen.

**Negative:**

- Single labeller = single point of bias; mitigated only by ADR-0005's cross-family validation pass and public methodology disclosure.
- Holdout < 200 limits statistical power for thin-sliced sub-analyses; acceptable at v8.0 scope.

## Alternatives Considered

1. **200 items upfront, 1–5 Likert, two labellers** *(rejected).* Inverts Shankar's "label-then-build" workflow; Likert dilutes signal per Hamel; second labeller adds coordination cost without disagreement-resolution payoff at solo-maintainer scale.
2. **Multi-labeller with κ-tracking** *(rejected).* Husain/Shankar FAQ explicitly endorses benevolent dictator below ~5 maintainers; κ-tracking pays off only when domain experts disagree systematically, which is not the bottleneck here.
3. **Synthetic-only calibration via stronger LLM** *(rejected).* Skips the human-judgment anchor entirely; fails the "Datadog for AI software" credibility test.

## References

- Hamel Husain, "LLM Evals FAQ", "Annotators" + "Binary vs Likert" sections — https://hamel.dev/blog/posts/evals-faq/
- Shankar et al., "Who Validates the Validators?" UIST 2024 §5.2.1 (n=16) and §7.3.1 (criteria drift) — https://arxiv.org/abs/2404.12272
- ADR-0001 — `docs/adr/0001-failure-mode-first-scoping.md`
- v8.0 Product Completion Spec — `docs/specs/2026-04-27-v8-product-completion.md`

## Addendum (2026-04-28, Day 1) — Phase-0 starter set revised + tier-stratified reliability

The "Phase 0 starter set: 30 items (Anthropic 13 + Rezvani 17)" is superseded by the stratified familiar-core + representative-probe corpus (see ADR-0001 Day-1 addendum). Labelling protocol is otherwise unchanged: binary pass/fail + mandatory written critique, solo benevolent dictator, iterative growth to 100-150. **New:** the critique field tags each item by tier (`familiar` / `probe`) so Phase-P3 reliability reporting (ADR-0005) can stratify TPR/TNR/κ by tier — a pooled metric could hide a familiar-high / probe-low generalization gap (Hamel-lens finding: a judge calibrated only on the 99th-percentile familiar tail may pass its gate yet not generalize to the messy production distribution).
