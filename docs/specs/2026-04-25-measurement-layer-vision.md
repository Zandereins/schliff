# Schliff — The Measurement Layer for AI Software (v8+ Strategic Vision)

> **Status:** v0.2 — reviewer-agent passes complete (architecture / security / market-validation / simplify all GREEN-WITH-CONDITIONS, conditions integrated below)
> **Date:** 2026-04-25
> **Supersedes:** Vision-section of `docs/specs/plans/2026-03-28-v8-master-plan.md` and `docs/specs/plans/2026-03-29-v8-final-plan.md` (those remain authoritative for Säule 1 implementation; this document positions them inside a broader 5-Säulen strategy)
> **Author:** Franz Paul + Claude (paired)
> **Decision-record:** Section 12. **Open questions:** Section 13. **Review verdicts:** Section 14.

---

## 1. Status & Metadata

| Field | Value |
|---|---|
| Spec ID | `2026-04-25-measurement-layer-vision` |
| Status | v0.3 — Round-2 reviewer conditions integrated (4 fresh agents: spec-quality / red-team / simplify-2 / cross-coherence), ready for merge |
| Owner | @Zandereins |
| Reviewers complete | Architecture (GREEN-WITH-CONDITIONS, 4), Security (GREEN-WITH-CONDITIONS, 6), Market-validation (GREEN-WITH-CONDITIONS, 3+), Simplify (GREEN-WITH-CONDITIONS, structural) — see §14 for verdict summaries |
| Effective date | After human merge approval. Re-trigger agent review on any v0.3+ revision. |
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
| **Source** | The artifacts a human authors that direct an agent: SKILL.md, CLAUDE.md, system prompts, .cursorrules | Almost no one measures these deterministically. General-purpose linters (ESLint, Pylint, Cursor's built-ins) cover code; instruction-file-specific deterministic scoring is Schliff's wedge. |
| **Output** | What the agent actually produces in response to inputs: text, tool calls, code | Promptfoo (20.5k★), DeepEval (15k★), Inspect (Anthropic), Braintrust (commercial). All ship deterministic-assertion paths but their flagship UX and marketing centres on LLM-as-judge. |
| **System** | How agents behave together over a trace: emergent loops, prompt-injection cascades, off-topic drift, tool misuse | LangSmith / LangFuse (25k★) store traces but do not analyze them deterministically; no one ships pattern-detection as a library |

**Important nuance** (per market-validation review): Promptfoo, DeepEval and others document "deterministic first, LLM as fallback" as the recommended pattern, but their tooling defaults and onboarding paths still pull users toward LLM-judges. Schliff's wedge is therefore not "we invented deterministic-first" — it is "we ship the canonical library-first deterministic implementation that the existing eval frameworks recommend in theory but do not provide in their default flow."

Each existing tool addresses one layer with one ideology (LLM-as-judge dominates the actual usage even where docs recommend otherwise). The result: **non-deterministic, expensive, slow, hard to gate in CI**. Two consequences:

- Teams know their agents misbehave but cannot prove it consistently
- Compliance/security teams have no static-analysis equivalent for AI

Schliff's deterministic-first ideology, validated on 7-dimension source scoring, generalises to all three layers if extended carefully. That is the bet of this document.

---

## 4. Vision: The Measurement Layer for AI Software

> **Schliff measures every layer of AI software deterministically first, with LLM-judges only as a fallback when rules cannot decide. It runs as a library under existing eval frameworks, not as their competitor.**

Operating principles that follow from the vision:

1. **Deterministic-first.** Same input → same output, every machine, every run. LLM-judges are an explicitly opt-in fallback when no deterministic rule applies. This is the first library-first deterministic implementation of a pattern competitors recommend in docs but do not default to in tooling; whether it becomes *canonical* depends on adoption, not naming.
2. **Library-first, CLI-second.** v7's CLI-only surface limited adoption. v8 onwards: `from schliff import score, evaluate, observe` is the canonical surface; the CLI becomes a thin wrapper.
3. **Composable, not closed.** Schliff sits *under* Promptfoo / DeepEval / LangSmith / LangFuse (as a quality gate), not next to them. Adapters import their formats, run deterministic checks first, hand back to them.
4. **Anti-gaming as a first-class property.** Every metric Schliff emits is checked against inflate-the-number patterns (keyword stuffing, padding, repetition). A defensible CI gate is one developers cannot trivially trick.
5. **Free at the core, paid at the perimeter (eventually).** MIT-licensed core. Commercial offerings (managed leaderboard, enterprise compliance reports, hosted observability) are perimeter, not core.
6. **Spec-first, ship-late.** Each Säule lands behind a written spec with reviewer-agent gates. Better to ship Säule 1 cleanly than to ship 5 Säulen half-finished.

---

## 5. Strategic positioning vs. the field

Star counts as of 2026-04-25 (verified by market-validation reviewer):

| Tool | Stars | Layer covered | Approach | Would it use Schliff? |
|---|---|---|---|---|
| **Promptfoo** | 20.5k★ | Output | LLM-judge YAML suites; deterministic assertions documented but not the default flow | Yes — as deterministic-rule pre-pass: cuts cost on suites where structural assertions catch the failure |
| **DeepEval** | 15k★ | Output | pytest-style LLM testing; DAG metric for deterministic decision trees, but LLM-metrics are flagship | Yes — as fixture providing deterministic checks before LLM-judge |
| **LangFuse** | 25k★ | System (traces) | Trace store + UI + custom evaluators | Yes — as trace-pattern-analyzer library plugged into their evaluator API |
| **LangSmith** | (LangChain commercial) | System (traces) | Trace collection + UI + custom evaluators | Yes — same pattern as LangFuse |
| **Inspect** (Anthropic) | ~1-2k★ | Output (research) | Eval scaffolding for safety research | Yes — as deterministic baseline for reproducibility |
| **Braintrust** (commercial) | n/a | Output | SaaS, eval logging + LLM-judge | No (commercial, vendor lock-in); Schliff competes for OSS share here |
| **agnix / agent-sh** | 208★ | Orchestration build-time | Multi-agent harness | Indirect — agnix builds agents, Schliff observes their traces |
| **awesome-claude-code** | 40.9k★ | Discovery | Curated list | Yes — Schliff is *listed*, not competing |
| **Anthropic Skills SDK** (announced 2025-12, see §11 R1) | n/a | Source | Reference impl + creator plugin (Mar 2026) | Schliff stays the *reference quality bar* if Anthropic ships a quality-scorer; Schliff becomes Anthropic-SDK-adapter if not |

**Key insight:** every cell marked "Yes" is a *potential* distribution channel where Schliff could get pulled into other tools' tech stacks — actualization depends on the target project's competitive incentives and the friction of integration. That is how a measurement-layer wins — not by displacing players, by being plumbed into them when the integration cost is lower than the in-house build cost. The "deterministic-first" wedge is reinforced (not weakened) by market-validation: every competitor's docs already recommend this pattern. Schliff is the library that finally ships it as a first-class default.

---

## 6. The five Säulen

Each Säule has: scope, acceptance criteria, dependencies. Ship targets are tracked centrally in §7 (do not duplicate per Säule — single source of truth).

### Säule 1 — Library API + Source-Quality Foundation

**Status today.** Spec exists (`2026-03-29-v8-final-plan.md`), implementation 0%. v7.2.0 ships the CLI; the library API does not exist as a public surface yet.

**Scope.**
- Public `from schliff import score, evaluate, observe` API with stable type-annotated signatures
- Single-choke-point security: `allowed_root: Path` parameter on every public entry that touches a filesystem path. **Action item from architecture review:** the existing v8-final-plan does not explicitly scope this refactor; cross-reference must be added to v8-final-plan Phase 1a security requirements (path-traversal threat tests, `allowed_root` parameter on `build_scores()` and every public scorer entry, `os.path.realpath()` prefix-match on all file I/O).
- Pure-function scorers (no hidden home-dir state introduced by Säule 1). **Existing-state caveat (architecture review):** `composite.py:_load_calibrated_weights()` already reads `~/.schliff/meta/calibrated-weights.json` silently. This is a feature (auto-calibrated weights) not a bug, but Säule 1 must document it explicitly: every public entry that may consult calibrated weights documents it in its docstring; `compute_composite(..., use_calibrated_weights=False)` opt-out exists; tests cover both cold-cache and warm-cache paths.
- Clean package layout (`scripts/` dispatched into `schliff/` module tree per ARCH-004)
- Multi-format support extended to system-prompts (zero existing competition per v8-vision)

**Acceptance criteria.**
- A consumer can `pip install schliff` and run `from schliff import score; score(Path("CLAUDE.md"), allowed_root=Path.cwd())` without touching the CLI
- Path-traversal threat tests pass for every public entry
- All existing CLI behaviours backed by the new library API (no parallel implementations)
- Test count maintains the 1117 baseline + adds threat tests for `allowed_root`
- Calibrated-weights behaviour explicit: docstring + `use_calibrated_weights` flag + thread-safety documented (current cache is process-local, not thread-safe — acceptable for CLI but documented as limitation for library users)
- Documentation: one-page library-quickstart + ADR explaining the security-by-default decision

**Dependencies.** None blocking. v7.2.1 hotpatch (queued, ~4h) should land first because Säule 1 will inherit any defects in `EXCLUDED_DIRS`/`urllib`-lazy-import/error-message clarity that the hotpatch fixes.

### Säule 2 — Eval-Adapter Layer (output-quality wedge)

**Status today.** Net-new. No code, no spec.

**Scope.**
- `schliff.eval.run(suite, output)` accepts a normalized eval suite and returns `EvalResult` with deterministic-rule verdicts
- Built-in adapters: Promptfoo-yaml-import, DeepEval-pytest-fixture, OpenAI-evals-jsonl
- Deterministic-first decision tree:
  1. Does the assertion type have a deterministic rule? (`contains`, `regex`, `json_schema`, `format`, `length`, `equals`) → run it. **No LLM call.**
  2. Otherwise → fall through to LLM-judge (optional, requires `schliff[evolve]`)
- Cost report per suite: how many assertions skipped LLM via deterministic shortcut
- **Adapter input-validation hardening (security review condition).** Every adapter validates format-specific inputs at the entry boundary BEFORE handing to internal scorers:
  - Promptfoo-yaml: `yaml.safe_load` only, max nesting depth 10, reject `<<` merge-keys, reject anchors with > 1000 references (billion-laughs guard)
  - OpenAI-evals-jsonl: whitelist assertion types (`contains`/`regex`/`json_schema`/`format`/`length`/`equals`), unknown types rejected with clear error, NEVER silent-fallback to LLM
  - DeepEval-pytest: AST-check imports for arbitrary `exec`/`eval`/`__import__` calls in fixture defaults BEFORE pytest discovery; reject suspicious files

**Acceptance criteria.**
- Promptfoo-yaml suite import: `schliff.eval.run(suite="promptfoo.yaml", output=...)` produces results identical to Promptfoo's own runner for 95%+ of suite types
- Deterministic-shortcut metric: at least 40% of real-world public Promptfoo suites should hit at least one deterministic check (pre-launch corpus study required — see §13 OQ3)
- Zero LLM calls when a suite uses only `contains`/`regex`/`json_schema`/`format`/`length`/`equals`
- Adversarial test: at least 5 known-bad eval suites (over-permissive matchers, malformed JSON-schema, ReDoS regex, YAML with circular anchors, JSON with unknown assertion type, pytest fixtures with `exec()` calls) handled gracefully without crash, all rejected with explicit error

**Dependencies.** Säule 1 (library API must exist).

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
- **Output sanitization (security review condition).** Trace-derived output payloads (the JUnit/GitHub/Sentry emissions) must NOT re-leak unsanitized user content. Specifically: every adapter declares which trace fields contain user-controlled content (LangSmith `messages`, OpenAI `function outputs`, Anthropic `thinking` blocks); `observe()` strips or hashes these in the emitted payload by default; opt-in `include_raw=True` for users who explicitly want raw content (and accept the third-party-leakage risk).

**Acceptance criteria.**
- Each detector has at least 3 positive-case tests (real traces from public agents, anonymized) and 5 negative-case tests (clean traces that should NOT trigger)
- False-positive rate < 5% on a benchmark corpus of 1000+ clean public traces (security review expanded baseline from 100)
- Embedding-free fallback for off-topic drift (no mandatory `[ml]` extra)
- Library remains zero-network: no telemetry phone-home, no cloud calls
- PII-flagging: known-pattern PII (emails, phone numbers, SSN-like) in emitted reports is at minimum **flagged** in the report payload header so users notice before forwarding to third-party sinks; full PII-stripping opt-in via `pii_strip=True`

**Dependencies.** Säule 1 (library API) + Säule 2 (adapter pattern matures the import infrastructure)

### Säule 4 — Standard-Setting (distribution / network effect)

**Status today.** Partially started. v7-launch attempted (see `project_schliff_state.md` — posts never went out). Awesome-list submissions tried, none accepted yet. Public playground exists.

**Scope.**
- Public benchmark site (`leaderboard.schliff.dev`): top 100 public skills/CLAUDE.mds by Schliff-score, updated nightly. **Anti-vision boundary (architecture review).** This is a *quality-bar leaderboard*, not a registry-of-record: skills are submitted by their owners via `schliff publish`; Schliff hosts the score display but does not curate, gate, or own the canonical list. The badge definition is public + versioned so the community can fork the leaderboard. This wording matters because §8 explicitly disclaims marketplace ambitions.
- VS Code extension with live Schliff-score in the gutter
- Pre-commit hook + GitHub Action mature, badge-able, documented in 5+ public repo READMEs
- Outreach (deliberate, paced): Anthropic skills team, Promptfoo maintainers, LangSmith / LangFuse teams, agnix/agent-sh team, claude-flow author
- One technical talk per quarter at Python/AI/devtools meetup or conference
- Citation hygiene: every blog post about AI quality cites Schliff's methodology; we make this easy by maintaining a `docs/methodology/` page that is link-stable
- **IPC and upload boundary hardening (security review condition).** VS Code extension messages must be valid JSON, size-capped (1MB), and schema-validated; `BadJSON` and oversize messages dropped with clear error. Leaderboard uploads enforce `MAX_SKILL_SIZE`, reject path-traversal in any zip extraction (Zip-Slip guard), timeout extraction at 5s, require GitHub-OAuth or scoped API key (no anonymous submissions to prevent leaderboard-spam).

**Acceptance criteria.**
- 10+ external repos using `schliff verify` in CI by end of 2026
- Mentioned in at least 2 third-party blog posts / talks
- Featured in at least 1 awesome-list (without nudging — see `reference_awesome_claude_code.md` policy)
- 100+ GitHub stars by end of 2026 (current 2)

**Dependencies.** Säulen 1+2 must ship first; without library API the extension/benchmark do not have stable hooks.

### Säule 5 — Safety / Compliance

**Status today.** Net-new. No code, no spec.

**Scope.**
- Specialised dimensions for regulated use-cases:
  - PII-leakage detector (in skills AND in observed outputs) — extends existing security scorer
  - Jailbreak-resistance scoring: skill resists known jailbreak families on a held-out adversarial set
  - Prompt-injection-resistance scoring: defences declared in the skill (e.g. nonce-wrapped user content) are detected and credited
  - Compliance modes: HIPAA, GDPR, EU-AI-Act readiness checklists wrapped as scorers
- Audit-trail: every score in compliance-mode produces a signed JSON receipt with rule version, input hash, timestamp

**Key Management (security review condition — added v0.2).**
Signing keys MUST NOT live in `.schliff/keys/` or any filesystem path that a malicious skill could reach via path-traversal. Required policy:
- Keys live in environment variables (`SCHLIFF_SIGNING_KEY` containing base64-encoded Ed25519 private key) or are injected via hermetic build systems (Bazel, Nix, GitHub-Actions secrets)
- Keys rotated annually; every signing operation verifies key age < 365 days and refuses to sign with stale keys
- CI environments must NOT log key material; key-detection in stack traces / error messages is mandatory
- Audit-trail receipts stored append-only (the directory must reject overwrites of existing files); reads validate file hash against a manifest
- No "convenience" auto-generated keys — refusing to sign without configured key is the default

**Acceptance criteria.**
- One certified compliance-mode passes a third-party legal review (target: GDPR for v0.1, EU-AI-Act for v1.0)
- PII detector benchmark: 95%+ recall on a synthetic test corpus, < 1% false-positive rate on 1000 random public skills
- Audit-trail receipts cryptographically reproducible from the input + rule version
- Key-management policy enforced in code (signing refuses on missing/stale key, append-only receipt directory verified on every read)

**Dependencies.** Säulen 1, 2, 3 must be stable. Compliance teams do not adopt MVP-stage tools.

---

## 7. Roadmap (realistic; agent-reviewable)

| Quarter | Säule | Concrete deliverables | Confidence |
|---|---|---|---|
| Q2 2026 (now → end of June) | Säule 1 + v7.2.1 hotpatch | Library API public, Phase-0 security (`allowed_root`), system-prompt scoring shipped, hotpatch (Q1–Q5 + IMP-006/007) shipped | MEDIUM-HIGH (concrete plans exist, but HIGH applies only after v7.2.1 hotpatch ships and validates the scope estimate against actual velocity) |
| Q3 2026 (Jul-Sep) | Säule 2 begins, Säule 4 first move | Promptfoo-yaml adapter + cost-report MVP; VS Code extension MVP; outreach to Promptfoo maintainers begins; corpus study (OQ3) executed before marketing claims finalize | MEDIUM (depends on Säule 1 being clean) |
| Q4 2026 (Oct-Dec) | Säule 3 MVP, Säule 4 ongoing | Three trace-pattern detectors, LangSmith adapter, benchmark site beta-public; OpenTelemetry-AI alignment evaluated (per R11) | MEDIUM-LOW (Säule 3 is novel territory; corpus needed for false-positive baselining) |
| 2027 | Säulen 2/3 polish + Säule 5 | DeepEval adapter, full pattern library, GDPR-compliance-mode v0.1, third-party legal review of Säule 5 | LOW (too far out for honest estimation) |

The roadmap intentionally **does not promise** Säulen 2, 3, 5 within 2026 in mature form. A senior engineer ships one Säule cleanly per quarter rather than five Säulen unfinished per year. Sequential, not parallel.

---

## 8. Anti-vision: what Schliff explicitly will NOT be

| Will not be | Why |
|---|---|
| A multi-agent orchestrator | Different value add; Schliff observes orchestrators, does not replace them |
| A skill marketplace / registry-of-record | Säule 4 leaderboard is a *quality-bar display* (owner-submitted), not a curated marketplace; awesome-claude-code, Anthropic Skills SDK fill the registry role |
| A hosted SaaS in the core | Stays MIT, stays runnable offline; commercial perimeter optional |
| Bundled with a specific LLM provider | LiteLLM keeps it provider-agnostic; never default-import a single SDK |
| A research paper generator | We ship engineering artefacts, not academic ones (though methodology pages welcome citations) |
| A general code linter | Linter for instruction files, not for Python/JS/etc. |

Each entry in this list closes a door deliberately. A future PR that drifts into one of these is a scope-creep red flag; reviewer-agents must reject.

---

## 9. Architectural principles (binding)

1. **`allowed_root` everywhere a path enters.** The single-choke-point security pattern must be in every public entry, every adapter, every observer. No exceptions.
2. **Pure-function scorers where introduced; document existing exceptions.** New scorers ship as pure functions (no hidden state). Existing exceptions (calibrated-weights cache in `compute_composite`) are documented in their public docstrings and exposed via opt-out flags. Library users get explicit control.
3. **Adapters import; they do not subclass.** Promptfoo/DeepEval/LangSmith adapters convert formats to Schliff's internal model; Schliff does not inherit from their classes. This avoids cross-version brittleness when those projects refactor.
4. **Determinism is a property, not a hope.** Every scorer/detector ships a property test: `f(x) == f(x)` for 1000 random inputs across 3 Python versions.
5. **Anti-gaming is automatic.** New dimensions ship with at least one "this score must not be inflate-able by pattern X" test.
6. **No silent fallback to LLM.** Calling code must opt in (`evaluate(..., judge="llm")`); the library never decides for the user.
7. **Trace storage is the caller's problem — but `observe()` does not make it worse.** `observe(trace)` operates on a trace already in memory. We do not ship a trace store. AND: known-pattern PII fields in trace inputs are flagged in emitted reports (header field `"pii_flagged_fields": [...]`) so callers cannot accidentally forward raw PII to third-party sinks without seeing the warning. Full strip is opt-in.
8. **Adapters validate format-specific inputs at the boundary.** Every adapter's first action on input is a format-specific safety check (YAML depth + anchor-count for Promptfoo, AST-check for DeepEval-pytest, type-whitelist for OpenAI-evals). Garbage rejected with clear error before any internal scorer runs. (Added v0.2 from security review.)
9. **IPC and upload boundaries are validated as strictly as filesystem paths.** VS Code extension IPC: JSON-schema validated, 1MB cap. Leaderboard uploads: `MAX_SKILL_SIZE`, Zip-Slip guard, 5s extraction timeout, OAuth-or-API-key gated. (Added v0.2 from security review.)
10. **Errors at boundaries; trust internally.** Validate at public entry; do not re-validate the same dict in three internal helpers. (Anti-pattern from the recent UR-002 cluster: each scorer was independently re-validating; pulled into one entry guard now.)

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

**Critical assumption (added v0.2 from simplify review).** Reviewer-agents in the Cross-Review gate run in **parallel** (minutes), not serial (days). If agent dispatch becomes serial, the workflow exceeds sustainable cycle time for solo+AI capacity and must be re-evaluated. Track this empirically: average Cross-Review wall-clock per non-trivial PR; if it exceeds 2 hours consistently, a Säule's velocity is threatened.

**Two carve-outs:**
- One-line bugfixes do not need a spec (commit message + reverse-TDD test is enough)
- Doc-only PRs skip the cross-review agents

Anything in between honors the full gate.

---

## 11. Risk register

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Anthropic ships a competing skill-quality-SDK | 60% (per v8-vision register; updated by market-validation: Anthropic shipped Agent Skills standard 2025-12 + Skill-Creator plugin Mar 2026, so trajectory points toward eventually shipping a quality-scorer too) | High | Set the standard first; remain MIT and adapter-friendly so even if Anthropic ships, Schliff stays the reference impl that LangSmith/Promptfoo plug into. Re-evaluate at every quarterly review. |
| R2 | One Säule absorbs all engineering capacity, others stall | 80% with one engineer | High | Ship Säulen sequentially, not in parallel. Roadmap §7 honors this. |
| R3 | Deterministic-first claim erodes (via marketing-slogan-ification OR via LLM-judge fallback becoming the default) | 50% combined | Critical | Property tests on every scorer + every detector mandatory. Hard policy: LLM-judge requires explicit caller opt-in (`judge="llm"`), can never be the default. Reviewer-agents reject any new code violating either rule. (Merged R3+R5 from v0.1 per simplify review — same root cause, redundant entries collapsed.) |
| R4 | Adapter-target frameworks (Promptfoo, DeepEval) refactor incompatibly | 50% per year per framework | Medium | Versioned adapters (`schliff.adapter.promptfoo_v0_X`) + integration tests pinning to specific framework versions |
| R6 | Solo engineer + spec-first workflow burnout / velocity-cliff | 50% over 24 months | Existential | Ship Säulen sequentially; ritualized close-down per Säule (CHANGELOG + retrospective + memory update); permit "pause" without "abandon"; carve-outs in §10 for trivial changes. (Merged R6+R10 from v0.1 per simplify review — same root cause.) |
| R7 | Security flaw in `observe()` allows trace-injection cascade | Unknown | Critical | Säule 3 must commission a paid third-party pentest before ship; no exception |
| R8 | Compliance Säule promises certifications Schliff cannot deliver | High if marketed early | Critical | No public mention of Säule 5 capabilities until at least one independent legal review passes |
| R9 | Adoption stays at 2 stars indefinitely despite shipping | 30% | Medium | Roadmap §7 has a Säule 4 milestone (10+ external CI integrations by end of 2026); if missed, treat as signal to revisit positioning |
| R11 | No industry standard for AI-trace format; Schliff's adapters fragment instead of unify | 40% (ongoing — OpenTelemetry-AI is nascent) | Medium-High | Track OpenTelemetry-AI standardization; align Säule 3 trace-format-internal-model with emerging standard early; if standard fails to materialize by Q4 2026, consider proposing one (Schliff's adapter normalization layer becomes the de-facto standard if no alternative exists) |
| R12 | IPC / upload boundary crash in Säule 4 (VS Code extension or leaderboard submission) | Medium-High (new attack surface in v8) | Medium | JSON-schema validation on all IPC; `BadJSON`+oversize+Zip-Slip guards on leaderboard; OAuth/API-key gates documented; all crashes covered by adversarial tests before ship |
| R13 | Säule 5 signing-key compromise via filesystem path-traversal | Medium (depends on §9 Principle 1 enforcement) | Critical (audit-trail integrity loss) | Keys in env-vars only, never on filesystem; key-age enforcement; append-only receipt directory; no auto-generated convenience keys |
| R14 | Adapter-dependency supply-chain compromise (Promptfoo-yaml-parser, OpenAI-evals-jsonl, DeepEval pytest-plugin) | 20% over 2 years | High | Pin adapter versions in `schliff[adapters]` extras; include their SBOM in Schliff release notes; zero-tolerance policy for unsigned upstream releases; rotate or fork if upstream goes unmaintained |

Numbering preserved from v0.1 with R5 merged into R3 and R10 merged into R6. New entries: R11, R12, R13, R14 (added v0.2 from security and market-validation reviews).

The register is updated at every reviewer-agent pass. New entries require an owner.

---

## 12. Decision-records (ADR-lite)

Each entry: decision, alternatives considered, why-this-one, what-would-flip-it.

**ADR-001 — Position Schliff as a measurement layer, not a competitor.**
- Alternatives: (a) compete head-on with Promptfoo for output-eval, (b) merge into agnix as a quality module, (c) become a hosted SaaS
- Chosen: (d) measurement layer used by all of the above
- Why: avoids 3 unwinnable head-on fights; Datadog precedent shows the category is a viable scaling path; matches existing deterministic-first ideology
- Flip if: Anthropic ships a free official skill-quality SDK with the same deterministic-first API AND market evidence shows users prefer the official version over Schliff (≥ 80% adoption inside 12 months of Anthropic's launch). Response then aligns with R1 mitigation: re-position as adapter / reference implementation under the official SDK; only consider retirement of the core if Schliff's deterministic-first differentiation no longer holds (e.g., Anthropic's official tool ships the same engine and supersedes Schliff's MIT advantage).

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
- Why: agents over-claim in extended runs; the protocol caught false-positives in the v7.2.0 review (e.g. SSRF claim was wrong because allowlist was overlooked); validated again on this spec's own review (market-validation softened the "LLM-judge-first" claim that v0.1 overstated)
- Flip if: the protocol's overhead exceeds its benefit (track via post-mortems)

---

## 13. Open questions (block ship-readiness)

These must be answered before any Säule begins implementation. Each has a recommended-resolution strategy.

| # | Question | Recommended resolution |
|---|---|---|
| OQ1 | Are the existing 28 v8-final-plan commits + 5 v8-design.md docs still authoritative for Säule 1, or do they need refactor? | Keep existing v8 plan as Säule 1's implementation document; this strategy doc only re-positions. ANSWERED v0.2: existing plan stands; cross-reference for `allowed_root` requirement must be added explicitly per architecture review. |
| OQ2 | Should v7.2.1 hotpatch ship before Säule 1 begins? | Yes, ~4h gain in user experience; do not let it block beyond next focused session. |
| OQ3 | What is the corpus for Säule 2's "40% deterministic-shortcut hit rate" claim? | Commission a research-agent to scan top-100 public Promptfoo suites; result decides whether the marketing claim survives. Market-validation review confirmed: no public corpus exists, must build (~40h research effort). Schedule: month 2 of Säule 2, BEFORE marketing claims finalize. |
| OQ4 | Is `agnix`/`agent-sh` outreach a Q3 2026 task or earlier (now that v7.2.0 is out)? | Earlier — open distribution conversation while Säule 1 builds; cost is one email. |
| OQ5 | Should the leaderboard site (`leaderboard.schliff.dev`) be deferred to Q4, or is it useful for Säule 4 sooner? | Defer; it is a multiplier of trust, not a generator of trust. Build trust via 10+ external CI integrations first. |
| OQ6 | Who reviews Säule 5 compliance claims (legal review)? | TBD. Track as risk R8. Do not market Säule 5 publicly until resolved. |
| OQ9 | Säule 3 API design — will `observe(trace_list)` or streaming-detector paradigm require Säule-1 surface changes? | (Added v0.2 from architecture review.) Commission a 1-week design spike in early Q3 2026 to de-risk: prototype `observe()` against 3 trace formats; if it requires Säule-1 surface change, surface change ships in Säule 1 v0.2 minor revision; if not, Säule 3 is a pure adapter. |

OQ7 (test infrastructure) and OQ8 (burn-rate) from v0.1 deferred to per-Säule research phases (per simplify review — they are micro-questions, not vision-blockers).

---

## 14. Reviewer-agent verdicts (v0.1 review, integrated in v0.2)

### Architecture-reviewer — GREEN-WITH-CONDITIONS
- **Verdict:** No blockers. The codebase has evolved to address critical architectural risks. Säulen-split is sound.
- **Conditions integrated v0.2:** (1) calibrated-weights hidden state documented as feature in §6.1 + Principle 2 reworded; (2) `allowed_root` cross-reference added as Säule-1 action item; (3) Säule-3 stream-vs-stateless tension added as OQ9; (4) Säule-4 leaderboard wording clarified as quality-bar-not-marketplace (§6.4 + §8).
- **Awareness findings (non-blocking):** runtime.py has implicit `claude` CLI dependency (acceptable); composite.py cache is process-local-not-thread-safe (documented); MCP-tool-scoring spec must be written before Phase 1c (was already in v8-final-plan).

### Security-reviewer — GREEN-WITH-CONDITIONS
- **Verdict:** No exploitable vulnerabilities introduced. Three Säulen (2, 3, 4) introduce new boundaries that must be hardened in their sub-specs before code.
- **Conditions integrated v0.2:** (1) Principle 8 added — adapter input validation; (2) R11 / Principle 7 strengthened — trace content leakage to third-party sinks; (3) Principle 9 / R12 added — IPC + upload boundaries; (4) §6.5 Key Management subsection + R13 added; (5) R14 added — adapter supply-chain risks; (6) Principle 7 strengthened to flag PII fields in observe() output.
- **Hardening (defense-in-depth, tracked):** Säule-2 assertion-type whitelist (already in §6.2 acceptance criteria); Säule-3 false-positive baseline expanded from 100 to 1000+ traces; Säule-4 leaderboard auth via OAuth/API-key.

### Market-validation-reviewer — GREEN-WITH-CONDITIONS
- **Verdict:** Strategic thesis defensible. Three corrections required.
- **Corrections integrated v0.2:** (1) star counts updated (Promptfoo 12k → 20.5k, DeepEval 10k → 15k, agnix 207 → 208, awesome-claude-code 38.9k → 40.9k); (2) LangFuse 25k★ added to §5 table; (3) "LLM-judge-first" framing softened in §3 — Promptfoo + DeepEval recommend deterministic-first in docs but their tooling defaults still pull users toward LLM-judges; Schliff's wedge is library-first canonical implementation.
- **Findings integrated v0.2:** R11 added (no AI-trace standard, OpenTelemetry-AI nascent) — affects Säule 3 long-term; R1 commentary updated (Anthropic Agent Skills standard already shipped Dec 2025, Skill-Creator plugin Mar 2026 — increases probability of full quality-scorer SDK).

### Simplify-reviewer — GREEN-WITH-CONDITIONS
- **Verdict:** Spec is sound but contains redundancy. Several high-value cuts taken in v0.2; aggressive cuts deferred.
- **Cuts integrated v0.2:** (1) §15 + §16 merged into single Navigation & Governance; (2) R3 + R5 merged → R3; R6 + R10 merged → R6 in risk register; (3) Säule ship-target lines removed from §6 (single source of truth in §7); (4) §10 parallel-agent-assumption explicitly noted as a workflow load-bearer.
- **Cuts NOT taken (rationale):** §2+§4 collapse and §3-table-move would conflict with new security/market content additions; preserved for clarity. §9 Principles kept inline (not moved to ARCH-005) because they are read frequently by reviewer-agents and the indirection cost exceeds the duplication cost.

---

## 15. Navigation & Governance

**Cross-references (related specs and source docs):**
- v8 implementation detail (Säule 1 superset): `docs/specs/plans/2026-03-29-v8-final-plan.md`
- v8 architectural design: `docs/specs/2026-03-28-v8-design.md`
- System prompt scoring spec (Säule 1 sub-component): `docs/specs/system-prompt-scoring-spec.md`
- Registry platform (Säule 4 sub-component): `docs/specs/schliff-registry-platform.md`
- v7.2.1 hotpatch queue (must precede Säule 1): see `project_schliff_state.md` in memory + `Schliff Plan 2026-04-24 — Ultrareview + Optimizations.md`
- Release procedure (binds every Säule's ship gate): `RELEASING.md`

**Supersession scope:** This document supersedes the *vision* sections of `2026-03-28-v8-master-plan.md` and `2026-03-29-v8-final-plan.md`. It does NOT supersede their *implementation* content (those plans remain authoritative for Säule 1 mechanics).

**Versioning of this document:**

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-04-25 | Claude (drafted on Franz's brief) | Initial draft, dispatched to 4 reviewer-agents |
| 0.2 | 2026-04-25 | Claude (post-review) | Integrated all conditions from architecture / security / market-validation / simplify reviewers. New: Principles 8 + 9, R11–R14, OQ9, Säule 5 Key Management subsection. Updated: §3 LLM-judge framing softened, §5 star counts current as of 2026-04-25 + LangFuse added, §6.1 calibrated-weights documented, §6.4 leaderboard scoped as quality-bar-not-marketplace. Merged: R3+R5 → R3, R6+R10 → R6, §15+§16 → §15. §14 reviewer verdicts populated. |
| 0.3 | 2026-04-25 | Claude (Round-2 post-review) | Round-2 review by 4 fresh agents (spec-quality / executability, adversarial red-team, simplify v0.2 fresh pass, cross-coherence + smartest-next-step). All GREEN-WITH-CONDITIONS, 0 BLOCKER. **One genuine contradiction fixed:** ADR-001 flip condition aligned with R1 mitigation (was "shut down core" vs "stay reference impl" — now consistent: re-position as adapter/reference impl, retire only if differentiation collapses). **Four too-optimistic claims softened** per red-team: §3 "Schliff is alone" → "deterministically alone in instruction-files" (general linters cover code), §4 Principle 1 "canonical" → "first library-first impl, canonicality earned by adoption", §5 distribution-channel "Yes" → "potential Yes contingent on competitive incentives", §7 Q2 confidence HIGH → MEDIUM-HIGH (HIGH only after hotpatch ships). Simplify-2's bigger cuts (§14 compression to 4 lines, §6.5 Key Management move) NOT taken — current §14 size is already moderate, Key Management content is load-bearing for security clarity. |

Future revisions: bump version, log the change, re-trigger the reviewer-agent pass on any v0.X+1 substantive revision (corrections-only edits do not require re-review).
