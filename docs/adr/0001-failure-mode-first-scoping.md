# ADR-0001: Failure-Mode-First Scoping for AI-Eval Pillar

- **Status:** Accepted
- **Date:** 2026-04-27
- **Decision-Driver:** Franz Paul (benevolent dictator, ADR-0002)
- **Sprint:** v8.0 14-day sprint (2026-04-28 to 2026-05-11)
- **Supersedes:** none
- **Related:** [Spec](../specs/2026-04-27-v8-product-completion.md) §3, ADR-0002

## Context

The original v8.0 sprint plan (drafted 2026-04-27 morning) defined 7 pre-determined LLM-judge dimensions — frontmatter, structure, format, length, output_contract, completeness, and others — before observing real-world failures in SKILL.md files.

This was rejected during sparring-round review on the basis of three converging arguments from the practitioner-mainstream eval doctrine of 2024–2026:

1. **Hamel Husain ([evals-faq](https://hamel.dev/blog/posts/evals-faq/)):** "Error analysis is the most important activity in evals. Error analysis helps you decide what evals to write in the first place." Pre-defining dimensions inverts the canonical workflow.

2. **Shreya Shankar ("Who Validates the Validators?", EvalGen, UIST 2024 — criteria-drift discussion §7.3.1):** "It is impossible to completely determine evaluation criteria prior to human judging of LLM outputs." Her empirical finding from EvalGen user studies: criteria *drift* as users grade outputs — pre-defined rubrics get revised after observation begins (no specific percentage published in EvalGen).

3. **Schliff-internal:** the existing deterministic linter already scores 7 structural dimensions (frontmatter, triggers, structure, etc.). An LLM-judge scoring the *same* dimensions duplicates regex-checkable work and adds no value. The LLM-judge must target failures the deterministic linter *cannot* detect.

## Decision

**Phase 0 of the v8.0 sprint (Days 1–3) is dedicated to open-coded failure-mode analysis.**

1. Franz reads **30 SKILL.md** files sampled from corpus v1 (Anthropic 13 + Rezvani 17, balanced) — Husain's stated minimum of 30–50 traces for theoretical saturation. Reduced from initial 50 per Reviewer-1 finding (50 × ~10–15min/skill = 8–12h, exceeds 1.5–2h/day Franz-budget).
2. For each skill: free-form failure notes — what is wrong, why it is wrong, what a good version would do differently. No pre-existing rubric is consulted during reading.
3. Notes are clustered into a failure taxonomy via axial coding. Output: `docs/research/2026-04-28-skill-failure-modes.md`.
4. From the taxonomy, the LLM-Judge dimensions emerge — likely 2–4 dimensions covering semantic / contextual / disambiguation failure modes that the deterministic linter cannot detect.

The deterministic linter's existing dimensions remain untouched. The LLM-Judge layer is *additive*, not replacement.

**Hard kill-gate end-of-Day-3:** if no LLM-judge-worthy dimensions emerge that the deterministic linter does not already cover, the AI-Eval pillar is deferred to v8.1. v8.0 ships with deterministic scoring + library-API + auto-loop only.

## Consequences

**Positive:**

- AI-Eval pillar evaluates what cannot be regex-checked; provides genuine value-add over the existing linter.
- Aligns with Hamel/Shreya practitioner consensus, reducing "premature formalization" risk identified during sparring-round meta-finding.
- Failure taxonomy is a reusable artifact for v8.1+ AI-Eval expansion (more dims, more domains).
- Avoids the trap of building eval infrastructure before understanding failure modes.

**Negative:**

- Day 1–3 budget is locked to Franz's solo cognitive work; subagents can prepare (clone, pre-annotate, queue) but cannot replace the reading.
- If kill-gate triggers (no semantic dims emerge), AI-Eval pillar is dropped from v8.0 — narrative is simpler but less ambitious. Trade-off accepted.
- Phase 0 cannot start in parallel with Phase 1 worktree builds; serializes the first 3 days.

## Alternatives Considered

1. **Pre-defined 7-dim scope** *(rejected).* Efficient (saves Phase 0) but fails Hamel/Shreya doctrine; LLM-judge would duplicate existing deterministic linter coverage; adds no measurement-layer value.

2. **All-deterministic for v8.0, AI-Eval entirely in v8.1** *(rejected).* Too conservative; misses opportunity to ship a research-grade differentiator if Phase 0 yields a strong taxonomy. The failure-mode-first approach has built-in kill-gate that gracefully degrades to this if needed.

3. **Subagent-driven failure-mode coding** *(rejected).* The source-of-truth must be Franz's domain judgment, per benevolent-dictator pattern (Husain/Shankar FAQ "How many people should annotate?"). Delegating to subagents introduces a labeler-of-record problem that breaks calibration downstream.

4. **Hamel's 7-step llm-judge workflow exactly as written** *(adopted in spirit, adapted in scope).* His workflow assumes one mega-judge over open-ended text; Schliff has a hybrid where deterministic scoring covers structure and LLM-judge covers semantics. We adopt his "look at data first → iterate to ≥90% alignment → re-align on material change" but split judges per emergent dimension rather than mega-judge.

## References

- Hamel Husain, "LLM Evals FAQ" — https://hamel.dev/blog/posts/evals-faq/
- Hamel Husain, "Creating an LLM-as-Judge" — https://hamel.dev/blog/posts/llm-judge/
- Shankar et al., "Who Validates the Validators?" UIST 2024 — https://arxiv.org/abs/2404.12272
- Schliff Vision Spec v0.3 — `docs/specs/2026-04-25-measurement-layer-vision.md`
- v8.0 Product Completion Spec — `docs/specs/2026-04-27-v8-product-completion.md`
- Sparring-round meta-finding (2026-04-27): "Premature Formalisation" — discussed in this conversation; key insight that solo-maintainer eval engineering must lean toward less ceremony, more data, faster loops.

## Addendum (2026-04-28, Day 1) — Phase-0 corpus revised to stratified familiar-core + mini-probe

The Phase-0 reading sample defined above ("30 SKILL.md = Anthropic 13 + Rezvani 17, balanced") was revised on Day 1 after a 6-agent research evaluation (Karpathy / Hamel-Maven / linter-coverage / ecosystem / dimension-hypothesis / positioning lenses):

- **Rezvani dropped from Phase-0 reading.** The sole labeller of record (ADR-0002) lacks domain context on the Rezvani community skills (finance/compliance/PM) → low-confidence open-coding. Rezvani's role in the v8.0 *benchmark* corpus (spec §9) is a separate question, deferred to P2/B1.
- **Familiar-core added superpowers + Karpathy.** Anthropic (Apache-2.0 examples) + Karpathy `karpathy-guidelines` (analyze-only pending license) + obra/superpowers (MIT, maintainer uses daily) + Schliff dogfood. Famous, cleanly-licensed, high-confidence-labelable, strongest world-value case studies.
- **Representative mini-probe added.** Real messy community skills from the existing scored 120-file corpus (`docs/launch/corpus/`), filtered to maintainer-judgeable domains, to restore the representativeness all-familiar sacrifices (Hamel's non-negotiable: eval data must represent production input — corpus mean composite 61.7, 59% below grade C).
- **N is saturation-driven, not fixed at 30.** Husain's 30-50 is for heterogeneous traces; SKILL.md is homogeneous and should saturate earlier.

Full rationale in `docs/research/2026-04-28-skill-failure-modes.md` (Day-1 Scope Decision).
