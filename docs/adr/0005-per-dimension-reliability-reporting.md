# ADR-0005: Per-Dimension Reliability Reporting (TPR/TNR + Cohen's κ)

- **Status:** Accepted
- **Date:** 2026-04-27
- **Decision-Driver:** Franz Paul (benevolent dictator)
- **Sprint:** v8.0 14-day sprint (2026-04-28 to 2026-05-11)
- **Related:** [Spec](../specs/2026-04-27-v8-product-completion.md) §11 + §8, ADR-0002, ADR-0006

## Context

The AI-Eval pillar needs to publish how well its LLM-Judge agrees with human ground truth. Three reporting shapes were considered: raw agreement %, per-dimension precision/recall + κ, and a single composite headline number.

Hamel Husain's "Creating an LLM-as-Judge" post is direct on the metric choice: raw agreement is "generally not recommended" because it conflates true positives and true negatives, hides class imbalance, and makes a 90%-pass-rate dimension look identical to a 50%-pass-rate dimension at the same agreement level. The recommendation is to **measure precision and recall separately** — equivalently TPR (true positive rate, sensitivity) and TNR (true negative rate, specificity) — and report Cohen's κ to chance-correct.

The reporting-shape question is separate. Going per-dimension-only optimises for academic rigour but produces a methodology page with no headline; HN-thread and PyPI-listing risk is high because reviewers scan for one number. Composite-only optimises for marketing legibility but is a Goodhart magnet and undermines the "Datadog for AI software" measurement-layer positioning, which depends on academic-grade transparency. Eugene Yan's eval-pattern writeups model the resolution: one composite headline that anchors first-glance, with a methodology drill-down one click away.

## Decision

1. **AI-Eval reports per-dimension TPR + TNR + Cohen's κ.** Raw agreement is **not** published.

**Attribution note on κ:** Cohen's κ is added beyond Hamel's TPR/TNR recommendation as a Schliff design choice for chance-correction. Hamel's [llm-judge post](https://hamel.dev/blog/posts/llm-judge/) advocates precision/recall (TPR/TNR equivalents) but does not specifically advocate κ; we add it for chance-corrected agreement reporting at the per-dim level, particularly relevant for low-base-rate failure modes.

2. **Public methodology page** at `docs/methodology/ai-eval-v8.0.md` shows the full per-dimension table including n-per-cell, holdout composition, and judge configuration (model+date pin, N self-consistency, temperature).
3. **README headline shows ONE composite reliability number** computed as a documented function of the per-dimension table — explicitly: macro-averaged TPR, macro-averaged TNR, mean κ, formatted as "Schliff AI-Eval: TPR X% / TNR Y% / κ Z" with a methodology link adjacent.
4. **Threshold targets** (per Spec §11): TPR ≥ 85%, TNR ≥ 85%, κ ≥ 0.7 on every dimension before AI-Eval headline ships; otherwise the headline is suppressed and the dimension is flagged "preview".

## Consequences

**Positive:**

- Per-dim drilldown earns measurement-layer credibility with eval-literate readers (the Hamel/Shreya/Eugene audience).
- Composite anchor satisfies first-glance scan on README and HN comment threads; removes the "what is this number" friction.
- Threshold suppression ("preview" flag) is a built-in honesty mechanism for dimensions still calibrating.

**Negative:**

- Two-layer reporting is more documentation surface to maintain (methodology page must stay in sync with the headline computation).
- Macro-averaging in the composite hides class imbalance across dimensions; mitigated only by the per-dim drilldown one click away.

## Alternatives Considered

1. **Per-dim only, no composite** *(rejected).* Marketing footgun. Customers and HN commenters want one number for first-glance; absence of a headline reads as evasion. The drilldown still exists either way.
2. **Composite only, no per-dim** *(rejected).* Loses academic-grade transparency required for the "Datadog for AI software" positioning. Composite-only is the EvalGen pattern Shankar critiques in §7.2.4.
3. **Raw agreement %** *(rejected).* Hamel's explicit "do not use" — conflates TPR and TNR, hides class imbalance, optically flattering on imbalanced holdouts.
4. **F1 instead of TPR/TNR** *(rejected).* F1 is one number per dim; TPR/TNR separately is two numbers but exposes the asymmetry between false-pass and false-fail costs, which matters for a measurement product.

## References

- Hamel Husain, "Creating an LLM-as-Judge" (precision/recall not raw agreement) — https://hamel.dev/blog/posts/llm-judge/
- Shankar et al., "Who Validates the Validators?" UIST 2024 §7.2.4 (per-criterion alignment in Report Card) — https://arxiv.org/abs/2404.12272
- Eugene Yan, "Patterns for Building LLM-Based Systems" (headline + drilldown pattern) — https://eugeneyan.com/writing/llm-patterns/
- v8.0 Product Completion Spec — `docs/specs/2026-04-27-v8-product-completion.md` §11 + §8
- ADR-0002 — `docs/adr/0002-calibration-set-protocol.md`
