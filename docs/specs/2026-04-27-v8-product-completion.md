---
date: 2026-04-27
status: in-progress (v0.2 — post-review revision)
type: product-spec
sprint-window: 2026-04-28 to 2026-05-11 (14 days)
extends: docs/specs/2026-04-25-measurement-layer-vision.md (v0.3)
related-adrs:
  - docs/adr/0001-failure-mode-first-scoping.md
  - docs/adr/0002-calibration-set-protocol.md
  - docs/adr/0003-composio-corpus-exclusion.md
  - docs/adr/0004-both-modes-ship-judge-advisory.md
  - docs/adr/0005-per-dimension-reliability-reporting.md
  - docs/adr/0006-same-family-llm-default.md
  - docs/adr/0007-spec-versioning-via-adr.md
review-history:
  - 2026-04-27 v0.1 — initial spec (FLAG verdicts from 3-reviewer pass)
  - 2026-04-27 v0.2 — post-review revision: F1 packaging clarified; KILL-GATE 2 moved Day 7→8 with N=100 + Wilson CI + κ≥0.7; time-slip-budget added; K9 Anthropic-competition risk added; Goodhart stack +3 items; binary-only scale; sub-reviewer pattern per kill-gate; Phase-0 corpus 50→30 (Husain min); Panickssery arXiv ID corrected (2410.21819 → 2404.13076); ADR-Spec cross-refs aligned
  - 2026-04-27 v0.3 — re-review pass: Wilson math correction (CI floor ≥80% was unreachable at p=0.85; lowered to ≥75% with explicit math note — R3-finding); sub-reviewer hardened (cross-family + concrete-reject + override gated by written rationale + 24h cooldown + auto-descope); time-slip anchored to nearest preceding kill-gate (not Day 1); K9 trigger criteria explicit; forensic-log isolation (item 14) added to Goodhart stack against context-stuffing attack; cumulative-cap +lifetime ≤300 lines (window-reset attack); F1 interface-freeze Day 4 vs implementation-freeze Day 5 split (unblocks wt-judge); §6 wt-judge dead-alternative path stripped
tags: [v8, product-completion, sprint, ai-eval, auto-loop]
---

# Schliff v8.0 Product Completion — 14-Day Sprint Specification

## 1. Executive Summary

This spec governs a 14-day sprint (2026-04-28 to 2026-05-11) to ship Schliff v8.0 with four user-defined pillars:

1. **P1 — Success Stories + Use Cases** from a real-skill corpus
2. **P2 — Skills measurably improved** through Schliff (closed-corpus benchmark with provable deltas)
3. **P3 — AI-Eval pillar live**, calibrated, reliable
4. **P4 — Auto-fix loop** in both autonomous and advisor modes, with provable Goodhart-resistance

The sprint adopts a **failure-mode-first** approach (Husain/Shankar 2024–2026 doctrine): error analysis precedes infrastructure; LLM-judge dimensions emerge from observed failure patterns rather than being pre-defined; deterministic scoring remains the gate, LLM-judge is advisory (never a synchronous guardrail).

This spec extends but does not supersede `2026-04-25-measurement-layer-vision.md` (v0.3). It collapses Säule 1 (Library API) and a partial Säule 2 (calibrated AI-Eval, scope emerges from Phase 0) into a single 14-day sprint. Full Säule 2 (Eval-Adapter-Suite) and Säulen 3–5 remain deferred per Vision-Spec roadmap.

## 2. Pillar-to-Säule Mapping

| User Pillar | Vision Säule | Net-new vs Vision v0.3 |
|---|---|---|
| P1 Success Stories | Säule 4 evidence base | Yes — case-study artifacts not previously scoped |
| P2 Closed-corpus benchmark | Säule 1 + corpus for OQ3 | Reuses corpus-study work originally scoped for Säule 2 |
| P3 AI-Eval calibrated | New sub-pillar (failure-mode-driven) | Promotes LLM-judge from opt-in fallback to measured subsystem with public reliability |
| P4 Auto-fix loop both modes | Existing `schliff:auto` + `evolve/` | UX modes + Goodhart hardening + advisor surface |

**Precondition: ARCH-001 Library API.** All four pillars consume the same callable surface (`from schliff import score, evaluate, observe`). Building it once unblocks all four; not building it forces three forks of the CLI subprocess pattern.

## 3. Failure-Mode-First Pivot

The original plan defined 7 LLM-judge dimensions before observing data. **This was rejected during sparring-round review** based on:

> "Error analysis is the most important activity in evals. Error analysis helps you decide what evals to write in the first place." — Hamel Husain, [evals-faq](https://hamel.dev/blog/posts/evals-faq/)

> "It is impossible to completely determine evaluation criteria prior to human judging of LLM outputs." — Shankar et al., EvalGen UIST 2024 (criteria-drift discussion, §7.3.1)

**Revised approach (ADR-0001):**

- Days 1–3: Franz reads a **stratified familiar-core + representative mini-probe** corpus — Anthropic + Karpathy + superpowers + dogfood (familiar, high-confidence labels), plus messy community probe skills from `docs/launch/corpus/` (representativeness), **saturation-driven** (Husain's 30–50 is for heterogeneous traces; SKILL.md is homogeneous and saturates earlier — revised Day-1 after 6-agent evaluation, see ADR-0001 addendum). Open-coded failure notes. Cluster into taxonomy.
- LLM-Judge dimensions emerge from this taxonomy, not pre-definition.
- Deterministic Linter (existing **7 default dimensions, 1 opt-in `security`**) continues to score structure.
- LLM-Judge targets what the linter CANNOT see — semantic coherence, contextual appropriateness, disambiguation, output_contract↔description consistency.

**Hard kill-gate end-of-Day-3:** if no LLM-judge-worthy dimensions emerge that the linter doesn't already cover, AI-Eval pillar is deferred to v8.1; v8.0 ships with deterministic scoring + library-API + auto-loop only. Sub-reviewer subagent pass required to confirm "this taxonomy is genuinely beyond linter coverage" (mitigates confirmation bias).

## 4. Pillar Sub-Components

### Foundation (precondition for P1, P2, P3, P4)

- **F1** `lib-api`: introduces a top-level Python package shim (`schliff/__init__.py` + `schliff/api.py`) that re-exports from `skills.schliff.scripts.*` (composite, evaluate, observe). `pyproject.toml` `[tool.setuptools.packages.find].include` extended from `["skills*"]` to `["skills*", "schliff*"]`. Public surface: `from schliff import score, evaluate, observe` — each accepting `allowed_root: Path` for path-traversal security. Existing `schliff = "skills.schliff.scripts.cli:main"` console-script entrypoint is preserved (no breaking change to v7.2.x users). **F1 is interface-frozen by EOD Day 4** (signatures + F3 types ready — unblocks wt-judge consumers starting same day) **and implementation-frozen by EOD Day 5** (working code, no API changes thereafter — Risk K4 mitigation).
- **F2** `corpus-frame`: closed corpus directory layout + manifest schema + frozen-snapshot policy
- **F3** `metrics-contract`: `ScoreDelta`, `JudgeAgreement`, `FixOutcome` typed records — single source for all four pillars

### P1 — Success Stories

- A1 corpus selection (Anthropic 13 + Rezvani 108 + Schliff dogfood ~20 + Synthetic ~50 ≈ 191 skills)
- A2 baseline benchmark run
- A3 improvement campaigns (consumes P4)
- A4 case-study writeups: before/after metrics, narrative, reproducer command
- A5 publication: `docs/case-studies/`, links from README

### P2 — Closed-corpus benchmark

- B1 corpus contract: `benchmarks/corpus/v1/manifest.jsonl` with per-skill SHA, license, included-flag
- B2 baseline scoring infra (consumes F1, F3)
- B3 determinism test: `f(x)==f(x)` across runs (Vision-Spec §9 Principle 4)
- B4 anti-gaming probes: 2–3 inflate-attempts seeded; benchmark must reject
- B5 public report generator: HTML/MD with score histograms + commit hash

### P3 — AI-Eval (LLM-as-judge, dims emerge from Phase 0)

- C1 judge harness: `evaluate(..., judge="llm")` with deterministic prompt template + pinned model + temp 0.3
- C2 calibration set: 100–150 binary pass/fail with critique (grow iteratively from Phase-0 30-set, Solo Franz benevolent dictator)
- C3 self-consistency probe: N=5 plurality vote, dual-order for position bias
- C4 reliability metric: per-dimension TPR + TNR + Cohen's κ (NOT raw agreement)
- C5 safety: prompt-injection harness, output-schema validation, refusal handling
- C6 cost ledger: tokens/run, budget guard, cross-family fallback only on disagreement

### P4 — Auto-fix loop (both modes, Goodhart-hardened)

- D1 audit existing `schliff:auto` (`auto-improve.py` is real, **~620 LOC**, has 15pt-regression-guard via `_has_dimension_regression()` but missing explicit Goodhart guards)
- D2 hallucination bound + Goodhart guardrail stack (see §7)
- D3 autonomous mode: run-to-plateau, single end-verify, N=10 sampling-gate to human
- D4 advisor mode: per-patch human-confirm UX, diff narration, accept/reject/edit
- D5 reproducibility manifest: every fix run emits `fix-receipt.json`

## 5. 14-Day Sprint Plan

| Day | Franz | Subagents (parallel, max 5) | Output |
|---|---|---|---|
| **0 today** | Greenlight + spec/ADR review | Spec + 7 ADRs scaffolding (this commit) | Plan-Artefakte committed |
| **1 Tue** | 10 skills open-coded (~10–15 min/skill) | Korpus-Cloner pin SHAs + pre-annotate | 10 skills coded |
| **2 Wed** | 20 skills open-coded (30 total) | Live-clusterer aggregates notes → taxonomy draft | 30 skills coded |
| **3 Thu** | Failure-modes → emergent LLM-Judge dims; **sub-reviewer pass** confirms "beyond linter" | 4 parallel: scaffold lib-api, judge-harness, corpus-runner, fix-receipt schema | **KILL-GATE 1** |
| **4 Fri** | Holdout labelling Batch-1 (25 items) | 3 worktrees: WT-foundation, WT-judge, WT-autoloop; **F1 interface-frozen EOD** (signatures + F3 types ready) | 3 worktrees with v0 |
| **5 Sat** | Holdout Batch-2 (25 → 50 total) | TDD-builder per worktree + security-review on lib-api; **F1 implementation-frozen EOD** | trunk-v8 ready |
| **6 Sun** | Judge iteration v0→v1 + 5-disagreement spot-check | Judge runs full holdout; reports TPR/TNR per dim with **Wilson 95% CI** | Judge v1 |
| **7 Mon** | Judge v1→v3 (Hamel-style 3 iterations); sub-reviewer pass on intermediate metrics | Goodhart guards finalized: semantic-floor + Pareto + cycle-detect + content-padding guards | **EARLY WARNING**: TPR trending ≥80% across last-3 iters on N=50; if not → escalate dim-scope review |
| **8 Tue** | Holdout grow to 100 + re-grade pass (criteria drift) | Auto-Loop ↔ lib-api wiring; advisor-mode UX | Auto-Loop end-to-end on 1 skill; **KILL-GATE 2 (HARD)**: TPR ≥85% with Wilson CI lower-bound ≥80% on N=100, κ ≥ 0.7 per dim, **sub-reviewer pass** confirms statistical validity |
| **9 Wed** | Architecture review (1h) + corpus-run kickoff | **KORPUS-RUN**: 100 skills × auto-improve loop, 20-fold parallel, ~30–60 min wall | Korpus-Run dataset |
| **10 Thu** | Outlier triage on 10–15 unexpected cases (shrink-fallback if 60+: see §11) | 5 parallel case-study writers per top-improved skill | 5 case studies draft |
| **11 Fri** | Outlier-fix re-run + holdout re-grade | Per-dim reliability report + Cohen's κ compute | **KILL-GATE 3**: ≥3 positive case studies + **sub-reviewer pass** on no-Goodhart-attack-escaped |
| **12 Sat** | README + methodology doc review | Simplify-pass + security-review + code-reviewer all worktrees | trunk-v8 release-ready |
| **13 Sun** | Release v8.0 + first public posts | Vision-Spec ADR-pointer addendum, CHANGELOG, badge bust | **v8.0 LIVE** |
| **14 Mon** | Buffer / Schlaf | — | — |

## 6. Multi-Worktree Topology

| Worktree | Branch | Owns | Conflict-zone | Integration |
|---|---|---|---|---|
| `wt-foundation` | `feat/v8-lib-api` | F1, F3, top-level `schliff/__init__.py`, `schliff/api.py`, `pyproject.toml` packages.find | High — touches root module + pyproject | Merge to `trunk-v8` end of Day 5 |
| `wt-judge` | `feat/v8-judge-calibration` | C1–C6 in `schliff/judge/` | Low — new subpackage | Daily push, weekly merge |
| `wt-autoloop` | `feat/v8-autofix-modes` | D1–D5; updates `skills/schliff/scripts/auto-improve.py` | Medium | Coord with foundation on shared types |
| (corpus + cases happen in main on `trunk-v8` during Phase 2–3) | | | | |

**Trunk:** `trunk-v8` (long-lived integration off `main`). Worktrees PR into `trunk-v8`; only Phase-4 close merges `trunk-v8 → main`.

**Conflict-zone ownership:**

- Top-level `schliff/__init__.py`, `schliff/api.py`, `pyproject.toml` `packages.find` → wt-foundation only until Day 5
- `skills/schliff/scripts/auto-improve.py` → wt-autoloop only
- `pyproject.toml` (deps for `schliff[judge]` extra) → wt-judge proposes, foundation merges
- `CHANGELOG.md` → append-only by phase owner

## 7. Goodhart-Guardrail Stack (P4)

Concrete numbers from Goodhart-Researcher Agent + Manheim/Garrabrant 2018 + Kwa et al. NeurIPS 2024 + Reviewer-3 red-team additions:

1. **Held-out validation set: K=20 untouched skills.** Frozen at v0; never seen by patch-LLM.
2. **Cross-family judge: ONLY on disagreement** `|s_claude − s_gpt| > 0.15` on a holdout-dimension.
3. **Diff-size limit: D=40 lines/iter, max 15% of file length.**
4. **Cumulative diff-size cap: ≤100 lines across last-6-iters (sliding window) AND ≤300 lines per-skill-lifetime** (prevents both split-iteration drift attack AND window-reset attack — R3-findings v0.1+v0.3).
5. **Per-section diff caps:** frontmatter ≤5 lines/iter, body ≤35 lines/iter (prevents whole-section rewrite attack).
6. **Semantic-similarity floor: τ_sem=0.92** (sentence-BERT cosine vs. iter-0 baseline, NOT vs. previous step).
7. **Length-normalized cosine:** computed on token-budget-normalized excerpts, not full file (prevents content-padding attack — R3-finding).
8. **Pareto rule: ε=0.03 per-dim regression tolerance.** Tighter than current "composite up" rule.
9. **Cycle window: k=6.** SHA-256 of normalized SKILL.md; abort on cycle ≤6.
10. **Stop on plateau: M=5 iters with val-gain < 0.01.**
11. **Human checkpoint: every N=10 accepted patches** in autonomous mode (sampling-gate).
12. **Forensic log:** JSONL at `.schliff/audit/<run-id>.jsonl` per-iter `{parent_hash, child_hash, full_diff, all_scores_per_judge, gate_outcomes}`.
13. **Final report on TEST/HOLDOUT only**, run once at end. No selection on test scores.
14. **Forensic-log isolation:** patch-LLM context NEVER includes the audit JSONL or §7 guardrail thresholds verbatim. Guardrails are enforced on the *receiving* end after patch generation, never exposed to the *proposer* (mitigates adversarial-Goodhart context-stuffing where the patch-LLM optimizes exactly to known boundaries — Manheim/Garrabrant extremal-Goodhart, R3 v0.3 finding). Auto-loop implementation must verify this isolation in tests (`assert audit_log not in patch_llm_context`).

## 8. AI-Eval Architecture (P3)

- **Primary judge:** Claude Sonnet 4.5 (or 4.7 if available) pinned by exact model+date
- **Scale:** **Binary pass/fail with rubric-anchored critique** (per ADR-0002, Husain canonical: "If your evaluations consist of metrics LLMs score on a 1-5 scale, you're doing it wrong"). 0–5 Likert deferred to v8.1+ if dimensional gradation becomes necessary.
- **Self-consistency:** N=5 with temp 0.3, plurality vote per dimension
- **Position-bias:** dual-order evaluation (A,B) and (B,A); average; flag disagreement
- **Cross-family fallback:** GPT-5 / Gemini 2.5 Pro invoked ONLY on disagreement (Trust-or-Escalate ICLR 2025 cascade pattern)
- **Output schema:** Pydantic via Anthropic structured outputs `.parse()`
- **Reproducibility:** prompt SHA in JSONL log, temp ≤0.3, model snapshot pinned
- **Sandbox:** zero network during scoring (Vision-Spec invariant)

## 9. Korpus v1 (closed snapshot)

| Source | Pin SHA | Skills | License | Notes |
|---|---|---|---|---|
| anthropics/skills | `5128e186` | 13 (text-only, exclude docx/pdf/pptx/xlsx) | NOASSERTION (mixed) | Goldstandard — improving Anthropic's own skills is strongest marketing. text-only files are MIT-compatible per THIRD_PARTY_NOTICES.md; binary files (docx/pdf/pptx/xlsx) source-available, excluded |
| alirezarezvani/claude-skills | `f567c61d` | 108 (`.claude/skills/` dir only, exclude `.gemini`/`.cursor` copies) | MIT | Active community, clear license |
| Schliff dogfood | current trunk | ~20 | MIT | Internal eat-own-dogfood signal |
| Synthetic variations | n/a | ~50 | n/a | Stratified perturbations of above for robustness probes |
| **Total v1** | — | **~191** | — | |

**Excluded:** Composio (864 skills) — license unclear (no LICENSE file), deferred to v8.1. See ADR-0003.

**Phase-0 reading-corpus note (2026-04-28 addendum):** the *benchmark* corpus above (P2) is distinct from the *Phase-0 failure-mode reading* corpus, which was revised on Day 1 to a stratified familiar-core (Anthropic + Karpathy + obra/superpowers MIT + dogfood) + representative mini-probe (messy community skills from `docs/launch/corpus/`). Rezvani is dropped from Phase-0 reading; its inclusion in this *benchmark* corpus is under B1 review (note: at pinned SHA `f567c61d` Rezvani has no `.claude/skills/` dir and yields ~239 skills, not 108 — see `benchmarks/corpus/v1/README.md` Known discrepancies). See ADR-0001 Day-1 addendum.

## 10. Risk Register Top 9

| # | Risk | P | I | Mitigation | Early-warning |
|---|---|---|---|---|---|
| K1 | Phase-0 fails to yield LLM-judge-worthy dims | M | H | Kill-gate 1 → v8.0 ships deterministic-only | Day 3 EOD: taxonomy <3 distinct semantic clusters |
| K2 | Judge can't hit ≥85% TPR by Day 8 (with N=100, CI bound) | M | H | Kill-gate 2 → narrow to 2 dims | Day 7 PM: trend not ≥80% across iters |
| K3 | Auto-fix loop hallucinates plausible-but-wrong edits | M | H | Goodhart stack §7 (13 guards); anti-gaming corpus B4 | Anti-gaming probe shows score-up on inflate-attempt |
| K4 | F1 library-API design churns mid-build | M | H | Day-5 freeze gate: F3 types committed before consumers start; F1 packaging design Day 1 | Two consumers request same signature change Day 6 |
| K5 | Korpus-run reveals 30–60% issues (typical first-run) | H | M | Day 9–10 buffer for diagnostic+fix+re-run; **shrink-fallback to 50 skills if 60+ broken** | Day 9 EOD: <50 skills successfully scored |
| K6 | Solo-engineer burnout / sprint-day slip | M | H | Day-14 hard-cap; kill-gates force descope; protect sleep; time-slip-budget §11 | Two consecutive days with <80% planned output |
| K7 | LLM API cost overrun | L | M | Same-family default (ADR-0006); cost ledger per Day | Day 7 spend >$100 |
| K8 | Reviewer-agent gates run serially, blow cycle time | M | M | Drop reviewer-gates to "optional per ADR" not "mandatory per phase" | First gate >2h wall |
| **K9** | **Anthropic releases competing skill-quality-checker mid-sprint** | **M (60% per memory)** | **M** | **Pre-registered response: (a) reframe Schliff as "deterministic complement to X" — README + positioning rewrite (~1 day), OR (b) accelerate launch −3 days dropping P3 (~3-5 day disruption — recompiles sprint), OR (c) emphasize Schliff's research-grade reliability metrics (per-dim TPR/TNR/κ) as differentiator (only valid if Kill-Gate 2 passed)** | **Trigger signals (any one fires response): (1) Anthropic blog post about skill quality/linting/eval, (2) `anthropics/skills` repo gets `lint`/`quality`/`eval` directory or GitHub Action, (3) Anthropic Skills SDK official announcement, (4) @AnthropicAI X post on skill quality. Monitor: @AnthropicAI feed + GitHub watch on anthropics/skills + claude.ai changelog RSS** |

## 11. Kill-Switches (non-negotiable)

**Output-based kill-gates:**

1. **EOD Day 3:** Phase-0 must yield concrete LLM-judge dimensions not covered by deterministic linter, **AND sub-reviewer subagent pass** confirms "this taxonomy is genuinely beyond linter coverage" (mitigates confirmation bias on Solo authority). ELSE: AI-Eval pillar deferred to v8.1.
2. **EOD Day 7 (early warning, not hard gate):** TPR trending ≥80% across last-3 judge iterations on N=50 holdout. ELSE: pause iteration, escalate dim-scope review, treat Day 8 with extreme caution. Reviewer-3 finding: N=50 is statistically below noise threshold (95% Wilson CI on TPR=0.85 ≈ [0.72, 0.93]) — must NOT be hard kill-gate.
3. **EOD Day 8 (HARD kill-gate):** Judge must hit ≥85% TPR with **95% Wilson CI lower bound ≥75%** on N=100 holdout (math: Wilson(p=0.85, N=100) → CI lower ≈ 0.767, passes ≥0.75 floor; Wilson(p=0.80, N=100) → CI lower ≈ 0.713, fails — gate is statistically meaningful, not noise; original v0.2 ≥0.80 floor was unreachable at p=0.85 per R3 v0.2 finding), **AND κ ≥ 0.7 per published dimension**, **AND sub-reviewer pass** confirming statistical validity (CI calculation, sample independence, dual-order). ELSE: dim-scope shrinks to 2-3 (or single dim), or pillar deferred.
4. **EOD Day 11:** ≥3 positive case studies (positive score-delta + no Goodhart-anomaly + **sub-reviewer pass** confirming "no goodhart attack escaped guardrails on §7 stack"). ELSE: autonomous-mode deferred to v8.1, ship advisor-only.

**Time-based slip budget (Reviewer-3 finding — explicit response per slip magnitude). Slip is measured against the nearest preceding output-based kill-gate timestamp (Day 3 / Day 8 / Day 11), NOT against Day 1 — so "+1d slip" only counts after the most recent kill-gate has passed:**

- **+1 day slip past nearest preceding kill-gate** → autonomous-mode deferred to v8.1 (ship advisor-only)
- **+3 days slip past nearest preceding kill-gate** → AI-Eval pillar deferred to v8.1 (ship lib-api + auto-loop + corpus benchmark only)
- **+7 days slip past nearest preceding kill-gate** → cancel sprint, ship v8.0 = lib-api + corpus benchmark only

**Day-14 hard-cap.** Whatever's done ships; remainder becomes v8.1 backlog with explicit "known not-done" CHANGELOG section.

**Sub-reviewer pattern (mitigates Solo confirmation bias):** for each of the four output-based kill-gates, a separate subagent (not the one performing the work) reviews the artifacts (taxonomy / TPR holdout / CI math / Goodhart-anomaly check / case-studies) and confirms or denies the gate-pass. Cheap insurance (~30min per gate) against confirmation bias on solo-judgment decisions.

**Sub-reviewer hardening (R3 v0.3):**

- Sub-reviewers must be **cross-family** (different model family from the artifact producer; mitigates Panickssery 2024 self-preference where same-family judges hallucinate PASS on artifacts they see).
- Sub-reviewer must surface **at least one concrete artifact-element it would have rejected** (forces grounded judgment vs. vibes-PASS).
- Sub-reviewer's verdict is advisory in form but **quasi-binding in process**: if Franz overrides a sub-reviewer FAIL, override requires (1) **written rationale committed to CHANGELOG**, (2) **24h cooldown** before re-running gate, (3) the override **auto-flips the affected pillar to descope-defer in v8.1** (cannot be reversed mid-sprint). This prevents Franz-in-confirmation-bias-mode from papering over a FAIL with one sentence.

## 12. Cost Budget

LLM call estimate:

- Judge calibration: 3 iters × 100 holdout × 5 self-consistency = ~1500 calls
- Korpus auto-loop: 100 skills × ~10 iters × 2 calls/iter = ~2000 calls
- Cross-family fallback: ~10% disagreement × Gemini = ~350 calls
- Re-grade + buffer: ~1000 calls
- **Total: ~5000 calls**
- **Cost: ~$50–150 USD** at Sonnet 4.5 ($3/$15 per 1M tok), assuming avg 2k input + 500 output per call (math: 5000 × (2k in + 0.5k out) = 10M in + 2.5M out × ($3 + $15)/1M = $30 + $37.50 = ~$67.50 — center of range)

Cross-family-everywhere alternative would have been ~$500+. Saved by ADR-0006.

## 13. Decisions encoded as ADRs

| ADR | Decision | Status |
|---|---|---|
| 0001 | Failure-mode-first scoping | Accepted |
| 0002 | Calibration-set protocol — solo iterative | Accepted |
| 0003 | Composio corpus exclusion | Accepted |
| 0004 | Both modes ship; LLM-judge advisory | Accepted |
| 0005 | Per-dimension reliability publication | Accepted |
| 0006 | Same-family LLM default; cross-family fallback | Accepted |
| 0007 | Spec versioning via ADR addenda | Accepted |

## 14. References

**Internal:**

- Vision Spec v0.3 — `docs/specs/2026-04-25-measurement-layer-vision.md`
- ADRs — `docs/adr/0001-*.md` through `0007-*.md`

**External:**

- Husain & Shankar, "LLM Evals: Everything You Need to Know" — https://hamel.dev/blog/posts/evals-faq/
- Hamel Husain, "Creating an LLM-as-Judge That Drives Business Results" — https://hamel.dev/blog/posts/llm-judge/
- Shankar et al., "Who Validates the Validators?" UIST 2024 — https://arxiv.org/abs/2404.12272
- Trust-or-Escalate, ICLR 2025 — https://arxiv.org/abs/2407.18370 — Cascaded Judging
- GEPA, Agrawal/Khattab et al., ICLR 2026 — https://arxiv.org/abs/2507.19457 — Pareto-aware selection
- Manheim & Garrabrant 2018 — "Categorizing Variants of Goodhart's Law" — https://arxiv.org/abs/1803.04585
- Kwa et al., NeurIPS 2024 — "Catastrophic Goodhart" — https://arxiv.org/abs/2407.14503
- Panickssery, Bowman, Feng, NeurIPS 2024 — "LLM Evaluators Recognize and Favor Their Own Generations" — https://arxiv.org/abs/2404.13076
- Rating Roulette, Haldar & Hockenmaier, EMNLP 2025 — https://arxiv.org/abs/2510.27106 — self-inconsistency on subjective dimensions
