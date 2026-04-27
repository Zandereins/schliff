---
date: 2026-04-28
status: in-progress (Phase 0 — Days 1-3)
type: research
phase: 0 (failure-mode analysis)
sprint: v8.0
target-completion: 2026-04-30 EOD
related-spec: docs/specs/2026-04-27-v8-product-completion.md
related-adrs: docs/adr/0001-failure-mode-first-scoping.md
methodology: Husain (evals-faq) + Shankar (EvalGen UIST 2024) — open-coded → axial-coded failure taxonomy
---

# SKILL.md Failure-Mode Analysis — Phase 0

## Objective

Read **30 real SKILL.md** files (no pre-existing rubric), write open-coded failure notes, cluster into a taxonomy. Output drives the LLM-Judge dimension scope for v8.0 P3 (AI-Eval pillar).

**Hard kill-gate end-of-Day-3:** if no LLM-judge-worthy dimensions emerge that the deterministic linter does not already cover, AI-Eval pillar deferred to v8.1.

## Method (Husain/Shankar canonical pattern)

1. **Read individually, no rubric in mind.** Free-form notes per skill — what's wrong, why, what would a good version do differently.
2. **Open coding (Day 1-2).** First-pass tags emerge from notes — use `#tag-name` prefix for searchability.
3. **Axial coding (Day 3).** Cluster open codes into ≥3 distinct semantic clusters. Those become candidate LLM-Judge dimensions.
4. **Sub-reviewer pass (Day 3 EOD).** Cross-family subagent confirms taxonomy is genuinely beyond deterministic-linter coverage (Kill-Gate 1).

**Constraint:** the deterministic linter (skills/schliff/scripts/scoring/registry.py) already scores 7 default dimensions: structure, triggers, quality, edges, efficiency, composability, clarity. The LLM-Judge layer must target what the deterministic layer cannot detect — semantic, contextual, disambiguating failures.

## Corpus Sample (n=30, balanced 13 + 17)

| #  | Source                       | Skill name           | Local path           | Read-date | Note-tag |
|----|------------------------------|----------------------|----------------------|-----------|----------|
| 1  | anthropics/skills            | _(populate Day 1)_   | _(populate Day 1)_   | _(date)_  | #_(tag)_ |
| 2  | anthropics/skills            |                      |                      |           |          |
| 3  | anthropics/skills            |                      |                      |           |          |
| 4  | anthropics/skills            |                      |                      |           |          |
| 5  | anthropics/skills            |                      |                      |           |          |
| 6  | anthropics/skills            |                      |                      |           |          |
| 7  | anthropics/skills            |                      |                      |           |          |
| 8  | anthropics/skills            |                      |                      |           |          |
| 9  | anthropics/skills            |                      |                      |           |          |
| 10 | anthropics/skills            |                      |                      |           |          |
| 11 | anthropics/skills            |                      |                      |           |          |
| 12 | anthropics/skills            |                      |                      |           |          |
| 13 | anthropics/skills            | _(13 anthropic)_     |                      |           |          |
| 14 | alirezarezvani/claude-skills |                      |                      |           |          |
| 15 | alirezarezvani/claude-skills |                      |                      |           |          |
| 16 | alirezarezvani/claude-skills |                      |                      |           |          |
| 17 | alirezarezvani/claude-skills |                      |                      |           |          |
| 18 | alirezarezvani/claude-skills |                      |                      |           |          |
| 19 | alirezarezvani/claude-skills |                      |                      |           |          |
| 20 | alirezarezvani/claude-skills |                      |                      |           |          |
| 21 | alirezarezvani/claude-skills |                      |                      |           |          |
| 22 | alirezarezvani/claude-skills |                      |                      |           |          |
| 23 | alirezarezvani/claude-skills |                      |                      |           |          |
| 24 | alirezarezvani/claude-skills |                      |                      |           |          |
| 25 | alirezarezvani/claude-skills |                      |                      |           |          |
| 26 | alirezarezvani/claude-skills |                      |                      |           |          |
| 27 | alirezarezvani/claude-skills |                      |                      |           |          |
| 28 | alirezarezvani/claude-skills |                      |                      |           |          |
| 29 | alirezarezvani/claude-skills |                      |                      |           |          |
| 30 | alirezarezvani/claude-skills | _(17 rezvani)_       |                      |           |          |

(Subagent populates Day 1 morning via `Korpus-Cloner` per spec §5 Day-1 row.)

## Open-coded Failure Notes (Days 1-2)

(One subsection per skill, ~50-200 words free-form. Use `#tag-prefix` consistently for clustering.)

### Skill 01: _(name)_

_(Franz writes during Day 1)_

### Skill 02: _(name)_

_(...)_

### Skill 03: _(name)_

_(...)_

### Skill 04: _(name)_

### Skill 05: _(name)_

### Skill 06: _(name)_

### Skill 07: _(name)_

### Skill 08: _(name)_

### Skill 09: _(name)_

### Skill 10: _(name)_

### Skill 11: _(name)_

### Skill 12: _(name)_

### Skill 13: _(name)_

### Skill 14: _(name)_

### Skill 15: _(name)_

### Skill 16: _(name)_

### Skill 17: _(name)_

### Skill 18: _(name)_

### Skill 19: _(name)_

### Skill 20: _(name)_

### Skill 21: _(name)_

### Skill 22: _(name)_

### Skill 23: _(name)_

### Skill 24: _(name)_

### Skill 25: _(name)_

### Skill 26: _(name)_

### Skill 27: _(name)_

### Skill 28: _(name)_

### Skill 29: _(name)_

### Skill 30: _(name)_

## Axial Clustering (Day 3 morning)

Top failure clusters (target: ≥3 distinct semantic categories):

### Cluster A — _(name)_

- **Description:**
- **Member skills (#):**
- **Common open-codes:**
- **Deterministic-linter coverage:** yes / no / partial — _(brief why)_
- **LLM-Judge value-add hypothesis:** _(what would the judge measure that the linter misses?)_

### Cluster B — _(name)_

- **Description:**
- **Member skills (#):**
- **Common open-codes:**
- **Deterministic-linter coverage:** yes / no / partial — _(brief why)_
- **LLM-Judge value-add hypothesis:**

### Cluster C — _(name)_

- **Description:**
- **Member skills (#):**
- **Common open-codes:**
- **Deterministic-linter coverage:** yes / no / partial — _(brief why)_
- **LLM-Judge value-add hypothesis:**

_(Add D, E, etc. if more clusters emerge.)_

## LLM-Judge Dimensions — Emergent (Day 3 PM)

Based on clustering, the following dimensions show positive value-add over deterministic linter:

1. **`dim_name_1`:** _(rubric anchor description, binary-pass criterion: "passes if ___, fails if ___")_
2. **`dim_name_2`:** _(...)_
3. **`dim_name_3`:** _(...)_
4. **`dim_name_4`:** _(...)_

(Target: 2-4 dimensions. If <2 emerge with positive value-add, **KILL-GATE 1 fires** — AI-Eval pillar deferred to v8.1, sprint shrinks to lib-api + auto-loop + corpus benchmark only.)

## Sub-Reviewer Verdict (Day 3 EOD, cross-family subagent)

- **Taxonomy is beyond linter coverage:** PASS / FAIL
- **Cross-family judge model used:** _(name + version)_
- **Concrete element it would have rejected (if FAIL):** _(specific cluster + reason)_
- **Specific clusters at risk of duplicating linter:** _(list, if any)_

## Decision (Day 3 EOD)

**KILL-GATE 1: [PASS / FAIL]**

If PASS: dimensions [list] proceed to Phase 1 judge harness build (Day 4).
If FAIL: AI-Eval pillar deferred to v8.1. Sprint shrinks. Update spec §11 + ADR-0001 with kill-gate-trigger record.

## References

- Husain "LLM Evals FAQ" — error-analysis workflow https://hamel.dev/blog/posts/evals-faq/
- Husain "LLM-as-Judge" — 7-step alignment workflow https://hamel.dev/blog/posts/llm-judge/
- Shankar et al. EvalGen UIST 2024 — criteria-drift, open-coding pattern https://arxiv.org/abs/2404.12272
- ADR-0001 — failure-mode-first scoping
- Master Spec §3 — failure-mode-first pivot
- Master Spec §11 — Kill-Gate 1 definition
