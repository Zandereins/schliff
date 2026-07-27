# ADR-0004: Both Auto-Fix Modes Ship in v8.0; LLM-Judge is Advisory

- **Status:** Accepted
- **Date:** 2026-04-27
- **Decision-Driver:** Franz Paul (benevolent dictator)
- **Sprint:** v8.0 14-day sprint (2026-04-28 to 2026-05-11)
- **Related:** [Spec](../specs/2026-04-27-v8-product-completion.md) §4-P4, §7, ADR-0001

## Context

Schliff has two auto-fix UX surfaces under consideration:

- **Autonomous mode:** the loop runs, applies patches, re-scores, and only escalates to human at end-verify with N=10 sampling-gate.
- **Advisor mode:** every patch requires per-step human confirmation before being applied.

Two questions: (1) ship both or phase them; (2) what role does the LLM-Judge play in the auto-loop's keep/revert decision?

On (1), a phased rollout (advisor-only in v8.0, autonomous in v8.1) was the original plan. Hamel Husain's evals-faq notes that phased rollouts where "advisor never gets used" are a common failure mode — once a power user has tasted autonomous improvement they will not click through 50 confirmations, so advisor-only ships to nobody. On (2), Husain and Shankar's FAQ entry "Evaluator-as-Guardrail" is unambiguous: a slow, non-deterministic LLM-as-Judge should "almost never" be a synchronous gate. The existing deterministic 15-point regression guard in `skills/schliff/scripts/auto-improve.py:_has_dimension_regression()` is exactly the right shape for synchronous gating: fast, deterministic, dimension-aware.

**Doctrine adaptation note:** Husain/Shankar's "synchronous guardrail" warning ("you would almost never use a slow or non-deterministic LLM-as-Judge as a synchronous guardrail" — FAQ Evaluator-as-Guardrail) applies primarily to user-facing latency contexts (chat applications, real-time guardrails). Schliff's auto-loop is offline/asynchronous, so the latency argument does not directly apply. We adopt the doctrine on **stability and reproducibility grounds**: deterministic gating ensures `f(x)==f(x)` reproducibility (Vision-Spec §9 Principle 4), debuggable failure modes, and stable invariants for users. The latency caveat is non-binding here, but the determinism caveat fully binds.

## Decision

1. **Both modes ship in v8.0.** No phased rollout.
2. **Auto-loop gating uses the existing deterministic 15-point regression guard** in `skills/schliff/scripts/auto-improve.py`, in **both** modes. This is the keep/revert decision authority for individual patches.
3. **The LLM-Judge from Phase P3 is advisory.** It informs metrics, reporting, the public methodology page, and the AI-Eval headline number. It does **not** gate the auto-loop.
4. **Mode difference is purely UX surface:**
   - **Advisor:** per-patch human-confirm prompt before each `git apply`.
   - **Autonomous:** end-verify with N=10 sampling-gate to human; loop runs to plateau or target without per-patch interruption.
5. Autonomous mode is the documented default in the README and CLI help. Advisor is opt-in via flag.

## Consequences

**Positive:**

- One gating-mechanism (the deterministic guard) means one place to audit and tune for regressions; reduces cognitive surface area.
- LLM-Judge stays slow/expensive but advisory — it can be Sonnet-4.5 with N=5 self-consistency (ADR-0006) without blocking the inner loop.
- Both modes ship → no "advisor never gets used" failure mode.

**Negative:**

- Two modes to document, support, and test in the README/CHANGELOG.
- Users who *want* LLM-judgment to block patches must wait for v8.1 (an opt-in `--llm-gate` flag is on the v8.1 backlog).

## Alternatives Considered

1. **Phased: advisor v8.0, autonomous v8.1** *(rejected).* Hamel-flagged anti-pattern; advisor-only ships to nobody once power users exist. Both modes wired to the same deterministic gate is no more code than just one.
2. **LLM-Judge as synchronous keep/revert gate** *(rejected).* Husain/Shankar "Evaluator-as-Guardrail" rule. Adds 5–30s + cost per patch; non-determinism makes the loop non-reproducible; regressions on the judge itself silently break gating.
3. **Autonomous-only (drop advisor entirely)** *(rejected).* Kills the trust on-ramp for first-time users; "I want to see what it would do before letting it run" is a real user need that costs ~50 LOC to satisfy.

## References

- Husain & Shankar, "LLM Evals FAQ", "Evaluator-as-Guardrail" section — https://hamel.dev/blog/posts/evals-faq/
- Schliff source: `skills/schliff/scripts/auto-improve.py`, function `_has_dimension_regression()`
- v8.0 Product Completion Spec — `docs/specs/2026-04-27-v8-product-completion.md` §4-P4 (auto-loop), §7 (Goodhart guardrails)
- ADR-0001 — `docs/adr/0001-failure-mode-first-scoping.md`
