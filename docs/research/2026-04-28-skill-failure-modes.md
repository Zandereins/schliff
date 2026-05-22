---
date: 2026-04-28
status: Phase 0 COMPLETE — human-coded & accepted by maintainer 2026-05-22; Kill-Gate-1 PASS (narrowed scope). See End Consolidation. Claude 10-council pass retained as third-opinion advisory layer.
type: research
phase: 0 (failure-mode analysis)
sprint: v8.0
target-completion: 2026-04-30 EOD
related-spec: docs/specs/2026-04-27-v8-product-completion.md
related-adrs: docs/adr/0001-failure-mode-first-scoping.md, docs/adr/0002-calibration-set-protocol.md
methodology: Husain (evals-faq) + Shankar (EvalGen UIST 2024) — open-coded → axial-coded failure taxonomy
---

# SKILL.md Failure-Mode Analysis — Phase 0

## Objective

Read SKILL.md files from a **stratified familiar-core + representative mini-probe** corpus (no pre-existing rubric), write open-coded failure notes, cluster into a taxonomy. **Stopping criterion is theoretical saturation** (no new open-codes emerging), not a fixed N. Output drives the LLM-Judge dimension scope for v8.0 P3 (AI-Eval pillar).

**Hard kill-gate end-of-Day-3:** if no LLM-judge-worthy dimensions emerge that the deterministic linter does not already cover, AI-Eval pillar deferred to v8.1.

## Day-1 Scope Decision (2026-04-28, revised after 6-agent research evaluation)

Phase-0 corpus = **stratified familiar-core + representative mini-probe**, saturation-driven. Revised from ADR-0001's "30 = Anthropic 13 + Rezvani 17" in two iterations: (a) maintainer-familiarity → Rezvani dropped; (b) a 6-agent research evaluation (Karpathy / Hamel-Maven / linter-coverage / ecosystem / dimension-hypothesis / positioning lenses) showed that all-familiar **over-corrects** on representativeness.

- **Familiar-core (high-confidence labels):** Anthropic (Apache-2.0 example skills) + Karpathy (`karpathy-guidelines`) + **superpowers** (obra, MIT — maintainer uses daily) + Schliff dogfood. Famous, cleanly-licensed, judgeable with confidence; improving them = strongest world-value case studies.
- **Representative mini-probe:** real messy community skills from the existing scored 120-file corpus (`docs/launch/corpus/`), filtered to domains the maintainer can judge (dev-tooling / content / automation — NOT finance/compliance/medical). Injects the GROSS production failure modes (stub/manifest, prose-free, no-procedure) the polished familiar tail never exhibits. Production reality: mean composite 61.7, 59% below grade C (`docs/launch/corpus/stats.md`).
- **Rezvani** stays dropped from Phase-0; benchmark-corpus role deferred to P2/B1.
- **Karpathy license** ⚠: MIT-in-file but no root LICENSE → Phase-0 analyze-only; benchmark inclusion gated on license confirmation (B1).
- **N saturation-driven**, not fixed.

**Why this beats all-14 (Hamel doctrine):** a judge calibrated only on 99th-percentile skills passes its gate but fails to generalize to the wild skills Schliff scores. The probe restores representativeness without sacrificing label-confidence (domain-filtered + the maintainer's own superpowers familiarity).

**Spec/ADR reconciliation:** ADR-0001/0002 addenda + spec §3/§9 patches record this — bundled with Day-1 EOD commit.

## Method (Husain/Shankar canonical pattern)

1. **Read individually, no rubric in mind.** Free-form notes per skill — what's wrong, why, what would a good version do differently.
2. **Open coding (Day 1-2).** First-pass tags emerge from notes — use `#tag-name` prefix for searchability.
3. **Axial coding (Day 3).** Cluster open codes into ≥3 distinct semantic clusters. Those become candidate LLM-Judge dimensions.
4. **Sub-reviewer pass (Day 3 EOD).** Cross-family subagent confirms taxonomy is genuinely beyond deterministic-linter coverage (Kill-Gate 1).

**Constraint:** the deterministic linter (skills/schliff/scripts/scoring/registry.py) already scores 7 default dimensions: structure, triggers, quality, edges, efficiency, composability, clarity. The LLM-Judge layer must target what the deterministic layer cannot detect — semantic, contextual, disambiguating failures. Per-note filter while reading: **"would a regex / deterministic check already find this?"** If yes → not LLM-judge-worthy, skip or hedge.

> **Score caveat (verified by linter-coverage agent):** the CLI scorer measures only 4/8 dims (structure, efficiency, composability, clarity). `triggers` (0.20), `quality` (0.20), `edges` (0.15) return −1 — **55% of the weight profile is dark** because no eval suites exist in the corpus. The `composite` below is a partial structural signal, not a full baseline. A high composite means "clean on the 4 measured structural dims" — which is exactly why high-composite skills are good beyond-linter specimens.

## Corpus Sample — Day-1 reading set (stratified familiar-core + mini-probe)

Rows 1-10 = Day-1 confirmed reading set. Rows 11+ = reserve (read Day-2 if saturation not reached). `band:probe` = real messy community skill (representativeness injection).

> **Durable source (2026-05-22):** the 10 source SKILL.md are snapshotted reboot-proof at `benchmarks/corpus/v1/phase0-snapshot/` (see `MANIFEST.md` there for origin paths, sha256, and bundle-presence). The `/tmp` and plugin-cache paths in the table below are the *original* locations; re-code and verify against the snapshot.

| #  | Source       | Skill name           | Local path · composite · band | Read-date | Note-tag |
|----|--------------|----------------------|-------------------------------|-----------|----------|
| 1  | anthropic    | webapp-testing       | `/tmp/schliff-corpus-v1/anthropics-skills/skills/webapp-testing/SKILL.md` · 78.0 · high | 2026-05-22 | #unstated-precondition |
| 2  | anthropic    | canvas-design        | `/tmp/schliff-corpus-v1/anthropics-skills/skills/canvas-design/SKILL.md` · 58.6 · low | 2026-05-22 | #fabricated-context |
| 3  | anthropic    | brand-guidelines     | `/tmp/schliff-corpus-v1/anthropics-skills/skills/brand-guidelines/SKILL.md` · 59.6 · low | 2026-05-22 | #capability-overclaim |
| 4  | anthropic    | internal-comms       | `/tmp/schliff-corpus-v1/anthropics-skills/skills/internal-comms/SKILL.md` · 59.4 · low | 2026-05-22 | #owner-coupled |
| 5  | karpathy     | karpathy-guidelines  | `/tmp/schliff-corpus-v1/karpathy-skills/skills/karpathy-guidelines/SKILL.md` · 67.6 · mid | 2026-05-22 | #self-inconsistent-standard |
| 6  | superpowers  | brainstorming        | `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/brainstorming/SKILL.md` · 70.9 · mid | 2026-05-22 | #process-overhead-mismatch |
| 7  | superpowers  | systematic-debugging | `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/systematic-debugging/SKILL.md` · 66.8 · mid | 2026-05-22 | #confident-but-unsourced |
| 8  | community    | Nemp-memory          | `docs/launch/corpus/skill/SukinShetty__Nemp-memory__SKILL.md.md` · 0.0 · probe (gross stub) | 2026-05-22 | #desc-body-mismatch (linter-redundant) |
| 9  | community    | algorithms           | `docs/launch/corpus/skill/luofengmacheng__algorithms__skill.md.md` · 56.3 · probe (thin dev) | 2026-05-22 | #unguarded-destructive |
| 10 | community    | GAP-Design-System    | `docs/launch/corpus/skill/neatsarab__GAP-Design-System__Skill.md.md` · 48.8 · probe (⚠ 1987 lines — skim for hypertrophy) | 2026-05-22 | #scope-bloat-codebase-dump |
| 11 | anthropic    | claude-api           | `/tmp/schliff-corpus-v1/anthropics-skills/skills/claude-api/SKILL.md` · 68.4 · mid (K1-positive: gates assumptions) | _(reserve)_ | #_(tag)_ |
| 12 | anthropic    | mcp-builder          | `/tmp/schliff-corpus-v1/anthropics-skills/skills/mcp-builder/SKILL.md` · 79.1 · high | _(reserve)_ | #_(tag)_ |
| 13 | anthropic    | skill-creator        | `/tmp/schliff-corpus-v1/anthropics-skills/skills/skill-creator/SKILL.md` · 67.8 · mid (meta, 485L) | _(reserve)_ | #_(tag)_ |
| 14 | anthropic    | doc-coauthoring      | `/tmp/schliff-corpus-v1/anthropics-skills/skills/doc-coauthoring/SKILL.md` · 63.6 · low (K4-positive: reader-test loop) | _(reserve)_ | #_(tag)_ |
| 15 | anthropic    | algorithmic-art      | `/tmp/schliff-corpus-v1/anthropics-skills/skills/algorithmic-art/SKILL.md` · 57.6 · low (strong K4-fail, 405L) | _(reserve)_ | #_(tag)_ |
| 16 | superpowers  | writing-skills       | `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/writing-skills/SKILL.md` · 58.3 · low (meta, 655L; description-leak doctrine) | _(reserve)_ | #_(tag)_ |
| 17 | community    | _(sweet-spot probe)_ | _(pick a 300-2000-token messy skill from docs/launch/corpus/skill/ on Day 2)_ | _(reserve)_ | #_(tag)_ |

## Open-coded Failure Notes (Days 1-2)

(One subsection per skill, ~50-200 words free-form. Use `#tag-prefix` consistently for clustering. Per-note filter: "would a regex / deterministic check already find this?" — if yes, skip or hedge.)

### Maintainer re-coding log (2026-05-22 — human pass, labeller of record)

> Franz re-codes each skill in his own judgment; Claude pre-stages + offers a third opinion (does not grade). These entries are the Phase-0 **ground-truth open-codes**; the per-skill council notes below are the third-opinion advisory layer they were checked against (ADR-0001 Alt-3 honored: human-ratified, not subagent-of-record).

- **Skill 01 webapp-testing — ACCEPTED.** Agrees with the A–E pre-stage. Core beyond-linter: `#unstated-precondition` + `#missing-failure-path` (no `playwright install chromium`, no fallback if the black-box script errors). `#vague-success-criteria` (the "absolutely necessary" gate). **Hedged:** `#env-coupled` weak — the SKILL.md body only hardcodes `/tmp/inspect.png` (broadly available); the sandbox-only `/mnt/user-data/outputs/` path is in the bundled `examples/console_logging.py`, not the body. Mild `#desc-body-mismatch` ("viewing browser logs" only via example). Struck: typo (linter-catchable). Verified: `scripts/with_server.py` present.
- **Skill 02 canvas-design — ACCEPTED.** A confirmed as heaviest + safety-relevant: `#fabricated-context` (Z.122 fake "the user ALREADY said…" quote firing an unconditional second pass, Z.126) — conversation-state spoofing, drove **Cluster F**. B `#vague-success-criteria`/`#unverifiable-claim` (Z.106/114 vibes as the *operative* criteria; adjective-density itself hedged as regex-near). C `#instructed-redundancy` + `#self-inconsistent-standard` (Z.48/83 "Emphasize craftsmanship REPEATEDLY" vs Z.47 "mention once"). D `#unstated-assumption`/`#capability-overclaim` (Z.89–96 assumes every request hides a niche reference). Validated rewrite in `rewrites/` (PASS).
- **Skill 03 brand-guidelines — ACCEPTED.** Cluster-A anchor logic confirmed: lead with `#capability-overclaim`/`#desc-body-mismatch` (Z.3/42/44/45/57/72 active verbs describing non-existent execution; verified only `SKILL.md`+`LICENSE.txt` ship), `#missing-procedure` **supporting only** (else collapses to linter). `#unstated-precondition` (Z.72 `.pptx` scope vs "any artifact"). `#vague-success-criteria` (Z.51 "smart color selection"). **Maintainer agrees** Cluster A is a fragile one-skill anchor → `capability_fidelity` metrics **gated** on a procedural + non-procedural counter-sample before trust. Validated rewrite (PASS).
- **Skill 04 internal-comms — ACCEPTED.** Core = `#owner-coupled` (Z.3 first-person "help **me** write… formats that **my company** likes to use"). **CORRECTION ratified:** all 4 `examples/*.md` present & load-bearing → prior "unjudgeable in isolation / produces nothing" overstated; `#externalized-content` reframed as a **harness meta-property** (load referenced files before judging), NOT a defect. `#over-broad-trigger` (Z.32 keywords) hedged. Security/tool-ingestion + "Never use any formatting other than this" = **bundle-level advisory** (in `examples/`, not this SKILL.md unit).
- **Skill 05 karpathy-guidelines — ACCEPTED + DECISION.** A–D as framed: reflexive `#self-inconsistent-standard`+`#vague-success-criteria` (§4 demands verifiable criteria yet §2 Z.33 / §3 Z.49 are themselves unverifiable), Z.31 "200→50" unactionable (counterfactual unknown at write-time), Z.11 vs Z.60 `#scope-boundary-undefined`, latent §1↔§3 conflict (Z.20 push-back vs Z.41 don't-refactor). **🔑 MAINTAINER DECISION: collapse Cluster D → "B with a `#reflexivity` sub-tag."** D is NOT retained as a standalone judge dim; `self_consistency_proportionality` folds into `verifiable_success`. Rationale: even at D's near-best case (karpathy) it reduces to B + `#scope-boundary-undefined`; reflexivity is the only distinct ingredient and is archetype-bound. **Supersedes the locked advisory's 4th dim** (full reconciliation batched at end-of-re-coding).
- **Skill 06 brainstorming — ACCEPTED.** Core = A `#self-inconsistent-standard`+`#process-overhead-mismatch` (Z.13/18 `<HARD-GATE>` mandates the full 9-step ceremony for "a config change" vs Z.142 "YAGNI ruthlessly" — applies YAGNI to designs, exempts itself). B `#unstated-precondition`+`#brittle-handoff` (Z.32/66/136 writing-plans terminal + Z.29/111 git/fs spec commit — two distinct preconditions). C `#over-broad-trigger`/`#mis-triggering-risk` **HEDGED** (regex-near). D mild `#capability-overclaim` (`<HARD-GATE>` = suasion, not runtime enforcement). Security: instruction-capture chokepoint (advisory, low).
- **Skill 07 systematic-debugging — ACCEPTED + DECISION.** A `#unverifiable-claim`/`#confident-but-unsourced` (Z.292-296 "95% vs 40%" etc. sourced only to "From debugging sessions"; **Z.276 "95% of 'no root cause' cases are incomplete investigation"** is the self-sealing/dangerous instance — pressures override of a correct environmental diagnosis). B = proportionality `#absolutism-overconstraint`/`#process-overhead-mismatch` (Z.12/19/22/42 — four-phase ritual mandated for a typo). **CORRECTION ratified:** `root-cause-tracing.md` / `defense-in-depth.md` / `condition-based-waiting.md` all present → `#unstated-precondition` dropped, `#brittle-handoff` downgraded to filename-not-path (hedged). **🔑 MAINTAINER DECISION (Hamel 4-bar test): proportionality/absolutism is NOT a scored judge dim** — retained as open-code tag `#process-overhead` ("observed, not operationalized"). Fails frequency (2/10, single archetype), cross-archetype generalization, and inter-rater agreement (value judgment — the superpowers authors treat the always-on gate as a *feature*); partly linter-near. **Revisit-trigger:** promote only if it later recurs across non-guideline archetypes with measurable κ. → **Post-collapse scored scope = 3 core (B incl. `#reflexivity` · C · A-probationary) + 1 opt-in (F) + `#process-overhead` as retained annotation.**
- **Skill 08 Nemp-memory — ACCEPTED.** Fully linter-caught (5-line stub, 0.0 correct) → **judge NOT run.** `#desc-body-mismatch`/`#capability-overclaim` linter-redundant; `metadata:{openclaw:{always:true}}` (Z.4) inert/unknown-key for the CC loader (cross-loader watch-item, not a finding). **Confirms the GATING INVARIANT** — judge runs only above a linter-completeness floor (Husain failure-mode-first). Floor anchor of the set.
- **Skill 09 algorithms — ACCEPTED + DECISION (Hamel-tightened).** A `#name-content-mismatch`/`#desc-body-mismatch`/`#mis-triggering-risk` (no frontmatter; "algorithms" = Linux sysadmin one-liners; the absence is linter-caught, the topic-mismatch is semantic). B (safety core) `#unguarded-destructive`/`#missing-failure-path` (Z.3 `echo b > /proc/sysrq-trigger` = unsynced reboot; Z.15-21 grub `mem=` persistent footgun; zero warning). C `#missing-procedure`/`#no-trigger` (mostly linter). Copy-run hazards (`//`, `%(jobid)`) hedged secondary. **🔑 MAINTAINER DECISION (Hamel "cheapest tool first" + "align on real data"):** NOW = a **deterministic default detector** ("contains destructive/mutating command") → **human-review flag, NOT an LLM score**. DEFERRED = the opt-in `harmful_downstream_instruction`/guardedness LLM dim — build only once enough destructive specimens exist to align it (can't validate TPR/TNR at n≈1–2); binary criterion (warning + safe-alt + reversibility) written + agreement-tested before it scores. Reframe honestly as "safety detector + flag," not a new judge dim. Validated rewrite `09-linux-ops-cheatsheet` (PASS).
- **Skill 10 GAP-Design-System — ACCEPTED + DECISION.** ~90% (effectively ~95% of judge-relevant signal) linter-redundant: no frontmatter, hypertrophy, missing-procedure all linter-caught; §16 env = `VITE_` placeholders, no secrets. **Net-new judge-dim signal ≈ 0.** Residuals downgraded below dimension status: `#name-content-mismatch` = shared annotation with 09 (filename↔content; entangled with the structural no-name finding; overlaps linter trigger/structure dims); `#language-trigger-ambiguity` = 1/10 + partly deterministic → **candidate deterministic linter check**, not a judge dim. **🔑 MAINTAINER DECISION: Skill 10 = control / negative specimen** — anchors the *hypertrophy* floor (as 08 anchors the *stub* floor), confirms the linter covers the dumped-codebase archetype + the gating invariant. No rewrite (council verdict: reclassify, don't repair).

### Skill 01: webapp-testing · anthropic · 78.0 · high

**[2026-05-22 — 10-council synthesis · advisory, Franz = labeller of record]**

**CORRECTION to prior draft:** the bundled `scripts/with_server.py` IS present and its argparse signature (`--server`/`--port` both `action='append'`, `command` as `REMAINDER`) matches the SKILL examples exactly — so the earlier "script absent / unverified, no fallback" premise was overstated. The real beyond-linter gap is a narrower **`#unstated-precondition`**: the skill assumes Playwright **and its browser binaries** (`p.chromium.launch`) **and** Python are installed; `playwright install chromium` — the single most common real-world failure — is never mentioned, with no fallback → `#missing-failure-path`. "DO NOT read the source until you try running... find a customized solution is *absolutely* necessary" is an uncheckable judgment threshold → `#vague-success-criteria`; combined with the black-box mandate it actively suppresses recovery if the script errors. The SKILL.md body hardcodes `/tmp/inspect.png` (broadly available — minor); the Claude-sandbox-only `/mnt/user-data/outputs/console.log` path lives in the bundled `examples/console_logging.py`, not the body, so as a SKILL.md-unit finding `#env-coupled` is weak/hedged. Mild `#desc-body-mismatch`: "viewing browser logs" is surfaced only via a *referenced example file*, not the procedure itself.

**Best-version fix:** (1) add an explicit preconditions block — `pip install playwright` + `playwright install chromium` + a check/install fallback; (2) replace the "absolutely necessary" gate with a concrete recovery branch ("script `--help` errors or exits non-zero → read source / write Playwright directly"); (3) parameterize the hardcoded output path (`os.environ.get(..., "/tmp")`).

### Skill 02: canvas-design · anthropic · 58.6 · low

**[2026-05-22 — 10-council synthesis · advisory, Franz = labeller of record]**

The richest beyond-linter specimen. Dominant failure: success criteria are aesthetic incantation — "museum or magazine quality," "looks like it took countless hours," "everything screams expert-level craftsmanship," "This is true art" — vibes a downstream model cannot self-check → `#vague-success-criteria` `#unverifiable-claim`. The vagueness is then weaponized as a *generation instruction*: "**Emphasize craftsmanship REPEATEDLY**... repeat phrases like 'meticulously crafted'" → `#instructed-redundancy`, which directly contradicts the adjacent rule "Avoid redundancy: each design aspect should be mentioned once" → `#self-inconsistent-standard` (two rules collide in the same section). Two distinct injected-state failures: (1) the "FINAL STEP" hardcodes a **fabricated user quote** — "The user ALREADY said 'It isn't perfect enough...'" — asserting a turn that never occurred and firing an unconditional refine loop → `#fabricated-context` (conversation-state spoofing: it corrupts the model's representation of what the user actually said). (2) "DEDUCING THE SUBTLE REFERENCE" presupposes every request hides a "subtle, niche reference... woven invisibly" → `#unstated-assumption` `#capability-overclaim`.

**Best-version fix:** (1) delete the fabricated quote; replace the FINAL STEP with a *conditional self-audit* checklist (overlap / off-page / decorative-not-essential → fix); (2) convert vibes to checkable acceptance criteria (single page unless asked; nothing overlaps; all elements within margins; palette ≤ K colors; fonts from `./canvas-fonts`); (3) drop the "REPEATEDLY" mandate; (4) make subtle-reference *optional* ("if the request implies a concept, weave it in; otherwise let the philosophy stand").

### Skill 03: brand-guidelines · anthropic · 59.6 · low

**[2026-05-22 — 10-council synthesis · advisory, Franz = labeller of record]**

**Verified:** the directory ships only `SKILL.md` + `LICENSE.txt` — no script, no python-pptx call. Yet the description ("**Applies** Anthropic's brand colors and typography to **any sort of artifact**") and the "Features"/"Technical Details" sections read as runtime behavior — "**Applies** Poppins font to headings (24pt+)," "**Automatically falls back** to Arial," "**Applied via** python-pptx's RGBColor class." It neither performs the capability nor tells the agent how to → `#capability-overclaim` `#desc-body-mismatch`. This is the genuine beyond-linter core: the skill is *formally clean* and reads as a finished active tool while describing execution that does not exist — distinct from a plain stub. **`#missing-procedure` is present but must stay a SUPPORTING tag**: if the case is filed primarily under it, it collapses into linter territory (the linter catches absent procedure structurally); the load-bearing, regex-invisible signal is the *false active-verb claim*. "Smart color selection based on background" defines no contrast rule → `#vague-success-criteria`. "Applied via python-pptx" silently scopes the capability to `.pptx` while the description claims "any artifact" → `#unstated-precondition`.

**Best-version fix:** pick one — (a) reframe to honest reference (change every "Applies/Applied/Cycles" to declarative tokens) **or** (b) actually ship the python-pptx helper the prose implies; then (c) declare the `.pptx` scope and the orphaned "24pt+" threshold; (d) define-or-delete "smart color selection" (e.g. relative-luminance > 0.5 → dark text).

### Skill 04: internal-comms · anthropic · 59.4 · low

**[2026-05-22 — 10-council synthesis · advisory, Franz = labeller of record]**

**CORRECTION to prior draft:** all four delegated `examples/*.md` files ARE present and load-bearing (`3p-updates.md` carries the strict format spec, tools, workflow) — so "if those files are absent the skill produces nothing / unjudgeable" was factually wrong on this corpus. The real residue: the description is first-person — "help **me** write... formats that **my** company likes to use" — encoding an absent owner's private preferences as universal → `#owner-coupled` (this skill is the clean exemplar for the tag). `3p-updates.md`'s "very strict formatting. Never use any formatting other than this" presents one anonymous team's convention as an absolute → `#self-inconsistent-standard` `#absolutism-overconstraint`. "FAQs / common questions" can fire on general Q&A unrelated to *internal* comms → `#over-broad-trigger` (borderline-judge — a regex catches the literal string, not the semantic over-breadth). **`#externalized-content` is downgraded to a meta-property, not a defect**: progressive disclosure is the intended Anthropic pattern; the *judge harness* must LOAD referenced files before judging, rather than penalize delegation.

**Best-version fix:** (1) de-personalize the description + state the precondition that `examples/` reflect the org's conventions; (2) soften the false absolute to "default unless the team specifies otherwise"; (3) add a send/ingestion guardrail — untrusted tool-pulled content (Slack/Gmail/Drive) → human-confirm before drafting/sending (prompt-injection-to-publication surface); (4) tighten the FAQ trigger to "internal company FAQs."

### Skill 05: karpathy-guidelines · karpathy · 67.6 · mid

**[2026-05-22 — 10-council synthesis · advisory, Franz = labeller of record]**

High-quality content; refinements, not defects. The sharpest beyond-linter finding is **reflexive self-inconsistency**: §4 mandates "Define success criteria" and condemns weak ones like "make it work," yet §2's own test "Would a senior engineer say this is overcomplicated?" and §3's "Every changed line should trace directly to the user's request" are exactly that unverifiable kind — the skill holds the *agent's output* to a verifiability bar its *own rules* fail → `#self-inconsistent-standard` `#vague-success-criteria`. "If you write 200 lines and it could be 50, rewrite it" is unactionable: the counterfactual 50-line version is unknowable at write-time. "For trivial tasks, use judgment" vs §4's plan-demand for "multi-step tasks" leaves the boundary undefined → `#scope-boundary-undefined`. **New (beyond prior draft):** §1 ("If a simpler approach exists, push back") vs §3 ("Don't refactor things that aren't broken") collide on refactor requests with no precedence rule → `#self-inconsistent-standard`. (See Re-Review Delta: this skill is the key datapoint that Cluster D's distinguishing ingredient is *reflexivity* — and is therefore archetype-bound.)

**Best-version fix:** (1) reframe §2/§3 heuristics honestly as "judgment heuristics, not verifiable gates" **or** give checkable proxies ("each abstraction names a second current caller, else inline it"); (2) define the trivial/multi-step cut (">1 file OR >1 logical change"); (3) add a §1↔§3 precedence rule ("explicit refactor request → §1 overrides §3").

### Skill 06: brainstorming · superpowers · 70.9 · mid

**[2026-05-22 — 10-council synthesis · advisory, Franz = labeller of record]**

Three rigidity-vs-philosophy contradictions a regex cannot catch. (1) The `<HARD-GATE>` + "applies to EVERY project regardless of perceived simplicity" + the Anti-Pattern section mandate the full 9-step ceremony for "a config change" / "a todo list," while the skill itself preaches "YAGNI ruthlessly" — it applies YAGNI to *designs* but exempts *itself* → `#self-inconsistent-standard` `#process-overhead-mismatch`. (2) "The terminal state is invoking writing-plans" / "Do NOT invoke any other skill" assumes `writing-plans` is installed and reachable; if absent the flow dead-ends with no degraded path → `#unstated-precondition` `#brittle-handoff` (note: this is a *distinct dependency* from the `docs/superpowers/specs/` git/fs-write assumption). (3) "before any creative work — creating features, building components, adding functionality, or modifying behavior" matches almost every dev request → `#over-broad-trigger` `#mis-triggering-risk` (ceremony fatigue → habituated gate-skipping). The `<HARD-GATE>` pseudo-tag implies a runtime-enforced control that does not exist — it is suasion, mildly `#capability-overclaim`.

**Best-version fix:** (1) add a proportionality tier — trivial/single-file → one-line inline design + inline approval; only multi-component → full 9 steps; (2) make the handoff fail-safe ("invoke writing-plans if available; else present the spec and stop"); (3) narrow the trigger + add an explicit SKIP clause for trivial edits/bugfixes; (4) down-rank `<HARD-GATE>` to a plain MUST.

### Skill 07: systematic-debugging · superpowers · 66.8 · mid

**[2026-05-22 — 10-council synthesis · advisory, Franz = labeller of record]**

Beyond-linter signal concentrates in **fabricated quantitative authority**: "First-time fix rate: 95% vs 40%", "15-30 minutes vs 2-3 hours", "95% of 'no root cause' cases are incomplete investigation" — all sourced only to "From debugging sessions," uncheckable false precision a model will relay downstream stripped of the hedge → `#unverifiable-claim` `#confident-but-unsourced`. The last metric is the dangerous instance: an unsourced stat that *pressures the agent to override a correct "this is environmental" conclusion* — a self-sealing claim that suppresses falsification (the escalation unsourced-stat → behavioral-mandate is what makes it worse than plain marketing numbers). Second: absolutism overconstrains proportionality — "NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST", "If you haven't completed Phase 1, you cannot propose fixes", "Symptom fixes are failure" + "Don't skip when: Issue seems simple" mandate a four-phase ritual for a typo → `#absolutism-overconstraint` `#process-overhead-mismatch`. **CORRECTION to prior draft:** `root-cause-tracing.md`, `defense-in-depth.md`, `condition-based-waiting.md` ALL exist in-directory (verified) — the prior `#unstated-precondition` / strong `#brittle-handoff` was wrong for v5.1.0; downgrade to a hedged filename-not-path fragility only.

**Best-version fix:** (1) strip the four metrics or replace with linkable sources / qualitative claims; (2) add a proportionality escape hatch for trivial fully-understood fixes; (3) soften "Symptom fixes are failure" / "cannot propose fixes" to outcome language; (4) note sibling files live "in this skill directory" with a fallback if relocated.

### Skill 08: Nemp-memory · community · 0.0 · probe (gross stub)

**[2026-05-22 — 10-council synthesis · advisory, Franz = labeller of record]**

Pure stub: frontmatter only, zero body; the linter scores it 0.0 correctly. By the per-note filter this is **NOT** a useful judge specimen — every nameable defect is regex-detectable. The only semantic residue is thin and redundant: the description promises "Save, recall, and search project decisions as local JSON," "Zero cloud, zero infrastructure," which a null body cannot deliver — an extreme `#desc-body-mismatch` / `#capability-overclaim` where the body is null (both linter-redundant here). The nonstandard `metadata: {"openclaw": {"always": true}}` key is inert for Claude Code's loader (unknown vendor namespace) — a lint/unknown-key issue, not a live exploit; the `always: true` *shape* (body-less shell declaring always-on activation) is the right primitive for silent-activation **in any host that honors it**, so flag it as a cross-loader watch-item, not a finding against this artifact. **Verdict: fully linter-caught — do not run the judge here.** This specimen's value is as the floor anchor + evidence for an explicit *gating invariant* (see Re-Review Delta): the judge must run only above a linter-completeness floor, or it will fabricate semantic findings on stubs.

**Best-version fix:** (1) write the body or pull the skill; (2) replace the `openclaw.always` key with an explicit trigger description; (3) align "zero cloud" claims to verifiable steps once a body exists.

### Skill 09: algorithms · community · 56.3 · probe (thin dev)

**[2026-05-22 — 10-council synthesis · advisory, Franz = labeller of record]**

No frontmatter (name/description absent → triggering undefined; the absence is linter-caught, the *consequence* is not). Standout beyond-linter failure: `#name-content-mismatch` — filed as "algorithms" but the body is five Linux sysadmin one-liners (forced reboot, `free -m`, faking RAM via grub, `iostat`, `disown`); a regex sees valid fences + Chinese prose, only semantics catch the topic mismatch → `#desc-body-mismatch` `#mis-triggering-risk`. Worse: **confidently destructive content with zero guardrail** — `echo b > /proc/sysrq-trigger` is an **immediate unsynced kernel reboot** (equivalent to a power-cut: data loss on dirty buffers, no `s,u` sync first), and `mem=1G` in grub is a *persistent* boot footgun that survives reboots — both presented as neutral tips → `#unguarded-destructive` `#missing-failure-path` `#unstated-precondition`. Not a skill at all: no procedure, no when-to-use, no verification → `#missing-procedure` `#no-trigger`. Danger is latent (missing frontmatter means it should never auto-trigger) but on explicit load nothing stays the agent's hand. (See Re-Review Delta: this is the canonical case where routing `#unguarded-destructive` to opt-in-only would *miss the highest-blast-radius failure in the corpus*.)

**Best-version fix:** (1) rename to the real topic + add accurate frontmatter; (2) guard every destructive command (warn + sync-first `s,u,b`; mark grub edit persistent + back-up-first; confirmation-required framing); (3) add preconditions/verification; (4) fix copy-run hazards (`//` comments in shell fences, `%(jobid)` placeholder).

### Skill 10: GAP-Design-System · community · 48.8 · probe (skim — 1987 lines)

**[2026-05-22 — 10-council synthesis · advisory, Franz = labeller of record]**

Skimmed strategically (frontmatter, TOC, §3 Auth, §15 Env, §16 Deploy, code samples). Confirms: no YAML frontmatter (line 1 is a Thai H1), no name/description, no trigger, no procedural "how Claude should apply this" — 1986 lines of Vue3/Vuetify/Pinia reference implementation for a Thai GAP-certification webapp, i.e. a project README/architecture doc mislabeled as `SKILL.md` → `#scope-bloat-codebase-dump` `#hypertrophy` `#no-trigger` `#missing-procedure` (**all linter-detectable** on a 73 KB file). The genuinely beyond-linter residue is **thin and weak**: `#name-content-mismatch` ("Design-System" vs a full-stack app spec) and `#language-trigger-ambiguity` (tri-script Thai/Chinese/English headers fragment retrieval). The prior draft's headline "reference-code dump masquerading as agentic instructions" is the *structural verdict re-narrated*, not independent semantic signal — this artifact is **~90% linter-redundant**; label LOW beyond-linter yield. Dropped from prior draft: `#externalized-content` (the "inverted" use strains the definition; subsumed by `#scope-bloat-codebase-dump`) and `#desc-body-mismatch` (no description exists to mismatch — correct tag is `#name-content-mismatch` against the H1/filename). Security: §15 `.env` uses only safe `VITE_`-prefixed placeholders (`example.com`), no secrets in sampled blocks (~15% read).

**Best-version fix:** (1) reclassify, don't repair — move to `docs/`/`reference/` as architecture documentation; (2) if a skill is genuinely wanted, distill to a ~50–150-line procedural skill (frontmatter + conventions) that *links* the code externally; (3) normalize section headers to English for retrieval.

### Reserve (Day 2 — read if saturation not reached): claude-api, mcp-builder, skill-creator, doc-coauthoring, algorithmic-art, writing-skills, +1 sweet-spot community probe

_(...)_

## Open-code Tag Glossary (2026-05-22 — refreshed by 10-council pass · advisory)

Every `#tag` used in the notes above, one-line definition, and the skill numbers exhibiting it. This is the clustering anchor. (Franz = labeller of record.) **Memberships refreshed 2026-05-22:** file-existence checks overturned three draft assumptions (scripts/examples/sibling files for skills 01/04/07 are actually present) — the affected tags below are corrected; the analytical/cluster-level divergences are recorded separately in **Re-Review Delta**.

- `#unstated-precondition` — skill silently assumes installed tools / bundled files / sibling skills exist, with no prereq statement or fallback if absent. Skills: 01 (browser-binary install), 03 (.pptx scope), 06, 09. *(Removed 04, 07 — their referenced files are present.)*
- `#missing-failure-path` — no instruction for what to do when the happy path fails (script missing, command errors, irreversible action). Skills: 01, 09.
- `#vague-success-criteria` — "done"/"good"/"necessary" defined by unverifiable judgment, not a checkable signal. Grammatically clean, regex-invisible. Skills: 01, 02, 03, 05.
- `#desc-body-mismatch` — frontmatter description promises capability/scope the body does not deliver or match. Skills: 01, 03, 08, 09.
- `#unverifiable-claim` — confident quality or quantitative assertion that cannot be checked. Skills: 02, 07.
- `#instructed-redundancy` — skill explicitly directs the model to repeat/pad downstream output. Skills: 02.
- `#fabricated-context` — skill injects a fake user statement / context that fires unconditionally. Skills: 02.
- `#mis-triggering-risk` — trigger surface broad/ambiguous enough to fire on unrelated requests. Skills: 02, 04, 06, 09.
- `#unstated-assumption` — assumes a situational fact about the request that often won't hold. Skills: 02, 04.
- `#capability-overclaim` — claims to *perform* an action (apply fonts, save JSON) with no procedure/code backing it. Skills: 03, 08.
- `#missing-procedure` — no actionable "how the agent should do this" steps. Skills: 03, 10.
- `#externalized-content` — load-bearing content lives in unshown files; skill unjudgeable in isolation. Skills: 04 *(hedged → reframed as a judge-harness meta-property, NOT a defect: progressive disclosure is the intended pattern; the harness must load referenced files before judging)*. *(Dropped from 10 — its "inverted/everything-inlined" use strained the definition; subsumed by `#scope-bloat-codebase-dump`.)*
- `#owner-coupled` — encodes a specific absent owner's private preferences as universal. Skills: 04.
- `#env-coupled` *(NEW 2026-05-22)* — skill hardcodes paths / runtime assumptions valid only in one execution environment (e.g. `/mnt/user-data/outputs/`), silently failing elsewhere; distinct from `#owner-coupled` (a named human/repo owner). Candidate sub-facet of Cluster C. Skills: 01.
- `#self-inconsistent-standard` — skill violates a rule it itself preaches. Skills: 05, 06.
- `#scope-boundary-undefined` — "trivial vs not" / when-it-applies boundary left to the model. Skills: 05.
- `#process-overhead-mismatch` — mandates heavy ceremony for cases where cost-benefit inverts (simple tasks). Skills: 06, 07.
- `#brittle-handoff` — terminal/next step hard-depends on another skill with no fallback. Skills: 06 (writing-plans), 07 *(hedged/downgraded — sibling `.md` files verified present; only filename-not-path fragility remains)*.
- `#over-broad-trigger` — description so broad it should fire on nearly every request in its domain. Skills: 06.
- `#confident-but-unsourced` — precise-looking numbers attributed to vague/no source. Skills: 07.
- `#absolutism-overconstraint` — "NEVER/ALWAYS/cannot" framing that removes legitimate judgment. Skills: 07.
- `#name-content-mismatch` — skill title/topic unrelated to actual content. Skills: 09.
- `#unguarded-destructive` — irreversible/dangerous commands presented with no warning. Skills: 09.
- `#scope-bloat-codebase-dump` — a full project/codebase pasted in place of a distilled skill. Skills: 10.
- `#hypertrophy` — length far exceeds what the (thin) instructional payload justifies. Skills: 10.
- `#no-trigger` — missing frontmatter/description so the skill has no retrieval handle (largely linter-caught; noted for completeness). Skills: 10.
- `#language-trigger-ambiguity` — mixed/non-English content creates retrieval-trigger ambiguity in an English-keyed system. Skills: 10.

## Axial Clustering (Day 3 morning)

Top failure clusters (target: ≥3 distinct semantic categories):

> **Day-3 cross-check (do NOT consult during open-coding):** after deriving clusters from YOUR own codes, compare them against the research-prior hypotheses recorded in the session synthesis / memory (`feedback_*` notes). Confirmation is a bonus; divergence is itself a finding (criteria drift, per Shankar). The data is the authority — the priors only tell us where the 6-agent evaluation expected failures to concentrate.

**[Advisory axial coding — REVISED 2026-05-22 per Re-Review Delta. Franz = labeller of record; this is NOT the Kill-Gate-1 decision below, which remains the locked record. Revisions reflect the 10-council file-existence corrections and divergences; the locked Decision is left intact for audit.]**

### Cluster A — Capability Fidelity ("says vs does") · ⚠ PROBATIONARY (thin)

- **Description:** the skill *looks formally clean* but its description / stated "Features" promise a capability the body never implements (narrowed: empty-body / missing-procedure cases are excluded — those are linter territory).
- **Member skills (#):** **03 (sole clean anchor)**; 01 (mild — `#desc-body-mismatch` only, after script-present correction); 08 (fully linter-redundant, excluded); 09 (the mismatch is `#name-content-mismatch`, partly structural).
- **Common open-codes:** `#capability-overclaim`, `#desc-body-mismatch` *(load-bearing)*; `#name-content-mismatch`, `#missing-procedure` *(supporting only — if a case is filed under these it collapses into linter territory)*.
- **Deterministic-linter coverage:** partial — "description claims a capability the prose never implements" reads as grammatical, well-headed text → semantic; but the boundary to structural `#missing-procedure` is thin.
- **LLM-Judge value-add hypothesis:** judge reads description against body and flags claim-vs-delivery gaps a regex sees as valid prose.
- **⚠ Delta caveat:** with 03 as the *only* uncontaminated member, A is a one-skill cluster. **Secure a procedural + a non-procedural counter-sample before trusting A's metrics.**

### Cluster B — Verifiable Success Criteria

- **Description:** "done / good / correct" is defined by unverifiable judgment or confident-but-unsourced claims, so the agent cannot self-check.
- **Member skills (#):** 01, 02, 03, 05, 07
- **Common open-codes:** `#vague-success-criteria`, `#unverifiable-claim`, `#confident-but-unsourced`
- **Deterministic-linter coverage:** no — "museum quality" and "zero #REF! errors" are both grammatical sentences; regex cannot tell checkable from vacuous.
- **LLM-Judge value-add hypothesis:** judge rates whether a triggered agent could verify success; flags aspiration-as-criterion and false-precision metrics.

### Cluster C — Assumption Completeness & Dependency Robustness · SOLID (weight shifted)

- **Description:** skill silently depends on unstated context (installed tools/binaries, an absent owner's prefs, sandbox-specific paths) with no statement or fallback.
- **Member skills (#):** 01 (browser-binary install + `#env-coupled`), 03 (.pptx scope), 04 (`#owner-coupled` — the clean exemplar), 06 (writing-plans handoff). *(07 dropped — sibling files verified present; 10 dropped — its issue is structural bloat, not silent dependency.)*
- **Common open-codes:** `#unstated-precondition`, `#owner-coupled`, `#env-coupled` *(NEW)*, `#brittle-handoff`, `#missing-failure-path`.
- **⚠ Delta caveat:** file-existence corrections (04, 07) shift C's weight from the *missing-fallback* half toward the *unstated-assumption / unstated-precondition* half — **scope the dimension to the unstated-assumption core**, not dependency-declaration (which overlaps `composability`). `#externalized-content` is removed as a defect → handled as a judge-harness meta-property (load referenced files before judging).
- **Deterministic-linter coverage:** no — you cannot pattern-match an *absent* statement; detecting a silent assumption requires modeling what a fresh agent would not know.
- **LLM-Judge value-add hypothesis:** judge surfaces preconditions the skill relies on but never states, and the absence of a fallback when they fail.

### Cluster D — Self-Consistency & Proportionality (NOVEL) · ⛔ COLLAPSED INTO B (maintainer decision 2026-05-22)

> **🔑 Maintainer decision (2026-05-22, labeller of record):** Cluster D is **collapsed into Cluster B** as a `#reflexivity` sub-tag and is **NOT retained as a standalone judge dimension**. Even at its near-best case (skill 05 karpathy-guidelines) D reduces to B + `#scope-boundary-undefined`; reflexivity (a skill stating a standard its own body violates) is the only distinct ingredient and is archetype-bound to guideline/process skills. The analysis below is retained as the historical archetype-bound argument that led to this decision.

- **Description:** skill mandates ceremony/absolutism that contradicts its own stated philosophy, or overconstrains simple cases where cost-benefit inverts.
- **Member skills (#):** 05, 06, 07 (+ 02's "mention once" vs "REPEATEDLY" contradiction, + 04's false absolute).
- **Common open-codes:** `#self-inconsistent-standard`, `#process-overhead-mismatch`, `#absolutism-overconstraint`, `#scope-boundary-undefined`
- **Deterministic-linter coverage:** no — requires understanding the skill's own stated principles and detecting self-contradiction / disproportion.
- **⚠ Delta caveat (two-council convergence, 05 + 07):** D's distinguishing ingredient is **reflexivity** — a skill that *states* a normative standard its own body violates. That ingredient is structurally available only in **guideline/process/rubric skills**; outside that archetype D degenerates into B (vagueness) or A (proportionality). karpathy (05) is near best-case and still mostly reduces to B + `#scope-boundary-undefined`. **Keep D low-confidence/archetype-tagged; open question whether it is an independent axis or a sub-flavor of B.** Validate on procedural **and** non-procedural counter-samples before trusting its metrics.
- **LLM-Judge value-add hypothesis:** judge checks whether the skill obeys the standards it preaches and scales effort to task complexity. **Emerged from the blind data, not predicted by the 6-agent priors — a criteria-drift signal (Shankar).**

### Cluster E — Trigger/Routing Semantics (hedge: overlaps deterministic `triggers`)

- **Description:** trigger surface fires on unrelated requests, is over-broad, or is ambiguous (incl. language).
- **Member skills (#):** 02, 04, 06, 09, 10
- **Common open-codes:** `#mis-triggering-risk`, `#over-broad-trigger`, `#language-trigger-ambiguity`, `#no-trigger` (largely linter-caught)
- **Deterministic-linter coverage:** partial — the `triggers` dim (when an eval suite exists) checks form/overlap; the *behavioral* "would this route correctly on a realistic near-miss" half is semantic.
- **LLM-Judge value-add hypothesis:** keep ONLY the simulated-routing half, explicitly disjoint from the structural triggers dim, else it duplicates the linter.

### Cluster F — Harmful / Biasing Downstream Instruction (PROMOTED 2026-05-22 from held-back theme)

- **Description:** the skill instructs the model to do something harmful or biasing downstream — inject a false conversation state, pad output with unsubstantiated claims, or run an unguarded destructive command.
- **Member skills (#):** 02 (`#fabricated-context` — fake "the user ALREADY said…" quote; `#instructed-redundancy`), 09 (`#unguarded-destructive` — `echo b > /proc/sysrq-trigger`).
- **Why promoted (Delta finding):** `#fabricated-context` has **no clean home** in dims A–D — it is an *asserted false fact* (conversation-state spoofing), not a missing one (≠ C) and not a capability gap (≠ A). It is orthogonal and regex-invisible. Two councils (02, 09) independently flagged that the original "revisit if it grows" undersells it.
- **Deterministic-linter coverage:** no for the biasing half (a regex sees a quoted string, not that it asserts an utterance that never happened); partial for the destructive half (`#unguarded-destructive` ⊂ opt-in `security`).
- **LLM-Judge value-add hypothesis:** opt-in dimension flagging downstream-harmful / belief-spoofing instructions. **Rec:** keep destructive-command detection in opt-in `security`, but add a lightweight *default binary gate* ("contains shell/config-mutating command") that escalates — so a default judge run does not miss the corpus's highest-blast-radius failure (skill 09).

## LLM-Judge Dimensions — Emergent (Day 3 PM)

**[Advisory — REVISED 2026-05-22 per Re-Review Delta. Binary criteria per ADR-0002. Franz confirms/edits before any judge build. The locked Decision below is unchanged; these are the post-delta candidate dims.]**

**Gating invariant (prerequisite for ALL dims, promoted from skill 08):** the judge runs only on artifacts **above a linter-completeness floor** and awards no points where the linter already scores ~0. Without this gate the judge fabricates semantic findings on stubs (failure-mode-first doctrine). This operationalizes the locked "Universal design rule" as a hard precondition.

Candidate beyond-linter dimensions (each binary pass/fail + critique):

1. **`verifiable_success`** (Cluster B) · **rock-solid, strongest dim**: PASS if a triggered agent has a concrete checkable way to know it succeeded; FAIL if success rests on unverifiable adjectives or unsourced precise-looking numbers. Members 01/02/03/05/07.
2. **`assumption_completeness`** (Cluster C) · **solid**: PASS if prerequisites/tools/environment are stated with a fallback; FAIL if the skill silently assumes context a fresh agent won't have. *Scope to the unstated-assumption core, disjoint from `composability`'s dependency-declaration.*
3. **`capability_fidelity`** (Cluster A) · ⚠ **probationary/thin**: PASS if a *formally-clean* skill's description matches what the body delivers; FAIL only when it looks complete but doesn't implement its claimed capability (empty-body/missing-procedure excluded → linter). Sole clean anchor (03); needs counter-samples.
4. **`self_consistency_proportionality`** (Cluster D, NOVEL) · ⚠ **low-confidence/archetype-bound**: PASS if the skill obeys the standards it preaches and scales ceremony to task complexity; FAIL if it contradicts its own philosophy or overconstrains trivial cases. Distinguishing ingredient = reflexivity; only fires on guideline/process skills. Validate before trusting; may be a sub-flavor of B.
5. **`harmful_downstream_instruction`** (Cluster F, opt-in — NEW 2026-05-22) · candidate: PASS if the skill does not instruct belief-spoofing / unsubstantiated-padding / unguarded destructive actions; FAIL otherwise. Recovers the orthogonal axis `#fabricated-context` exposed (no home in dims 1–4). Pair with a default "contains shell/config-mutating command" gate that escalates to `security`.

Cross-check vs 6-agent research priors: **A/B/C independently confirm hypotheses H3/H1/H2** (blind coder never saw them); **H4 (disambiguation) merged into Cluster E** (hedged for linter overlap); **Cluster D emerged from the data alone** — criteria drift, the data generating signal the priors missed. ≥3 distinct beyond-linter clusters with margin → **Kill-Gate 1 trends PASS (advisory)**.

(Target: 2-4 dimensions. If <2 emerge with positive value-add, **KILL-GATE 1 fires** — AI-Eval pillar deferred to v8.1, sprint shrinks to lib-api + auto-loop + corpus benchmark only.)

(Target: 2-4 dimensions. If <2 emerge with positive value-add, **KILL-GATE 1 fires** — AI-Eval pillar deferred to v8.1, sprint shrinks to lib-api + auto-loop + corpus benchmark only.)

## Sub-Reviewer Verdict (Day 3 EOD)

### Interim same-family review (Claude, advisory — does NOT satisfy §11 cross-family requirement)

_Codex/GPT-5 cross-family run was blocked by macOS (codex binary flagged as malware → SIGKILL). This interim Claude adversarial pass is a stopgap; the formal gate still needs a cross-family verdict (Franz running GPT-5/Gemini manually)._

- **Verdict:** PASS, conditional — narrower than the advisory draft implies.
- **Concrete elements rejected:** (1) **Cluster E / trigger-routing as a standalone dimension** — substantially duplicates deterministic `triggers`; the only novel (behavioral-routing) sliver isn't operationalizable without running the model → drop or defer. (2) **Membership inflation in Cluster A** — skills 08 (fully) and 10 (~70%) are linter-caught; counting them overstates A. Genuine beyond-linter core of A is essentially skill 03 only.
- **Clusters at risk of duplicating linter:** A `#missing-procedure` ⊂ `structure`; C `#brittle-handoff`/dependency ⊂ partial `composability` (declares-dependency regex) — beyond-linter only the *unstated assumption* + *missing fallback*; danger theme ⊂ opt-in `security`; E ⊂ `triggers`.
- **Dimension robustness:** `verifiable_success` (B) unassailable, 5 members. `assumption_completeness` (C) strong if scoped disjoint from `composability`. `capability_fidelity` (A) thin — must be narrowed to "body structurally present but claim not delivered." `self_consistency_proportionality` (D, novel) genuinely beyond-linter BUT only appears in the 3 procedural skills → **generalizability unproven, possibly archetype-bound**; needs procedural + non-procedural counter-samples.
- **Honesty calibration:** Nemp-memory "fully linter-caught, don't run judge" = correct. Skill 10/GAP is mostly linter-caught — a weak specimen (draft half-admits; reviewer is harsher).
- **Net:** after stripping weak/linter-redundant parts → B + C rock-solid distinct, D wobblier third. Meets "≥3 distinct beyond-linter" with conditions: drop E, narrow A, shore up D.

### Cross-family verdict (§11 — GPT-5, run manually by maintainer 2026-05-22)

- **Taxonomy is beyond linter coverage:** **PASS**, narrower scope (PASS does not apply to all clusters unchanged).
- **Cross-family model used:** GPT-5 (manual maintainer run; cross-family vs Claude-produced taxonomy).
- **Concrete elements it would reject:** (1) **Cluster E / trigger-routing as a standalone judge dimension** — dangerously near deterministic `triggers`; keep ONLY the narrow part (simulate realistic near-miss scenarios, check semantic routing); `#no-trigger` / over-broad-description / missing trigger-metadata are linter-near. (2) **`#missing-procedure` inside Cluster A must NOT be treated as semantic** — empty body / no structure / no usable steps is structure/quality linter territory; it becomes semantic only when the skill looks formally clean but does not deliver its claimed capability.
- **Clusters at risk of duplicating linter:** A contaminated by `#missing-procedure`/`#no-body` (structural); E highest dup risk with `triggers`; danger theme (`#unguarded-destructive`) → belongs in opt-in `security` if active; GAP/skill 10 mostly linter-redundant (no frontmatter, no trigger, hypertrophy) — semantic residue only "reference-code dump masquerading as agentic instructions"; Nemp-memory/skill 08 "fully linter-caught, don't run judge" essentially correct.
- **4 draft dims regex-uncatchable?** `capability_fidelity` yes *once cleaned* (filter out empty-body/missing-procedure cases); `verifiable_success` yes; `assumption_completeness` mostly yes (some relative-path-existence checks could be linter-assisted, core stays semantic); `self_consistency_proportionality` yes.

### Convergence note

The cross-family (GPT-5) and same-family interim (Claude) reviews **independently agreed** on every material point: PASS-conditional, reject/restrict Cluster E, exclude A's `#missing-procedure` from the semantic core, D is genuine, skill 08 correctly linter-caught, skill 10 over-sold semantically. Two model families converging on the same verdict + same conditions is the §11 anti-self-preference signal working as intended.

## Re-Review Delta (2026-05-22 — 10-Council Pass)

> **Layer note (per maintainer instruction):** This block records what a fresh 10-council deep pass (1 council/skill, lenses: AI-eval · auditor/pentester · architect · simplify · skill-creator) found *after* the original open-coding and the locked Decision below. It is **advisory and additive — it does NOT overwrite the locked Kill-Gate-1 = PASS.** Franz adjudicates which deltas to absorb (re-grade pass, ADR-0002 §5). Each council verified file-existence and cited exact phrases.

### A. Factual corrections (overturned draft premises)

These matter because parts of the locked taxonomy rest on them:

1. **Skill 01 (webapp-testing):** `scripts/with_server.py` IS present and matches the SKILL examples — the draft's "script absent/unverified, no fallback" was overstated. The real precondition is the *browser-binary install* (`playwright install chromium`), never mentioned. New finding `#env-coupled` (hardcoded `/mnt/user-data/outputs/` sandbox path).
2. **Skill 04 (internal-comms):** all four `examples/*.md` files ARE present and load-bearing — "if absent the skill produces nothing / unjudgeable in isolation" was factually wrong. `#externalized-content` reframed as a **judge-harness meta-property** (load referenced files before judging), not a defect; the genuine Cluster-C content is `#owner-coupled`.
3. **Skill 07 (systematic-debugging):** `root-cause-tracing.md`, `defense-in-depth.md`, `condition-based-waiting.md` ALL exist in-dir — the draft's `#unstated-precondition` / strong `#brittle-handoff` was wrong for v5.1.0 (downgraded to hedged). Skill 07's metric/absolutism findings (B/D) stand.
4. **Skill 03 (brand-guidelines):** confirmed only `SKILL.md` + `LICENSE.txt` ship (no python-pptx helper) — the capability-overclaim premise holds.

### B. Taxonomy divergences (advisory — do NOT alter the locked Decision)

1. **Cluster A (`capability_fidelity`) is even thinner than the locked text admits.** With skill 01's mismatch demoted to "mild" and skill 04 reframed, **brand-guidelines (03) is the sole clean anchor**, and its beyond-linter status hinges entirely on *leading with `#capability-overclaim` over `#missing-procedure`* — if filed under the latter it collapses into linter territory. A one-skill cluster is fragile. **Rec:** secure a procedural **and** a non-procedural counter-sample before trusting A's metrics.
2. **Cluster D (`self_consistency_proportionality`) confirmed REAL but ARCHETYPE-BOUND.** Two independent councils (05, 07) converged: D's distinguishing ingredient is **reflexivity** — a skill that states a normative standard its own body violates — which is structurally available only in guideline/process/rubric skills. Outside that archetype D degenerates into B (vagueness) or A (proportionality). karpathy (05) is near best-case and *still* mostly reduces to B + `#scope-boundary-undefined`. This **strengthens** the locked decision's existing "low-confidence/archetype-bound" flag rather than overturning it; consider whether D is a sub-flavor of B.
3. **`#fabricated-context` (skill 02) has no clean home among the 4 judge dims.** It is an *asserted false fact* (conversation-state spoofing), not a missing one (≠ assumption-completeness) and not a capability gap. The held-back theme **"skill instructs harmful/biasing downstream behavior"** (skills 02 `#fabricated-context`/`#instructed-redundancy`, 09 `#unguarded-destructive`) is orthogonal and regex-invisible. **Rec:** promote it to its own opt-in dimension (or sub-facet of D) — this is a genuine gap in the locked 4-dim scope.
4. **`#unguarded-destructive` routing (skill 09).** The locked decision sends it to opt-in `security` only. Skill 09 is the **canonical case where opt-in-only would miss the highest-blast-radius failure in the corpus** (`echo b > /proc/sysrq-trigger` = unsynced reboot). **Rec (compromise):** keep it opt-in, but add a lightweight **default binary gate** ("contains shell/config-mutating command") that *escalates* to the security dim — captures asymmetric harm without a full default dim or double-counting `#missing-failure-path`.
5. **Gating invariant (skill 08).** Formalize as an explicit ADR/taxonomy rule: **the judge runs only on artifacts above a linter-completeness floor and awards no points where the linter already scores ~0.** This operationalizes the locked "Universal design rule" as a hard precondition and prevents the judge from fabricating semantic findings on stubs (failure-mode-first doctrine).
6. **New tag `#env-coupled`** (skill 01) — environment/sandbox-coupled hardcoded paths; candidate sub-facet of Cluster C, distinct from `#owner-coupled`.

### C. Net effect on Kill-Gate-1

**None forced.** **B (`verifiable_success`) remains rock-solid** — arguably strengthened (members 01, 02, 03, 05, 07). **C (`assumption_completeness`) remains solid** but the file-existence corrections (04, 07) shift its weight from the *missing-fallback* half toward the *unstated-assumption* half — scope it accordingly. **A and D are both thinner/narrower than the locked prose** and should be treated as **probationary pending counter-samples**. The strongest new recommendation is to **recover the orthogonal axis exposed by `#fabricated-context`** (B.3) — the current 4 dims do not cover deliberately-biasing downstream instructions. Kill-Gate-1 = PASS still holds on B + C; A/D ride along with explicit caveats.

## End Consolidation — Hamel-Lens Evaluation & Optimal Specimen Portfolio (2026-05-22)

All 10 skills re-coded by the maintainer (Franz, labeller of record); Claude pre-staged + gave a third opinion (per-skill log above). **This consolidation is the authoritative Phase-0 result and supersedes the advisory clustering, judge-dimension list, and "Decision" recorded earlier in this document, which are retained as the dated historical record.**

### Per-skill Hamel evaluation (value to eval-building, not just "is it a bad skill")

Hamel's question is never "is this skill good?" — it is "what does this specimen teach the eval, and can I measure it?" Graded on that:

| # | Skill · band | Hamel role for the eval | Anchors | Disposition | Tier |
|---|---|---|---|---|---|
| 02 | canvas-design · low | Richest beyond-linter specimen; the `#fabricated-context` orthogonal axis | **F** + B | **Feature** | 1 (top) |
| 03 | brand-guidelines · low | "Looks formally clean, doesn't deliver claimed capability" — the *sole* clean A anchor | **A** | **Feature** + flags A-thin gap | 1 |
| 07 | systematic-debugging · mid | `#confident-but-unsourced` (fabricated metrics) — distinct, high-agreement B flavor | **B** | Keep | 1 |
| 04 | internal-comms · low | `#owner-coupled` exemplar + the "don't assume absence" lesson | **C** | Keep | 1 |
| 01 | webapp-testing · high | High-composite-but-flawed: linter passes, judge must catch the browser-binary precondition | **C** | Keep (clean-baseline) | 1 |
| 09 | algorithms · probe | `#unguarded-destructive` (safety) → justifies the deterministic detector; representativeness | **F** | Keep | 1–2 |
| 05 | karpathy-guidelines · mid | The negative result that *shrank* the taxonomy (D→B, criteria-drift evidence, Shankar) | B/`#reflexivity` | Keep (license-gated) | 2 |
| 08 | Nemp-memory · probe | Stub floor control — confirms the gating invariant (judge must NOT fire) | — (control) | Keep (control) | 2 |
| 10 | GAP-Design-System · probe | Hypertrophy floor control; net-new judge signal ≈ 0 | — (control) | Keep (control, low marginal) | 3 |
| 06 | brainstorming · mid | Findings mostly **de-scored** post-decision (proportionality → annotation); redundant with 07/01 | `#process-overhead` annot. | Most droppable as anchor | 3 |

### Final scored judge scope (human-ratified)

**3 core + 1 opt-in + deterministic helpers:**
1. `verifiable_success` (B) — rock-solid; incl. `#reflexivity` sub-tag. Members 01/02/03/05/07.
2. `assumption_completeness` (C) — solid; scoped to the *unstated-assumption* core, disjoint from `composability`. Members 01/03/04/06. (`#externalized-content` = harness meta-property, not a member.)
3. `capability_fidelity` (A) — ⚠ probationary; sole clean anchor 03; lead with `#capability-overclaim`. **Gated on counter-samples.**
4. `harmful_downstream_instruction` (F) — opt-in; 02 + 09.
- **Deterministic (not LLM):** destructive-command detector → human-review flag (09); mixed-script frontmatter check (10); the **gating invariant** (judge runs only above a linter-completeness floor).
- **Retained annotation, NOT scored:** `#process-overhead` (proportionality/absolutism, 06/07) — Hamel 4-bar fail; revisit only on cross-archetype recurrence with measurable κ.

### Calibration coverage matrix — and the holes Hamel would flag

| Dim | Positive (fail) anchors among the 10 | Clean PASS control? | Verdict |
|---|---|---|---|
| B | 01, 02, 03, 05, 07 (5) | ❌ none | Well-anchored on fails; **cannot measure TNR** |
| C | 01, 03, 04, 06 (4) | ❌ none | Solid on fails; same TNR gap |
| A | **03 only** | ❌ none | **Cannot align/validate** — single anchor |
| F | 02, 09 (2, opt-in) | n/a | Enough for opt-in + detector; LLM-score deferred until n grows |

### Optimal specimen portfolio for Schliff (the answer to "die optimalen skills")

**Optimal minimal anchor set (keep + feature):** `02` (F+B), `03` (A), `07` (B/false-precision), `04` (C/owner-coupled), `01` (C/clean-high-band), `09` (F/safety). **Controls:** `08` (stub floor), `10` (hypertrophy floor). **Secondary:** `05` (B/reflexivity, license-gated). **Most droppable as a calibration anchor:** `06` (de-scored, redundant) — retain only as a `#process-overhead` annotation example.

**The three corpus gaps that matter more than any single skill (Hamel):**
1. **A is a one-specimen anchor** → `capability_fidelity` cannot be aligned/validated. **Add ≥2 more A specimens (one procedural, one non-procedural)** before A scores anything.
2. **The set is fail-heavy with zero clean PASS controls** → the judge's **TNR / false-positive rate is unmeasurable**. **Add known-GOOD specimens per scored dim** (reserve candidates: `mcp-builder` 79.1, `claude-api` 68.4 K1-positive, `doc-coauthoring` K4-positive) as negative controls.
3. **Representativeness of the *scored* dims:** the probes (08/09/10) are mostly *floor/control*, not mid-band messy production skills that fail B/C/A. Schliff's users live at mean composite 61.7 — **add mid-band community probes that exhibit B/C/A failures**, not just stubs and dumps.

### Kill-Gate-1 (against the human clusters)

**PASS — narrower than the original advisory 4-dim scope.** ≥3 distinct beyond-linter scored dims survive (B rock-solid, C solid, A probationary) + 1 opt-in (F). Dropped vs advisory: Cluster D (collapsed/dispositioned), Cluster E (duplicates `triggers`), proportionality (de-scored to annotation). AI-Eval pillar proceeds on this disciplined human-ratified scope — with the explicit precondition that A-counter-samples and PASS-controls are added before A and the judge's false-positive rate are trusted.

### Provenance (honest Day-1 record)

Phase-0 open-coding ran as a Claude 10-council **third-opinion advisory**, then was **re-coded and ratified skill-by-skill by Franz (labeller of record)** on 2026-05-22 — consistent with ADR-0001 Alt-3 (human-ratified, not subagent-of-record) and ADR-0002 (Franz solo labeller; subagents pre-stage, do not grade). The non-delegable binary+critique calibration labels (ADR-0002 §3, Day-4+) remain a separate pending artifact. Source SKILL.md snapshotted at `benchmarks/corpus/v1/phase0-snapshot/` (sha256 in `MANIFEST.md`).

## Decision (Day 3 EOD)

> **Superseded 2026-05-22** by the End Consolidation above (human re-coding). Retained verbatim as the dated advisory record.

**KILL-GATE 1: PASS (conditional, disciplined scope)** — confirmed by cross-family GPT-5 sub-reviewer (+ corroborating Claude interim). AI-Eval pillar proceeds to Phase 1.

**Locked Phase-1 judge scope — 4 dimensions:**
1. `capability_fidelity` — *narrowed:* only "skill looks formally clean but doesn't deliver its claimed capability"; empty-body/missing-procedure cases are excluded (linter territory).
2. `verifiable_success` — unrestricted; strongest dim.
3. `assumption_completeness` — scoped disjoint from `composability` (judge the *unstated* assumption + *missing fallback*, not whether a dependency is declared).
4. `self_consistency_proportionality` — kept, but **flagged low-confidence/possibly archetype-bound** (only surfaced in procedural skills); validate against procedural + non-procedural samples before trusting its metrics.

**Dropped:** Cluster E / trigger-routing as a standalone dim (duplicates `triggers`; revisit only as a narrow behavioral near-miss routing simulation, post-v8.0). Danger theme → route to opt-in `security`, not a general judge dim.

**Universal design rule (both reviewers):** the judge awards **no points for cases the deterministic linter already clearly catches** — every dimension must be gated to fire only on beyond-linter (semantically-clean-but-flawed) inputs. This is the operational guarantee that the LLM-judge is additive, not duplicative.

**Caveats carried forward:** this taxonomy is built on Claude's ADVISORY open-coding, not Franz's human labels. The Day-4+ calibration holdout (ADR-0002) still requires Franz's binary+critique labels as ground truth — that is the non-delegable anchor. Re-grade pass absorbs criteria drift.

## References

- Husain "LLM Evals FAQ" — error-analysis workflow https://hamel.dev/blog/posts/evals-faq/
- Husain "LLM-as-Judge" — 7-step alignment workflow https://hamel.dev/blog/posts/llm-judge/
- Shankar et al. EvalGen UIST 2024 — criteria-drift, open-coding pattern https://arxiv.org/abs/2404.12272
- ADR-0001 — failure-mode-first scoping (+ Day-1 addendum)
- ADR-0002 — calibration-set protocol (+ Day-1 addendum)
- Master Spec §3 — failure-mode-first pivot
- Master Spec §11 — Kill-Gate 1 definition
