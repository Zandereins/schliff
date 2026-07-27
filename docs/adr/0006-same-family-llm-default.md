# ADR-0006: Same-Family LLM Default; Cross-Family as Fallback

- **Status:** Accepted
- **Date:** 2026-04-27
- **Decision-Driver:** Franz Paul (benevolent dictator)
- **Sprint:** v8.0 14-day sprint (2026-04-28 to 2026-05-11)
- **Related:** [Spec](../specs/2026-04-27-v8-product-completion.md) §8, §12, ADR-0002, ADR-0005

## Context

The LLM-Judge needs a model choice. Three patterns were on the table: cross-family-everywhere (judge with GPT-5 + Claude + Gemini on every call, ensemble or disagreement-flag), same-family default with cross-family fallback, and local-only (Prometheus-2 / Qwen3 self-hosted).

Cost and latency drove a closer look. A 191-skill corpus × N=5 self-consistency × ~3 dimensions ≈ 2865 judge calls per calibration cycle, run multiple times across P3. Cross-family-everywhere triples that envelope to ~$500+ in API spend per cycle without a measurable reliability win on routine tasks. The Trust-or-Escalate paper (ICLR 2025) showed cascaded same-family judging with confidence routing achieves 88% cost reduction at statistical equivalence to cross-family ensembles for routine eval tasks. Self-preference bias (Panickssery et al., NeurIPS 2024) is real — same-family judges score same-family outputs slightly higher — but Schliff's outputs are SKILL.md files, not LLM-generated text, so the bias surface is small. Variance is the more dangerous failure mode: Rating Roulette (Haldar & Hockenmaier, EMNLP 2025, arXiv:2510.27106) qualitatively documents self-inconsistency on subjective dimensions (no specific percentage published in source) without N≥5 voting.

Local-only was rejected on capability: published Cohen's κ vs human for Prometheus-2 and Qwen3 sits at ~0.6–0.7, below the κ ≥ 0.7 target from ADR-0005's per-dim thresholds.

**Doctrine adaptation note:** Husain's "using the same model is usually fine because the judge is doing a different task" (FAQ Same Model section) addresses **production-judging** scenarios. Schliff applies the parallel argument to **calibration-against-human-ground-truth**, with explicit acknowledgment of self-preference bias (Panickssery 2024) mitigated via the cross-family fallback path on disagreement. This is an extension of, not a direct cite of, Husain's stated position.

## Decision

1. **Default judge: Claude Sonnet 4.5** (or Sonnet 4.7 if available at sprint start), pinned by exact `model+date` string in the methodology page.
2. **N=5 self-consistency** with temperature 0.3, plurality vote per dimension. Mitigates Rating Roulette variance.
3. **Dual-order evaluation** (swap candidate A/B order on pairwise calls) to mitigate position bias.
4. **Cross-family judge** (GPT-5 / Gemini 2.5 Pro) is invoked **only** when:
   - same-family disagreement on a holdout dimension exceeds threshold (target |Δ| > 0.15 between N=5 runs), **or**
   - the methodology bias-validation pass runs on a 50-item validation holdout (one-off per release).
5. **Cost envelope:** ~$50–150 total for v8.0 calibration (vs $500+ for cross-family-everywhere).

## Consequences

**Positive:**

- Cost stays inside the v8.0 budget; calibration cycles can be re-run cheaply when the corpus or rubric shifts.
- N=5 self-consistency directly addresses the documented variance failure mode.
- Cross-family fallback path exists and is invoked exactly where it adds signal (disagreement, validation pass) — not as a flat tax.

**Negative:**

- Self-preference bias remains a known limitation; methodology page must disclose it explicitly with the validation-pass result.
- Adding a new family (e.g., Gemini-3 when it ships) requires re-running the validation pass before publishing.

## Alternatives Considered

1. **Cross-family on every calibration call** *(rejected).* 3x cost, no measurable reliability win on routine tasks per Trust-or-Escalate (ICLR 2025); cascaded routing achieves statistical equivalence at 88% cost reduction.
2. **Single judge with no self-consistency** *(rejected).* Rating Roulette (Haldar & Hockenmaier, EMNLP 2025, arXiv:2510.27106) qualitatively documents self-inconsistency on subjective dimensions (no specific percentage published in source); falls below ADR-0005 κ targets immediately.
3. **Local-only model (Prometheus-2 / Qwen3)** *(rejected for v8.0).* κ vs human ~0.6–0.7, below the ≥0.7 target. Reserved for the cheap-tier of a v8.1 cascade where the local model handles obvious cases and Sonnet handles the long tail.

## References

- Husain & Shankar, "LLM Evals FAQ", "Same Model" section — https://hamel.dev/blog/posts/evals-faq/
- Trust-or-Escalate (ICLR 2025) — cascaded confidence routing, 88% cost reduction at statistical equivalence.
- Panickssery, Bowman, Feng, "LLM Evaluators Recognize and Favor Their Own Generations" (NeurIPS 2024, arXiv:2404.13076) — self-preference bias evidence.
- Haldar & Hockenmaier, "Rating Roulette" (EMNLP 2025, arXiv:2510.27106) — variance evidence motivating N=5.
- ADR-0002 — `docs/adr/0002-calibration-set-protocol.md`
- ADR-0005 — `docs/adr/0005-per-dimension-reliability-reporting.md`
- v8.0 Product Completion Spec — `docs/specs/2026-04-27-v8-product-completion.md` §8, §12
