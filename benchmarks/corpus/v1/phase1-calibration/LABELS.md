# Phase-1 Calibration Labels — Maintainer Label Sheet (binary + critique)

**Labeller of record: Franz (ADR-0002 §3 — non-delegable).** Claude pre-staged the specimens +
pre-extracted the evidence; Claude did NOT pre-fill any verdict. Label each cell **fresh**.

## How to label
- One **binary PASS / FAIL** per (specimen × dimension) + a **one-line critique** (the *why* —
  this becomes a few-shot anchor for the judge prompt). No Likert, no "it depends" (an
  "it depends" means a missing dimension — note it).
- The **Intent** column is selection intent, not a hint. If an intended-PASS-control reads FAIL
  (or a fail-anchor reads PASS), label what you see and add `⚠ intent-mismatch` — that is a
  *finding* about the corpus, not an error.
- **Tier** (`familiar` / `probe`) is carried so Phase-P3 reliability can report TPR/TNR/κ
  per tier (ADR-0002 Day-1 addendum) — never pool a familiar-high / probe-low gap.
- **Gating invariant:** do NOT run the judge on artifacts the deterministic linter already kills
  (stub 08 Nemp-memory, dump 10 GAP). They are floor controls, excluded from these dim sheets.

Snapshot paths: phase0 fails → `../phase0-snapshot/NN-name.SKILL.md`; new → `./cN-name.SKILL.md`.

---

## B — `verifiable_success`
Can a triggered agent concretely verify it succeeded, or is success unverifiable adjectives / unsourced numbers?

| Specimen | Path | Intent | Tier | Evidence (pre-extracted) | PASS/FAIL | Critique |
|---|---|---|---|---|---|---|
| 01 webapp-testing | phase0 01 | fail-anchor | familiar | "find a customized solution is *absolutely necessary*" — uncheckable threshold | **FAIL** | No checkable success signal; "absolutely necessary" is an unverifiable judgment gate — the agent can't know when the bar is met. |
| 02 canvas-design | phase0 02 | fail-anchor | familiar | "museum quality / looks like it took countless hours" as the operative criteria | **FAIL** | Success defined entirely by aesthetic vibes; nothing a downstream model can self-verify. |
| 03 brand-guidelines | phase0 03 | fail-anchor → **PASS** (Franz override) | familiar | "smart color selection based on background" — no contrast rule defined | **PASS** | Override of scribe's FAIL-mild: the lone vague phrase is minor; brand-guidelines' real failure is capability_fidelity (A), not success-criteria. Keeps B's boundary tight — B is NOT a catch-all for any vagueness. (Franz to refine wording.) |
| 05 karpathy-guidelines | phase0 05 | fail-anchor (`#reflexivity`) | familiar | §4 demands verifiable criteria yet §2 "would a senior engineer say this is overcomplicated?" / "200→50" are unverifiable | **FAIL** | Reflexive: preaches verifiable success criteria while its own tests ("senior engineer", "200→50") are themselves unverifiable. |
| 07 systematic-debugging | phase0 07 | fail-anchor | familiar | "95% vs 40%", "15-30 min vs 2-3 hrs" — precise numbers sourced only to "debugging sessions" | **FAIL** | Unsourced false precision presented as fact; not a checkable success signal (and the model relays it downstream stripped of the hedge). |
| c3 doc-coauthoring | ./c3 | **PASS-control** | familiar | Stage-3 "Reader Testing with a fresh Claude" = concrete checkable success loop | **PASS** | Confirmed PASS-control: gives a concrete, runnable success check (fresh-Claude reader test) the agent can actually execute. |

## C — `assumption_completeness` · criterion LOCKED 2026-05-26 (5-expert + 3-member closing council)
**Criterion (DISCLOSURE, not provisionability):** FAIL iff the documented happy path relies on a consequential precondition (external package/binary, account, credential, paid service, runtime) that is NOT disclosed in the skill text at/before first use. Named/paid/external-but-disclosed = PASS. Harness-contract tools (file-I/O, Bash, Read, Write) need no disclosure. Provisionability/runtime-success → B's concern; declared sibling-skill handoffs → composability's concern.

| Specimen | Path | Intent | Tier | Evidence | PASS/FAIL | Critique |
|---|---|---|---|---|---|---|
| 01 webapp-testing | phase0 01 | fail-anchor | familiar | Playwright + browser binary (`playwright install chromium`) never stated; happy path runs `p.chromium.launch()` | **FAIL** | Consequential runtime precondition undisclosed (silence); fresh-agent happy path throws with no stated fallback. |
| c6 raindrop | ./c6 | fail-anchor | probe | instructs `./scripts/raindrop.sh` as primary interface; VERIFIED the script does NOT ship (only SKILL.md + metadata.json) | **FAIL** | Relies on a script neither shipped nor disclosed as something to obtain. (Distinct from c5: there the install IS stated.) |
| c2 claude-api | ./c2 | PASS-control | familiar | WebFetch surfaced+gated as fallback; API key downstream-of-artifact; bundled reference files | **PASS** | Consequential deps disclosed/gated; WebFetch gated-with-fallback, key downstream of the produced artifact, not a happy-path precondition. PASS-control holds. |
| 03 brand-guidelines | phase0 03 | (was fail-anchor) | familiar | font dep gated w/ fallback ("No font installation required" / "falls back to Arial/Georgia"); python-pptx ambient in sandbox | **PASS** | No undisclosed precondition. The ".pptx vs any artifact" gap is an A-overclaim (capability_fidelity), not C. |
| 04 internal-comms | phase0 04 | (was fail-anchor) | familiar | all 4 `examples/*.md` present + explicit "ask for clarification" fallback | **PASS** | Self-contained; deps bundled + disclosed. Owner-coupled wording is portability/scope, not an undisclosed precondition. |
| ~~06 brainstorming~~ | phase0 06 | **EXCLUDED from v0** | familiar | mandatory `writing-plans` sibling-skill handoff | — | EXCLUDED → composability turf (declared sibling-skill edge), disjoint from C. |
| ~~c5 voice-skill~~ | ./c5 | **EXCLUDED from v0** | probe | Vapi deps disclosed in `## Requirements`; `pip install claude-code-voice` (step-1) not in Requirements | — | EXCLUDED → criterion-pinning fixture. Label split 2:1 (Evals/Harness PASS — install is step-1-disclosed, unresolvability=B; Skeptic FAIL — pkg absent from Requirements). Resolve in rubric annex, not v0. |

**v0 C-anchors (clean): 01 FAIL · c6 FAIL · c2 PASS · 03 PASS · 04 PASS** (2F / 3P). ⚠ **Measurement guardrail (council-certified):** only 2 clean FAILs → **NO κ/TNR reported until Batch-2 adds ≥4 more FAILs**; until then judge-vs-human per-item agreement is a directional smoke test only.

## A — `capability_fidelity` ⚠ PROBATIONARY
Formally-clean skill whose description/Features claim a capability the body does NOT deliver. *(Lead with `#capability-overclaim`; empty-body/missing-procedure cases are linter territory, NOT this dim.)*

| Specimen | Path | Intent | Tier | Evidence (pre-extracted) | PASS/FAIL | Critique |
|---|---|---|---|---|---|---|
| 03 brand-guidelines | phase0 03 | fail-anchor (non-proc) | familiar | "Applies Poppins… Automatically falls back… Applied via python-pptx" — narrates a tool's internals; ships only SKILL.md + LICENSE | | |
| c4 theme-factory | ./c4 | fail-anchor (PROCEDURAL) | familiar | "can apply to any artifact" / "Apply the theme" — no apply mechanism (ships theme specs + PDF, no code) | | |
| c5 voice-skill | ./c5 | fail (mid-band community) | probe | "Claude can Read your files / Search your code… does everything automatically" — runtime caps, zero in-body mechanism (tool README) | | |
| c1 mcp-builder | ./c1 | **PASS-control** | familiar | procedural build-guide that delivers the claimed build steps in-body | | |

## F — `harmful_downstream_instruction` (OPT-IN — LLM-score DEFERRED until n grows)
Skill instructs belief-spoofing / unsubstantiated padding / unguarded destructive action. *Recorded for completeness; do NOT score as an LLM dim yet (n too small to align TPR/TNR). Skill 09's destructive command is handled by the deterministic detector → human-flag.*

| Specimen | Path | Intent | Tier | Evidence (pre-extracted) | PASS/FAIL | Critique |
|---|---|---|---|---|---|---|
| 02 canvas-design | phase0 02 | fail-anchor | familiar | fabricated user quote "the user ALREADY said 'It isn't perfect enough'" fires unconditional refine loop (belief-spoofing) | | |
| 09 algorithms | phase0 09 | fail-anchor | probe | `echo b > /proc/sysrq-trigger` = unsynced reboot, zero guard (also caught by deterministic detector) | | |

---

## After labeling
1. Drift check / re-grade pass (ADR-0002 §5) once Judge v0 is wired — absorb criteria drift.
2. Convert this sheet → JSONL for the judge harness (`{specimen, dim, label, critique, tier}`).
3. Grow Batch 2: more PASS controls (real TNR), 2nd non-procedural A specimen, more mid-band probes.

## v0 anchor exclusions + judge freeze (2026-05-27)

Three anchors marked `"status": "excluded"` in `labels-v0.jsonl` (the harness skips them). Rationale = the **text-intrinsic judge boundary** (council 2026-05-27): the LLM judge sees only the SKILL.md text; reality facts (does a file ship? is a package ambient?) belong elsewhere.

- **c6-raindrop · C** → reassigned to the deterministic layer. Its FAIL hinges on `scripts/raindrop.sh` not shipping (a filesystem fact), not on text disclosure. Future: a `guards.py` missing-referenced-file check.
- **03-brand · C** → descoped. Its PASS depends on python-pptx being ambient in the sandbox (a runtime fact); neither a text-judge nor a static linter can settle ambient-availability from static inputs. Out of v0 scope.
- **03-brand · B** → dimension-confounded. Its PASS only holds because the lone vague phrase's real defect routes to dim A (capability_fidelity), not yet a scored dim. Re-admit when A is stood up.

**Active set after exclusions: B = 4 FAIL / 1 PASS, C = 1 FAIL / 2 PASS** — deliberately NOT a calibration set, but the clean text-intrinsic seed for Batch-2.

**JUDGE FROZEN (v8.1 gate).** Phase-1 ran the judge 4× live (2026-05-27, real key): directional agreement plateaued at 7/11; every rubric edit swapped one miss for another → diagnosed as a sample-size/anchor problem (n=6/dim), not a prompt problem (12-agent council). Prompt-tuning is halted; rubric reverted to the locked baseline; calibration default dropped to N=1 (votes were 5/5 unanimous → N>1 bought nothing). The judge resumes ONLY when distribution of the deterministic linter yields **≥3 real users AND ≥1 names a concrete quality problem the deterministic score missed**. Then grow anchors to ≥12–15/class/dim (real, not synthetic — synthetic SKILL.md as ground truth is circular) and report TPR/TNR (not raw agreement) on a train/test split. The `#reflexivity` rubric clause (validated on 05-karpathy but it broke the c3-doc PASS-control) is deferred until enough PASS-controls exist to add it without collateral.
