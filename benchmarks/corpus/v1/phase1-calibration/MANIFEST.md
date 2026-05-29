# Phase-1 Calibration Additions — Manifest

Durable snapshot (captured **2026-05-23**) of the 6 specimens added to close the three
Hamel-flagged corpus gaps before judge-build (see `docs/research/2026-04-28-skill-failure-modes.md`
→ "End Consolidation" → "the three corpus gaps"). Companion to `../phase0-snapshot/` (the 10
open-coded sources). Only the `SKILL.md` unit is snapshotted.

**Role/intent below is SELECTION INTENT, not a label.** The maintainer (Franz, sole labeller of
record, ADR-0002) assigns the actual binary PASS/FAIL + critique in `LABELS.md`. If an
intended-PASS-control labels FAIL (or vice-versa), that is a *finding* about the selection, not an
error — record it.

**Composite scale: full-denominator (post-PR #41, 2026-05-26)** — no-eval-suite skills ceiling ≈ coverage×100, so all 6 cluster ~27–33. The composite is now largely a coverage/structure signal and does **not** separate the beyond-linter quality the judge targets (it cannot tell c1 the-good-build-guide from c4 the-hollow-claim) — precisely why the LLM-judge dims exist. Old-scale values (pre-#41) are in git history of commit 45e575a.

| File | Origin | sha256 | composite (full-denom) | Intent | Gap | License |
|---|---|---|---|---|---|---|
| `c1-mcp-builder.SKILL.md` | anthropics/skills `mcp-builder` (pin 5128e186) | `0f4592dcb53c…` | 33.3 | PASS-control for **A** (proc build-guide that delivers its claim) | b | Apache-2.0 |
| `c2-claude-api.SKILL.md` | anthropics/skills `claude-api` | `48ac608cbd34…` | 28.8 | PASS-control for **C** (explicitly gates assumptions) | b | Apache-2.0 |
| `c3-doc-coauthoring.SKILL.md` | anthropics/skills `doc-coauthoring` | `2e47d78846fa…` | 26.8 | PASS-control for **B** (reader-test success loop) | b | Apache-2.0 |
| `c4-theme-factory.SKILL.md` | anthropics/skills `theme-factory` | `c35893e221e2…` | 28.3 | **A**-fail anchor, PROCEDURAL (hollow "apply theme" claim, no mechanism) | a | Apache-2.0 |
| `c5-voice-skill.SKILL.md` | community `abracadabra50/claude-code-voice-skill` | `fc65992a57e1…` | 28.2 | **A**+**C**-fail, mid-band community (tool-README claims runtime caps; assumes external pkg/account) | a + c | unspecified upstream |
| `c6-raindrop.SKILL.md` | community `majiayu000/claude-skill-registry` (raindrop) | `2120137a3c3e…` | 28.9 | **C**-fail, mid-band community (assumes `scripts/raindrop.sh` exists, no fallback) | c | unspecified upstream |

Full sha256 reproducible via `shasum -a 256 c*.SKILL.md`. Originals untouched.

## Coverage after these additions

| Dim | Fail anchors | PASS control | Status |
|---|---|---|---|
| B `verifiable_success` | 01,02,03,05,07 (phase0) | c3 doc-coauthoring | TPR+TN measurable to start |
| C `assumption_completeness` | 01,03,04,06 (phase0) + c5,c6 | c2 claude-api | TPR+TN measurable; +representativeness |
| A `capability_fidelity` (probationary) | 03 (phase0) + c4,c5 | c1 mcp-builder | 1→3 fail anchors (proc/non-proc/community) → alignable |
| F `harmful_downstream_instruction` (opt-in) | 02,09 (phase0) | — | LLM-score DEFERRED; deterministic detector for 09 |

**Honest caveat (ADR-0002 iterative-growth):** one PASS-control per dim is enough to START judge
v0 and get a TN signal — a statistically meaningful **TNR needs a follow-up batch** of PASS
controls (Batch 2). Deferred: 2nd non-procedural A specimen (web search), more PASS controls.
