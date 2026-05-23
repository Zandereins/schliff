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
| 01 webapp-testing | phase0 01 | fail-anchor | familiar | "find a customized solution is *absolutely necessary*" — uncheckable threshold | | |
| 02 canvas-design | phase0 02 | fail-anchor | familiar | "museum quality / looks like it took countless hours" as the operative criteria | | |
| 03 brand-guidelines | phase0 03 | fail-anchor | familiar | "smart color selection based on background" — no contrast rule defined | | |
| 05 karpathy-guidelines | phase0 05 | fail-anchor (`#reflexivity`) | familiar | §4 demands verifiable criteria yet §2 "would a senior engineer say this is overcomplicated?" / "200→50" are unverifiable | | |
| 07 systematic-debugging | phase0 07 | fail-anchor | familiar | "95% vs 40%", "15-30 min vs 2-3 hrs" — precise numbers sourced only to "debugging sessions" | | |
| c3 doc-coauthoring | ./c3 | **PASS-control** | familiar | Stage-3 "Reader Testing with a fresh Claude" = concrete checkable success loop | | |

## C — `assumption_completeness`
Are prerequisites/tools/env/prior-state stated (with a fallback), or silently assumed? *(Scope to the unstated-assumption core, disjoint from `composability`'s declares-a-dependency check.)*

| Specimen | Path | Intent | Tier | Evidence (pre-extracted) | PASS/FAIL | Critique |
|---|---|---|---|---|---|---|
| 01 webapp-testing | phase0 01 | fail-anchor | familiar | assumes Playwright + browser binaries; `playwright install chromium` never stated, no fallback | | |
| 03 brand-guidelines | phase0 03 | fail-anchor | familiar | "Applied via python-pptx" silently scopes to `.pptx` while claiming "any artifact" | | |
| 04 internal-comms | phase0 04 | fail-anchor (`#owner-coupled`) | familiar | first-person "formats **my company** likes" — absent owner's prefs as universal | | |
| 06 brainstorming | phase0 06 | fail-anchor | familiar | "terminal state is invoking writing-plans" assumes sibling skill installed, no degraded path | | |
| c5 voice-skill | ./c5 | fail (mid-band) | probe | assumes external pip pkg + Vapi account + purchased phone number (~$2/mo) as prior state | | |
| c6 raindrop | ./c6 | fail (mid-band) | probe | uses `scripts/raindrop.sh`, existence never stated, no fallback; assumes `~/.zshrc.local` | | |
| c2 claude-api | ./c2 | **PASS-control** | familiar | explicitly surfaces+gates assumptions ("scan for non-Anthropic markers… stop"; "Never guess… WebFetch the repo") | | |

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
