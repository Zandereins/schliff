# Spec: AGENTS.md scoring profile

Status: IMPLEMENTED — TDD, 1238 tests green, ruff-clean, end-to-end verified (PR #67)
Date: 2026-06-25
Owner: Franz
Origin: moonshot strategy tournament — wave-rider bet ("agentsmd-lint: the deterministic CI quality gate for AGENTS.md"). The 4 open questions were resolved by an engine-backed subagent panel, then this spec was put through a double-sided adversarial review (5 specialists, every finding verified refute-by-default). The review caught a **critical inert-recipe bug** in the first draft (the frozenset-only edit shipped score 26.4 — worse than baseline); the implementation recipe below is the independently re-reproduced fix.

## Goal

Make schliff produce **defensible, AGENTS.md-appropriate scores** so the engine and the
GitHub Action become a credible quality gate for the cross-tool **AGENTS.md** standard
(Cursor / Codex / Copilot / Claude Code / Devin). Today schliff applied to AGENTS.md is an
*anti-billboard*: it tells well-formed files they are failing for SKILL-only reasons.

### Scope and NON-GOALS (review-hardened)

- **Non-goal — other formats:** do not change `SKILL.md` / `CLAUDE.md` / `.cursorrules` /
  `system_prompt` scoring. Byte-identical (golden gate).
- **Non-goal — correctness/safety (v1):** the v1 headline scores **form/structure + information
  density only**. It does **not** assess whether the documented commands are correct or safe.
  Verified: a deliberately dangerous but well-structured AGENTS.md (`curl … | sudo bash`,
  `git push --force origin main`, commit `.env`, `--no-verify`, self-merge) scores **90.0 / A**
  under this profile (security signal is `None` — `security.py` excludes code-block commands).
  Therefore README/Action copy MUST NOT imply a safety stamp. Real safety detection is
  Fast-follow scorer work.
- **Non-goal — content coverage (v1):** the headline does not verify that required operational
  sections (setup/build/test) are present. That is the Fast-follow operational-coverage dim.

## Context — the verified problem

AGENTS.md is **project context for coding agents** (setup, build/test commands, code style,
PR/commit rules, gotchas). It is *always-on* context, not a *reusable skill with triggers and
an eval suite*. But it is currently scored through the shared SKILL scorer registry.

Dogfood evidence — the real engine (v8.2.0) over the 30 real public AGENTS.md files in
`docs/launch/corpus/agents/` (all numbers reproduced in review):

```text
N=30   composite: mean 28.26, median 29.25, range 18.9–33.7
grade=None:            30/30   (every file)
>=1 null dimension:    30/30   (triggers, quality, edges — all null)
"add an eval suite" warning: 30/30
ceiling: 42% (full-denominator cap on the eval-gated dims)
```

Per-dimension distribution across the same 30 files (stdev = population, ddof=0):

| Dimension | n | mean | stdev | min | max | verdict for AGENTS.md |
|---|---|---|---|---|---|---|
| `structure` | 30 | 83.2 | 10.46 | 50 | 95 | **discriminates — keep** |
| `efficiency` | 30 | 64.6 | 17.07 | 25 | 95 | **discriminates — keep** (signal/noise ratio: rewards actionable lines, examples, bash command fences — not raw char/4) |
| `clarity` | 30 | 98.9 | 2.60 | 92 | 100 | saturated, corr -0.11 → **drop from headline** |
| `composability` | 30 | 29.7 | — | 20 | 50 | mis-fit SKILL semantics, corr ~0 → **drop from headline** |
| `triggers`/`quality`/`edges` | 0 | — | — | — | — | **inapplicable** (eval-suite-gated) → **drop from denominator** |

Root cause: `triggers`/`quality`/`edges` require an eval suite (a SKILL concept) and the
full-denominator composite keeps them in the denominator → permanent cap; `composability`
encodes SKILL invocable-unit semantics a project doc lacks; the warning hard-codes
`/schliff:init` + "add an eval suite", incoherent for an AGENTS.md author.

## Requirements

- **R1 — defensible spread.** A well-formed AGENTS.md lands in a defensible band (B/A); a sloppy
  one in C/D.
- **R2 — no SKILL-only output (headline AND fix-path).**
  - The headline composite must fold in **no eval-gated dim** and must emit **no eval-suite
    warning**. (The JSON `dimensions` / `dimension_status` side-signal block legitimately may
    still *report* triggers/quality/edges/composability/clarity — they are scored, just not in
    the headline. This is consistent with keeping the scorers running for `guards.py`.)
  - `suggest` / `evolve` must **not** emit SKILL-only fixes for `fmt == agents.md`. Verified
    today they do: `suggest` on a real AGENTS.md returns "Add YAML frontmatter (name/description)",
    "Create eval-suite.json with trigger test cases", "Add handoff points", "Add 'Use this skill
    when…'". These are the exact anti-billboard advice R2 forbids.
- **R3 — determinism preserved.** No LLM in the scoring path; reproducible.
- **R4 — no regression elsewhere.** The other four formats stay byte-identical.
- **R5 — locked.** A golden-score regression test pins the AGENTS.md corpus scores (including
  band boundaries) AND asserts no SKILL-only `suggest` output for agents.md.

## Technical decisions (RESOLVED + corrected)

### Dimension set & weights for `fmt == agents.md`

Headline composite = **`0.5 * structure + 0.5 * efficiency`**, renormalized over those two dims
only. Everything else is removed from the **denominator**: eval-gated `triggers`/`quality`/
`edges` (inapplicable), `clarity` (saturated, mean 98.87 / stdev 2.60 / corr -0.11), and
`composability` (mis-fit, corr ~0). `security`/`runtime` remain side signals. The per-dim
scorers for the dropped dims **still run** (guards + side-signal report intact); they leave the
headline denominator only.

50/50 over the two discriminating, distinct (inter-corr 0.718) axes; rejected the
efficiency-heavy 0.4/0.6 (marginally higher raw spread but hostage to the noisier efficiency
dim, stdev 17.07) and any clarity-weighted vector (saturation collapses files into one band).

Result over the 30-file corpus (population stdev): **mean 73.90, median 77.25, min 37.5,
max 95.0, stdev 12.74**.

### Token budget (Q2)

Keep `FORMAT_TOKEN_BUDGETS['agents.md'] = 3000`. It is **advisory-only**: it feeds the separate
`token_budget` JSON block in `cli.py`, NOT the efficiency dimension and NOT the composite —
changing it moves both by 0. 3000 lands in the empty gap between the 25-file cluster
(≤2079 tokens) and the 5-file tail (≥3219). Do not lower below 2079 / raise above 3219. The
budget/efficiency co-variation is coincidental — do not market it as a density proxy.

### Grade bands (Q3) — claim corrected

Reuse the **global** bands unchanged: S≥95, A≥85, B≥75, C≥65, D≥50, E≥35, F<35 (lower-bound
inclusive). `score_to_grade` is format-agnostic. The 50/50 composite spans 6 of 7 bands
(**S=2, A=2, B=12, C=7, D=6, E=1, F=0**) with monotone, face-valid ordering — no pathological
clustering, so agents-specific bands are not warranted.

**Corrected (review P3):** do NOT claim "a B means the same across all formats." It does not — a
SKILL.md `B` is gated on behavioral dims (triggers/quality/edges + composability/clarity); an
AGENTS.md `B` is gated on structure+efficiency only (10/12 corpus B-files have composability
≤31, i.e. content largely unmeasured). AGENTS.md grades are **form/structure-oriented**; band
equivalence must not be marketed until the operational-coverage dim lands.

### Calibration honesty (review M3)

The weights/drops were chosen by **spread maximization on N=30 with no ground-truth labels**
(no rubric/label file exists under `docs/launch/corpus/`). Ship the profile labeled
**provisional / uncalibrated**; the R5 golden test is a *reproducibility lock*, not a calibrated
cross-tool standard. Optional hardening: hand-label ~30 files on a 3-class rubric and report
per-class rank separation before any "standard" claim.

### Implementation surface — VERIFIED two-edit recipe

> **Both edits are required.** Either alone fails. Independently reproduced on `kudu` (structure
> 85, efficiency 84): frozenset-only (excl composability+clarity, default weights) → **26.4,
> capped 31%, warning present** (worse than baseline); + exclude eval-gated but default weights →
> 84.6 (the unintended **0.6/0.4** split, see below); + exclude eval-gated AND explicit 0.5/0.5 →
> **84.5, no warning** ✓.

1. **Weight table (PRIMARY).** `registry.py` `WEIGHT_PROFILES['agents.md']` = a **fresh literal**
   `{"structure": 0.5, "efficiency": 0.5}` — do **not** reuse `dict(_INSTRUCTION_FILE_WEIGHTS)`
   (the default 0.15/0.10 renormalizes to **0.6/0.4**, not the Q4-mandated 0.5/0.5). The entry is
   already an independent dict copy (registry.py:49), so this is a correctness change, not a
   byte-identity one.
2. **Headline exclusion.** `registry.py` `HEADLINE_EXCLUDED['agents.md']` = its **own** frozenset
   `_HEADLINE_EXCLUDED_INSTRUCTION | {"triggers", "quality", "edges", "composability", "clarity"}`.
   The eval-gated null dims MUST also leave the denominator or the cap + eval-suite warning
   survive. Do **not** mutate the shared `_HEADLINE_EXCLUDED_INSTRUCTION` (registry.py:74) — that
   would leak into the other formats and break their byte-identity.
   - Mechanism note: exclusion removes the dim from the renormalized basis (canonical set in
     `compute_composite`). A weight of 0 would NOT cap the score (the dim contributes 0 to a
     basis it is still in) but WOULD keep it "unmeasured" and **re-trigger the eval-suite
     warning** — so exclusion, not weight-0, is required to satisfy R2.
3. **Fix-path (R2).** Gate the SKILL-specific gradient computers in `text_gradient.py` on
   `detected_fmt`; pass `fmt` into `compute_gradients` so frontmatter / eval-suite / trigger /
   handoff / composability / quality / edges fixes are suppressed for agents.md (suppress, not
   replace — cheap, deterministic, no over-build). AGENTS.md v1 then has a score with few
   suggestions; the rich fix-path is Fast-follow.
4. **Format-routing prerequisite (BLOCKING, verified).** The corpus fixtures (`*__AGENTS.md.md`)
   detect as `format='unknown'` (budget 1500); identical content named `AGENTS.md` detects as
   `agents.md`; composite is identical (budget inert) so the per-dim stats are valid, BUT the
   profile (gated on `fmt==agents.md`) is a **no-op** on the fixtures until they route to
   `agents.md`. Fix first: copy fixtures to canonical `AGENTS.md` basenames in per-repo subdirs
   (or harden `detect_format`). Write the golden test against `agents.md`-detected scores.
5. `scripts/scoring/formats.py` — `FORMAT_AGENTS_MD` + 3000 budget already exist; no change.

## Risks (review-augmented)

- **Inert-recipe trap (caught):** the frozenset edit alone is worse than baseline. Both edits +
  the explicit 0.5/0.5 dict are mandatory.
- **Byte-identity trap:** editing the shared `_HEADLINE_EXCLUDED_INSTRUCTION` (not the agents.md
  entry) would silently change the other formats. Use an own frozenset.
- **Fix-path leak (R2):** if only the headline is changed, `suggest`/`evolve` still emit SKILL
  advice — the anti-billboard returns through the side door.
- **Safety mis-read:** a form-only headline grade-A's dangerous content (verified 90/A). Copy
  must not imply a safety/correctness stamp (see NON-GOALS).
- **State-of-AGENTS-2026 self-own:** a per-repo ranking on a form/density metric invites the
  rebuttal that thorough, content-rich docs rank lower for length (verified: FilOzone/synapse-sdk
  C@69.5 below underway S@95). Publish aggregate/anonymized only, or gate per-repo ranking on the
  operational-coverage Fast-follow.
- **Uncalibrated weights:** N=30, no ground truth; single files set the S/E boundaries. Label
  provisional.

## Acceptance test

The 30 corpus files, **routed to `agents.md`**, re-scored under the profile must show: (1) no
eval dim folded into the headline, no eval-suite warning; (2) the resolved distribution
(mean 73.90, median 77.25; bands S=2, A=2, B=12, C=7, D=6, E=1, F=0); (3) the other four formats'
golden scores unchanged; (4) `suggest` on an agents.md emits **no** SKILL-only fix (no
frontmatter/eval-suite/trigger/handoff/"use this skill when"); (5) a golden-score regression test
committed, pinning convention-free quantities (mean 73.90, median 77.25, band counts, and the
named anchors) plus the two exact-95.0 boundary files **meltano** and **underway** asserting
`score == 95.0 AND grade == 'S'` (the only off-by-one-sensitive boundary; no corpus file sits at
exactly 85.0 — the tight cluster is 86.0/A, 84.5/B, 84.0/B). Do not pin a stdev (convention-
dependent).

## Fast-follow (deferred — confirmed by review, do NOT fold into v1)

One AGENTS.md-native **operational-coverage** dimension (runnable setup/build/test commands,
code-style, PR/commit rules, gotchas) — the differentiated signal + the rich PR-comment fix-path.
The review verified the misrank that would justify it **does not reproduce** (a content-free
platitude caps at efficiency ~77 → B, a band below a genuine ops file at A, because efficiency
already rewards bash command fences), and a naive 4-item rubric scores the showcase misrank pair
identically — so building it now is the over-build trap with no validated trigger. The **real**
trigger to add it: a reproduced empty-doc gaming case (verified: 5 bare headings → 57.5/C) **plus**
a corpus-validated misrank. When built, key it on **content presence under headings**, not bash/sh
fences alone (which miss inline-backtick commands and false-negative good non-command docs).

## Dual-use of the dogfood batch

The 30-file run also seeds a one-shot **"State of AGENTS.md 2026"** data point — **aggregate /
anonymized only** for v1 (per the ranking-rebuttal risk above), NOT a perpetual crawler/index.
