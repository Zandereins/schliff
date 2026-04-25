# Schliff — The Measurement Layer for AI Software (v8+ Strategic Vision)

> **Status:** Draft — pending review (architecture / security / market-validation agents)
> **Date:** 2026-04-25
> **Supersedes:** Vision-section of `docs/specs/plans/2026-03-28-v8-master-plan.md` and `docs/specs/plans/2026-03-29-v8-final-plan.md` (those remain authoritative for Säule 1 implementation; this document positions them inside a broader 5-Säulen strategy)
> **Author:** Franz Paul + Claude (paired)
> **Decision-record:** Section 12. **Open questions:** Section 13.

---

## 1. Status & Metadata

| Field | Value |
|---|---|
| Spec ID | `2026-04-25-measurement-layer-vision` |
| Status | Draft, not yet reviewed |
| Owner | @Zandereins |
| Reviewers required | Architecture, Security, Market-validation, Simplify (one agent each, output captured below in §14) |
| Effective date | After 4 reviewer-agents return GREEN-with-conditions or BLOCKER-resolution |
| Review cadence | Quarterly, or when a Säule's roadmap shifts by > 1 quarter |
| Live state when written | Schliff v7.2.0 on PyPI, 1117 tests, 2 GitHub stars, 0 forks, 0 external PRs since launch |

---

## 2. Executive summary

Schliff today is a deterministic quality scorer for AI instruction files (SKILL.md, CLAUDE.md, .cursorrules, AGENTS.md). v7.2.0 hardened the existing surface; v8 (per `2026-03-29-v8-final-plan.md`) expands scoring to system-prompts, ships a registry, and adds an evolution engine. Both directions stay inside the "scoring" frame.

This document re-frames the project. **Schliff is positioning itself as the deterministic measurement layer for AI software.** Same intuition as Datadog for cloud workloads or Prometheus for distributed systems: not the thing being measured, the thing every responsible operator has instrumented to know whether their system is healthy.

Five Säulen carry the vision. The current v8 plan becomes Säule 1 + part of Säule 4. Säulen 2, 3, 5 are net-new and outlined below with acceptance criteria, not yet with implementation plans (those follow as separate spec docs).

The driving constraint behind every choice in this document: **no defects in production, no rushed shipping, no hand-waved security**. Every Säule is built spec-first with a senior-engineer gate workflow (§10).

---

## 3. Problem statement

AI software has three measurable layers, and none are systematically instrumented today:

| Layer | What it is | Who measures it today |
|---|---|---|
| **Source** | The artifacts a human authors that direct an agent: SKILL.md, CLAUDE.md, system prompts, .cursorrules | Almost no one. Schliff is alone here. |
| **Output** | What the agent actually produces in response to inputs: text, tool calls, code | Promptfoo (12k★), DeepEval (10k★), Inspect (Anthropic), Braintrust (commercial) — all use LLM-as-judge first |
| **System** | How agents behave together over a trace: emergent loops, prompt-injection cascades, off-topic drift, tool misuse | LangSmith/LangFuse store traces but do not analyze them deterministically; no one ships pattern-detection as a library |

Each existing tool addresses one layer with one ideology (LLM-as-judge). The result: **non-deterministic, expensive, slow, hard to gate in CI**. Two consequences:

- Teams know their agents misbehave but cannot prove it consistently
- Compliance/security teams have no static-analysis equivalent for AI

Schliff's deterministic-first ideology, validated on 7-dimension source scoring, generalises to all three layers if extended carefully. That is the bet of this document.

---

## 4. Vision: The Measurement Layer for AI Software

> **Schliff measures every layer of AI software deterministically first, with LLM-judges only as a fallback when rules cannot decide. It runs as a library under existing eval frameworks, not as their competitor.**

Operating principles that follow from the vision:

1. **Deterministic-first.** Same input → same output, every machine, every run. LLM-judges are an explicitly opt-in fallback when no deterministic rule applies. This is the wedge that no competitor matches.
2. **Library-first, CLI-second.** v7's CLI-only surface limited adoption. v8 onwards: `from schliff import score, evaluate, observe` is the canonical surface; the CLI becomes a thin wrapper.
3. **Composable, not closed.** Schliff sits *under* Promptfoo/DeepEval/LangSmith (as a quality gate), not next to them. Adapters import their formats, run deterministic checks first, hand back to them.
4. **Anti-gaming as a first-class property.** Every metric Schliff emits is checked against inflate-the-number patterns (keyword stuffing, padding, repetition). A defensible CI gate is one developers cannot trivially trick.
5. **Free at the core, paid at the perimeter (eventually).** MIT-licensed core. Commercial offerings (managed leaderboard, enterprise compliance reports, hosted observability) are perimeter, not core.
6. **Spec-first, ship-late.** Each Säule lands behind a written spec with reviewer-agent gates. Better to ship Säule 1 cleanly than to ship 5 Säulen half-finished.

---

## 5. Strategic positioning vs. the field

| Tool | Layer covered | Approach | Would it use Schliff? |
|---|---|---|---|
| **Promptfoo** | Output | LLM-judge YAML suites | Yes, as deterministic-rule pre-pass: cuts cost ~50% on suites where structural assertions catch the failure |
| **DeepEval** | Output | pytest-style LLM testing | Yes, as fixture providing deterministic checks before LLM-judge |
| **Inspect** (Anthropic) | Output (research) | Eval scaffolding for safety research | Yes, as deterministic baseline for reproducibility |
| **Braintrust** (commercial) | Output | SaaS, eval logging + LLM-judge | No (commercial, vendor lock-in); Schliff competes for OSS share here |
| **LangSmith / LangFuse** | System (traces) | Trace collection + UI + custom evaluators | Yes, as trace-pattern-analyzer library plugged into their evaluator API |
| **agnix / agent-sh** | Orchestration build-time | Multi-agent harness | Indirect — agnix builds agents, Schliff observes their traces |
| **awesome-claude-code** | Discovery | Curated list | Yes — Schliff is *listed*, not competing |
| **Anthropic Skills SDK (hypothetical)** | Source | Reference impl for skill format | If Anthropic ships this, Schliff's source-scoring stays the *reference quality bar* (60%+ probability per v8-vision risk register) |

**Key insight:** every cell that says "Yes" represents a distribution channel where Schliff gets pulled into other tools' tech stacks. That is how a measurement-layer wins — not by displacing players, by being plumbed into them.

---

## 6. The five Säulen

Each Säule has: scope, acceptance criteria, dependencies, ship target.

### Säule 1 — Library API + Source-Quality Foundation

**Status today.** Spec exists (`2026-03-29-v8-final-plan.md`), implementation 0%. v7.2.0 ships the CLI; the library API does not exist as a public surface yet.

**Scope.**
- Public `from schliff import score, evaluate, observe` API with stable type-annotated signatures
- Single-choke-point security: `allowed_root: Path` parameter on every public entry that touches a filesystem path
- Pure-function scorers (no hidden home-dir state in `compute_composite`)
- Clean package layout (`scripts/` dispatched into `schliff/` module tree per ARCH-004)
- Multi-format support extended to system-prompts (zero existing competition per v8-vision)

**Acceptance criteria.**
- A consumer can `pip install schliff` and run `from schliff import score; score(Path("CLAUDE.md"), allowed_root=Path.cwd())` without touching the CLI
- Path-traversal threat tests pass for every public entry
- All existing CLI behaviours backed by the new library API (no parallel implementations)
- Test count maintains the 1117 baseline + adds threat tests for `allowed_root`
- Documentation: one-page library-quickstart + ADR explaining the security-by-default decision

**Dependencies.** None blocking. v7.2.1 hotpatch (queued, ~4h) should land first because Säule 1 will inherit any defects in `EXCLUDED_DIRS`/`urllib`-lazy-import/error-message clarity that the hotpatch fixes.

**Ship target.** End of Q2 2026 (June). Estimate is the existing v8 final plan's "4-5 weeks" applied honestly: 6-10 weeks for one full-time-equivalent.

### Säule 2 — Eval-Adapter Layer (output-quality wedge)

**Status today.** Net-new. No code, no spec.

**Scope.**
- `schliff.eval.run(suite, output)` accepts a normalized eval suite and returns `EvalResult` with deterministic-rule verdicts
- Built-in adapters: Promptfoo-yaml-import, DeepEval-pytest-fixture, OpenAI-evals-jsonl
- Deterministic-first decision tree:
  1. Does the assertion type have a deterministic rule? (`contains`, `regex`, `json_schema`, `format`, `length`, `equals`) → run it. **No LLM call.**
  2. Otherwise → fall through to LLM-judge (optional, requires `schliff[evolve]`)
- Cost report per suite: how many assertions skipped LLM via deterministic shortcut

**Acceptance criteria.**
- Promptfoo-yaml suite import: `schliff.eval.run(suite="promptfoo.yaml", output=...)` produces results identical to Promptfoo's own runner for 95%+ of suite types
- Deterministic-shortcut metric: at least 40% of real-world public Promptfoo suites should hit at least one deterministic check (pre-launch corpus study required)
- Zero LLM calls when a suite uses only `contains`/`regex`/`json_schema`/`format`/`length`/`equals`
- Adversarial test: at least 5 known-bad eval suites (over-permissive matchers, malformed JSON-schema, ReDoS regex) handled gracefully without crash

**Dependencies.** Säule 1 (library API must exist).

**Ship target.** Q3 2026 (Jul-Sep). The wedge: a Promptfoo user adds 1 line and sees their suite cost drop ~50%. That moment is the marketing artefact.

### Säule 3 — System-Observability (Multi-Agent Quality)

**Status today.** Net-new. No code, no spec. Hardest of the five.

**Scope.**
- `schliff.observe(trace)` accepts a normalized trace format and returns `TraceReport` with detected patterns
- Initial pattern library (5–7 detectors, all deterministic):
  - Prompt-injection cascade: agent-A output containing instructions appears unsanitized in agent-B prompt
  - Infinite loop: same tool call > N times with bounded-distance arguments
  - Off-topic drift: cosine distance of tool-call topic vs. initial user request > threshold (deterministic embedding model OR token-overlap proxy if no embedding available)
  - Tool misuse: tool called with arguments that fail its declared schema
  - Context pollution: prompt size growing super-linearly across turns
- Adapters: LangSmith JSON, OpenAI tool-call format, Anthropic tool-use format, generic OpenTelemetry-trace
- Output: JUnit-XML / GitHub-Actions annotations / Sentry-event JSON

**Acceptance criteria.**
- Each detector has at least 3 positive-case tests (real traces from public agents, anonymized) and 5 negative-case tests (clean traces that should NOT trigger)
- False-positive rate < 5% on a benchmark corpus of 100 clean public traces
- Embedding-free fallback for off-topic drift (no mandatory `[ml]` extra)
- Library remains zero-network: no telemetry phone-home, no cloud calls

**Dependencies.** Säule 1 (library API) + Säule 2 (adapter pattern matures the import infrastructure)

**Ship target.** Q4 2026 (Oct-Dec). MVP with 3 detectors; expand quarterly thereafter.

### Säule 4 — Standard-Setting (distribution / network effect)

**Status today.** Partially started. v7-launch attempted (see `project_schliff_state.md` — posts never went out). Awesome-list submissions tried, none accepted yet. Public playground exists.

**Scope.**
- Public benchmark site (`leaderboard.schliff.dev`): top 100 public skills/CLAUDE.mds by Schliff-score, updated nightly
- VS Code extension with live Schliff-score in the gutter
- Pre-commit hook + GitHub Action mature, badge-able, documented in 5+ public repo READMEs
- Outreach (deliberate, paced): Anthropic skills team, Promptfoo maintainers, LangSmith team, agnix/agent-sh team, claude-flow author
- One technical talk per quarter at Python/AI/devtools meetup or conference
- Citation hygiene: every blog post about AI quality cites Schliff's methodology; we make this easy by maintaining a `docs/methodology/` page that is link-stable

**Acceptance criteria.**
- 10+ external repos using `schliff verify` in CI by end of 2026
- Mentioned in at least 2 third-party blog posts / talks
- Featured in at least 1 awesome-list (without nudging — see `reference_awesome_claude_code.md` policy)
- 100+ GitHub stars by end of 2026 (current 2)

**Dependencies.** Säulen 1+2 must ship first; without library API the extension/benchmark do not have stable hooks.

**Ship target.** Continuous. First milestone (VS Code extension MVP + benchmark site beta): end of Q3 2026.

### Säule 5 — Safety / Compliance

**Status today.** Net-new. No code, no spec.

**Scope.**
- Specialised dimensions for regulated use-cases:
  - PII-leakage detector (in skills AND in observed outputs) — extends existing security scorer
  - Jailbreak-resistance scoring: skill resists known jailbreak families on a held-out adversarial set
  - Prompt-injection-resistance scoring: defences declared in the skill (e.g. nonce-wrapped user content) are detected and credited
  - Compliance modes: HIPAA, GDPR, EU-AI-Act readiness checklists wrapped as scorers
- Audit-trail: every score in compliance-mode produces a signed JSON receipt with rule version, input hash, timestamp

**Acceptance criteria.**
- One certified compliance-mode passes a third-party legal review (target: GDPR for v0.1, EU-AI-Act for v1.0)
- PII detector benchmark: 95%+ recall on a synthetic test corpus, < 1% false-positive rate on 1000 random public skills
- Audit-trail receipts cryptographically reproducible from the input + rule version

**Dependencies.** Säulen 1, 2, 3 must be stable. Compliance teams do not adopt MVP-stage tools.

**Ship target.** 2027. This is the "land-and-expand" Säule — once enterprises adopt Schliff for compliance, they fund the rest.

---

## 7. Roadmap (realistic; agent-reviewable)

| Quarter | Säule | Concrete deliverables | Confidence |
|---|---|---|---|
| Q2 2026 (now → end of June) | Säule 1 + v7.2.1 hotpatch | Library API public, Phase-0 security (`allowed_root`), system-prompt scoring shipped, hotpatch (Q1–Q5 + IMP-006/007) shipped | HIGH (existing v8 plan + hotpatch list are concrete) |
| Q3 2026 (Jul-Sep) | Säule 2 begins, Säule 4 first move | Promptfoo-yaml adapter + cost-report MVP; VS Code extension MVP; outreach to Promptfoo maintainers begins | MEDIUM (depends on Säule 1 being clean) |
| Q4 2026 (Oct-Dec) | Säule 3 MVP, Säule 4 ongoing | Three trace-pattern detectors, LangSmith adapter, benchmark site beta-public | MEDIUM-LOW (Säule 3 is novel territory; corpus needed for false-positive baselining) |
| 2027 | Säulen 2/3 polish + Säule 5 | DeepEval adapter, full pattern library, GDPR-compliance-mode v0.1 | LOW (too far out for honest estimation) |

The roadmap intentionally **does not promise** Säulen 2, 3, 5 within 2026 in mature form. A senior engineer ships one Säule cleanly per quarter rather than five Säulen unfinished per year.

---

## 8. Anti-vision: what Schliff explicitly will NOT be

| Will not be | Why |
|---|---|
| A multi-agent orchestrator | Different value add; Schliff observes orchestrators, does not replace them |
| A skill marketplace / registry-of-record | awesome-claude-code, Anthropic Skills SDK fill this; Schliff supplies the quality bar |
| A hosted SaaS in the core | Stays MIT, stays runnable offline; commercial perimeter optional |
| Bundled with a specific LLM provider | LiteLLM keeps it provider-agnostic; never default-import a single SDK |
| A research paper generator | We ship engineering artefacts, not academic ones (though methodology pages welcome citations) |
| A general code linter | Linter for instruction files, not for Python/JS/etc. |

Each entry in this list closes a door deliberately. A future PR that drifts into one of these is a scope-creep red flag; reviewer-agents must reject.

---

## 9. Architectural principles (binding)

1. **`allowed_root` everywhere a path enters.** The single-choke-point security pattern must be in every public entry, every adapter, every observer. No exceptions.
2. **Pure-function scorers.** No hidden home-dir reads, no global mutation, no cache writes that surprise the caller. State lives in the caller.
3. **Adapters import; they do not subclass.** Promptfoo/DeepEval/LangSmith adapters convert formats to Schliff's internal model; Schliff does not inherit from their classes. This avoids cross-version brittleness when those projects refactor.
4. **Determinism is a property, not a hope.** Every scorer/detector ships a property test: `f(x) == f(x)` for 1000 random inputs across 3 Python versions.
5. **Anti-gaming is automatic.** New dimensions ship with at least one "this score must not be inflate-able by pattern X" test.
6. **No silent fallback to LLM.** Calling code must opt in (`evaluate(..., judge="llm")`); the library never decides for the user.
7. **Trace storage is the caller's problem.** `observe(trace)` operates on a trace already in memory. We do not ship a trace store. Reduces blast radius.
8. **Errors at boundaries; trust internally.** Validate at public entry; do not re-validate the same dict in three internal helpers. (Anti-pattern from the recent UR-002 cluster: each scorer was independently re-validating; pulled into one entry guard now.)

---

## 10. Engineering workflow (binding for every Säule)

This is the "senior engineer" gate. It applies to every spec and every code change above ~50 LOC.

```
Research → Spec → Plan → TDD → Code → Self-Review → Cross-Review (agents) → Test → Audit → QA → Verify → Ship
```

Concrete gates per phase:

| Gate | What it requires | Who signs off |
|---|---|---|
| **Research** | At least one source-grounded document in `docs/research/` covering competitive landscape, prior-art, technical risks. Cite file:line in own repo, URL for external | Author + 1 research-agent |
| **Spec** | Document in `docs/specs/` with: status frontmatter, acceptance criteria, dependencies, ship target, open questions, ADR-style decisions | Author + 1 spec-quality agent + Franz approval |
| **Plan** | TaskCreate-tracked breakdown into < 1-day chunks with dependencies. Each chunk has its own test plan | Author + reviewer (human or agent) |
| **TDD** | Failing test exists and is committed before any production code. Reverse-TDD verification on every non-trivial test | Mandatory; verification-before-completion skill enforces |
| **Code** | Atomic commits, conventional-commit messages, no scope creep beyond plan | Author |
| **Self-Review** | Author reads own diff before opening PR. Apply `simplify` skill | Author |
| **Cross-Review** | 3 parallel reviewer agents (code-quality, security, QA) with explicit hallucination-exclusion protocol (every finding cites file:line, every claim verified empirically or marked SPECULATION) | All three return GREEN-or-non-blocker before merge |
| **Test** | Full test suite green on every supported Python version on every supported OS | CI |
| **Audit** | Beyond-diff scan: whole-function review of every changed function, adjacent-bug-class grep, platform-portability matrix, dogfood in own repo | Author + post-merge agent dispatch |
| **QA** | Empirical dogfood of new feature; reverse-TDD spot-check on 25%+ of new tests | Author |
| **Verify** | `verification-before-completion` checklist signed off (every claim has evidence, no hand-waved "should work") | Author |
| **Ship** | PR merged via `--merge` (preserve history) or `--squash` (for trivial deps); tag if release; CHANGELOG updated; memory + handoff updated | Author |

This workflow is heavy. Honestly heavy. But it is what produced v7.2.0 with zero defects on first ship, and it is what scales without rework.

**Two carve-outs:**
- One-line bugfixes do not need a spec (commit message + reverse-TDD test is enough)
- Doc-only PRs skip the cross-review agents

Anything in between honors the full gate.

---

## 11. Risk register

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Anthropic ships a competing skill-quality-SDK | 60% (per v8-vision register) | High | Set the standard first; remain MIT and adapter-friendly so even if Anthropic ships, Schliff stays the reference impl that LangSmith/Promptfoo plug into |
| R2 | One Säule absorbs all engineering capacity, others stall | 80% with one engineer | High | Ship Säulen sequentially, not in parallel. Roadmap §7 honors this. |
| R3 | Determinism becomes a marketing slogan, not a property | 40% | Critical | Property tests on every scorer + every detector. Reviewer-agents reject any new code without one. |
| R4 | Adapter-target frameworks (Promptfoo, DeepEval) refactor incompatibly | 50% per year per framework | Medium | Versioned adapters (`schliff.adapter.promptfoo_v0_X`) + integration tests pinning to specific framework versions |
| R5 | LLM-as-judge fallback in Säule 2 erodes deterministic-first claim | 70% if not policed | High | Hard policy: LLM-judge requires explicit caller opt-in, can never be the default |
| R6 | Solo-engineer burnout; project stalls mid-Säule | 50% over 24 months | Existential | Ship small increments; close-down ritual after each Säule (CHANGELOG + retrospective + memory update); permit "pause" without "abandon" |
| R7 | Security flaw in `observe()` allows trace-injection cascade | Unknown | Critical | Säule 3 must commission a paid third-party pentest before ship; no exception |
| R8 | Compliance Säule promises certifications Schliff cannot deliver | High if marketed early | Critical | No public mention of Säule 5 capabilities until at least one independent legal review passes |
| R9 | Adoption stays at 2 stars indefinitely despite shipping | 30% | Medium | Roadmap §7 has a Säule 4 milestone (10+ external CI integrations by end of 2026); if missed, treat as signal to revisit positioning |
| R10 | Spec-driven workflow slows shipping below psychological tolerance | 50% | Medium | Carve-outs in §10 for trivial changes; reviewer-agents run in parallel (minutes) not serial (days) |

The register is updated at every reviewer-agent pass. New entries require an owner.

---

## 12. Decision-records (ADR-lite)

Each entry: decision, alternatives considered, why-this-one, what-would-flip-it.

**ADR-001 — Position Schliff as a measurement layer, not a competitor.**
- Alternatives: (a) compete head-on with Promptfoo for output-eval, (b) merge into agnix as a quality module, (c) become a hosted SaaS
- Chosen: (d) measurement layer used by all of the above
- Why: avoids 3 unwinnable head-on fights; Datadog precedent shows the category is a viable scaling path; matches existing deterministic-first ideology
- Flip if: Anthropic ships a free official skill-quality SDK with the same API, eliminating the wedge. Then re-position as their preferred engine, or shut down core.

**ADR-002 — Library-first, CLI-second.**
- Alternatives: (a) keep CLI as primary; (b) ship CLI + library at parity; (c) deprecate CLI
- Chosen: (b) parity, but library is the canonical surface for new features
- Why: adapters and IDE extensions need the library; CLI users are not abandoned but no longer drive design
- Flip if: a usability study shows users dramatically prefer CLI for >80% of flows (unlikely)

**ADR-003 — Deterministic-first decision tree, LLM-judge as opt-in fallback.**
- Alternatives: (a) LLM-judge always; (b) deterministic-only, no LLM ever; (c) library decides automatically based on assertion type
- Chosen: (d) deterministic when applicable, LLM only on explicit `judge="llm"` arg
- Why: keeps cost predictable for CI users; protects deterministic-first marketing claim; users who want LLM can always opt in
- Flip if: deterministic checks turn out to apply to <10% of real eval suites (Säule 2 corpus study will tell us)

**ADR-004 — Single `allowed_root` parameter on every path-touching public entry.**
- Alternatives: (a) one global `allowed_root` set per process; (b) per-call argument; (c) no enforcement, document the threat
- Chosen: (b) per-call argument, mandatory in library, default `None` in CLI for backward compat
- Why: per-call is composable; library users (Promptfoo etc.) need fine-grained control; backward-compat keeps CLI users
- Flip if: no library users emerge, suggesting the security argument is theoretical for current adoption

**ADR-005 — No core dependency on a specific LLM SDK.**
- Alternatives: (a) bundle litellm; (b) bundle Anthropic SDK; (c) abstract everything via litellm but as optional dep
- Chosen: (c) — `schliff[evolve]` extras include litellm; core stays zero-dep
- Why: matches current shipping pattern; protects core install footprint; avoids supply-chain blast on unrelated installs
- Flip if: zero users adopt the optional dep (signal: nobody actually wants the LLM features)

**ADR-006 — Reviewer-agent gates use hallucination-exclusion protocol mandatorily.**
- Alternatives: (a) trust agent verdicts; (b) require human re-verification of every finding; (c) require every finding cite file:line + empirical reproduction
- Chosen: (c) — see protocol in PR #32 review process
- Why: agents over-claim in extended runs; the protocol caught false-positives in the v7.2.0 review (e.g. SSRF claim was wrong because allowlist was overlooked)
- Flip if: the protocol's overhead exceeds its benefit (track via post-mortems)

---

## 13. Open questions (block ship-readiness)

These must be answered before any Säule begins implementation. Each has a recommended-resolution strategy.

| # | Question | Recommended resolution |
|---|---|---|
| OQ1 | Are the existing 28 v8-final-plan commits + 5 v8-design.md docs still authoritative for Säule 1, or do they need refactor? | Keep existing v8 plan as Säule 1's implementation document; this strategy doc only re-positions. |
| OQ2 | Should v7.2.1 hotpatch ship before Säule 1 begins? | Yes, ~4h gain in user experience; do not let it block beyond next focused session. |
| OQ3 | What is the corpus for Säule 2's "40% deterministic-shortcut hit rate" claim? | Commission a research-agent to scan top-100 public Promptfoo suites; result decides whether the marketing claim survives. |
| OQ4 | Is `agnix`/`agent-sh` outreach a Q3 2026 task or earlier (now that v7.2.0 is out)? | Earlier — open distribution conversation while Säule 1 builds; cost is one email. |
| OQ5 | Should the leaderboard site (`leaderboard.schliff.dev`) be deferred to Q4, or is it useful for Säule 4 sooner? | Defer; it is a multiplier of trust, not a generator of trust. Build trust via 10+ external CI integrations first. |
| OQ6 | Who reviews Säule 5 compliance claims (legal review)? | TBD. Track as risk R8. Do not market Säule 5 publicly until resolved. |
| OQ7 | Does the existing test infrastructure (1117 tests) need restructure to host Säulen 2, 3 cleanly, or can it grow incrementally? | Spec for Säule 2 must answer this in research phase. Default assumption: incremental works. |
| OQ8 | What is the burn rate beyond Säule 1? Is solo-engineer + AI-pair sustainable through Säulen 2-3? | Self-assess after Säule 1 ships. Honest signal: how many weekend sessions are burnout vs. flow. |

---

## 14. Reviewer-agent verdicts (placeholder; populated after spec is reviewed)

Section to be filled after the spec is dispatched to four agents:
- **Architecture-reviewer:** does the 5-Säulen split survive collision with the existing codebase?
- **Security-reviewer:** any Säule that introduces a novel attack surface not addressed in §11?
- **Market-validation-reviewer:** are the competitor claims in §5 accurate as of 2026-04-25?
- **Simplify-reviewer:** can any Säule be cut without losing the vision's coherence?

Each verdict format:
```
## Verdict — <agent>

GREEN | GREEN-WITH-CONDITIONS | BLOCKER

Findings:
- [VERIFIED|SPECULATION] <description> — <file:line or URL evidence>

Conditions (if conditional GREEN):
- ...

Blockers (if BLOCKER):
- ...
```

The spec is not effective until all four return GREEN or GREEN-WITH-CONDITIONS with conditions resolved.

---

## 15. Cross-references

- v8 implementation detail (Säule 1 superset): `docs/specs/plans/2026-03-29-v8-final-plan.md`
- v8 architectural design: `docs/specs/2026-03-28-v8-design.md`
- System prompt scoring spec (Säule 1 sub-component): `docs/specs/system-prompt-scoring-spec.md`
- Registry platform (Säule 4 sub-component): `docs/specs/schliff-registry-platform.md`
- v7.2.1 hotpatch queue (must precede Säule 1): see `project_schliff_state.md` in memory + `Schliff Plan 2026-04-24 — Ultrareview + Optimizations.md`
- Release procedure (binds every Säule's ship gate): `RELEASING.md`
- This document supersedes the *vision* sections of the v8 plans; it does not supersede their *implementation* content.

---

## 16. Versioning of this document

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-04-25 | Claude (drafted on Franz's brief) | Initial draft, awaiting reviewer-agent passes |

Future revisions should bump version, log the change, and re-trigger the four-agent review.
