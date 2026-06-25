# Spec: AGENTS.md scoring profile

Status: DRAFT (dogfood-verified, awaiting build greenlight)
Date: 2026-06-25
Owner: Franz
Origin: moonshot strategy tournament — wave-rider bet ("agentsmd-lint: the deterministic CI quality gate for AGENTS.md")

## Goal

Make schliff produce **defensible, AGENTS.md-appropriate scores** so the engine and the
GitHub Action become a credible quality gate for the cross-tool **AGENTS.md** standard
(Cursor / Codex / Copilot / Claude Code / Devin). Today schliff applied to AGENTS.md is an
*anti-billboard*: it tells well-formed files they are failing for SKILL-only reasons. This
profile is the contained engine change that turns the largest-TAM format from a liability
into the product's wedge.

Non-goal: changing how `SKILL.md`, `CLAUDE.md`, `.cursorrules`, or `system_prompt` are
scored. Those must stay byte-identical (golden-score gate).

## Context — the verified problem

AGENTS.md is **project context for coding agents** (setup, build/test commands, code style,
PR/commit rules, gotchas). It is *always-on* context, not a *reusable skill with triggers
and an eval suite*. But it is currently scored through the shared SKILL scorer registry.

Dogfood evidence — the real engine (v8.2.0) over the 30 real public AGENTS.md files in
`docs/launch/corpus/agents/`:

```
N=30   composite: mean 28.3, median 29.2, range 18.9–33.7
grade=None:            30/30   (every file)
>=1 null dimension:    30/30   (triggers, quality, edges — all null)
"add an eval suite" warning: 30/30
ceiling: 42% for all (full-denominator cap on the 3 eval-gated dims)
```

Per-dimension distribution across the same 30 files:

| Dimension | n | mean | median | min | max | verdict for AGENTS.md |
|---|---|---|---|---|---|---|
| `structure` | 30 | 83.2 | 85.0 | 50 | 95 | **discriminates well — keep** |
| `efficiency` | 30 | 64.6 | 65.5 | 25 | 95 | **discriminates well — keep** |
| `clarity` | 30 | 98.9 | 100 | 92 | 100 | saturated (no discrimination) — keep, low weight |
| `composability` | 30 | 29.7 | 30.0 | 20 | 50 | **mis-fit** — measures SKILL scope/handoffs; punishes all AGENTS.md |
| `triggers` | 0 | — | — | — | — | **inapplicable** — "when to invoke a skill"; AGENTS.md is always-on |
| `quality` | 0 | — | — | — | — | **inapplicable** — eval-suite-gated |
| `edges` | 0 | — | — | — | — | **inapplicable** — eval-suite-gated |

Root cause: (1) `triggers`/`quality`/`edges` require an eval suite (a SKILL concept) and the
full-denominator composite keeps them in the denominator → permanent 42% cap; (2) the
`composability` scorer encodes SKILL semantics (scope boundaries, I/O contract, handoffs)
that do not map to a project-context file; (3) the warning text hard-codes
`/schliff:init` + "add an eval suite", which is incoherent advice for an AGENTS.md author.

## Requirements

- **R1 — defensible spread.** A well-formed AGENTS.md (setup + build/test + code-style + PR
  rules + gotchas) must land in a defensible band (B/A); a sloppy one in C/D. No more "every
  file is ~28/None".
- **R2 — no SKILL-only output.** The AGENTS.md result must not surface `triggers`/`quality`/
  `edges`, the eval-suite warning, or `/schliff:init` guidance. Warnings/suggestions must be
  AGENTS.md-relevant.
- **R3 — determinism preserved.** No LLM in the scoring path; reproducible, same score on any
  machine (the core selling point).
- **R4 — no regression elsewhere.** `SKILL.md` / `CLAUDE.md` / `.cursorrules` / `system_prompt`
  scores unchanged (golden-score byte-identity over the existing corpus).
- **R5 — locked.** A golden-score regression test pins the new AGENTS.md scores over the
  30-file corpus so the profile cannot silently rot.

## Technical decisions

### Dimension set for `fmt == agents.md`

Drop the inapplicable eval-gated dims from the **denominator** (not just report them null):
`triggers`, `quality`, `edges`.

Keep and re-weight the dims that discriminate: `structure`, `efficiency`, `clarity`
(low weight — saturated). `security` / `runtime` remain side signals as today.

`composability`: **re-purpose or drop** (open question Q1). As-is it is a low-discrimination
penalty (20–50) that measures SKILL handoff semantics. Either drop it for AGENTS.md or
redefine it as "does the file reference/links other docs and stay modular".

### MVP vs. differentiated profile

- **MVP (Option A — re-weight, ship fast):** for `fmt == agents.md`, composite =
  renormalized over `{structure, efficiency, clarity}` (+ re-purposed/omitted composability),
  eval-gated dims removed from the denominator, eval-suite warning suppressed. This alone
  lifts the 30-file corpus off the 42% cap and produces an honest spread driven by the two
  signals that already work (structure, efficiency). Smallest, lowest-risk change — the
  "contained build" the tournament required.
- **Fast-follow (Option B — one AGENTS.md-native dimension):** add an **operational-coverage**
  scorer that rewards what actually makes an AGENTS.md useful to an agent: presence of
  runnable **setup**, **build**, and **test** commands; **code-style/conventions**; **PR/commit
  rules**; **gotchas/constraints**. This is the discriminating dimension AND it powers the
  PR-comment fix-path ("add a Build & Test section: +N") that converts an impression into an
  adopter. Deterministic (section/keyword/code-fence detection), no eval suite.

Recommendation: ship **Option A** to make scores defensible immediately, then add the single
**operational-coverage** dimension from Option B as the differentiator before the Action
rebrand. Do **not** build a wide new scorer set — that re-enters the over-build trap.

### Implementation surface (to confirm during build)

- `skills/schliff/scripts/scoring/formats.py` already defines `FORMAT_AGENTS_MD` and a
  3000-token budget — the format hook exists.
- The composite/denominator logic and the eval-gated-dim warning live in the scoring
  composite layer (`scripts/scoring/`); the change is a per-format branch, not engine surgery.
- Golden-score fixtures: the 30 files in `docs/launch/corpus/agents/`.

## Open questions

- **Q1 — composability:** drop for AGENTS.md, or redefine to a meaningful project-context
  signal (cross-file references / modularity)? Current behavior unfairly compresses all files
  to 20–50.
- **Q2 — token budget:** is 3000 right for real AGENTS.md? (Check the corpus length
  distribution; some real files are much longer/shorter.)
- **Q3 — grade bands:** reuse the global S/A/B/C/D/E/F bands, or AGENTS.md-specific bands? A
  re-weighted MVP may still cluster — verify the spread before deciding.
- **Q4 — composite weights for Option A:** exact weights for `{structure, efficiency,
  clarity, (composability?)}` — set to maximize discrimination on the corpus without rewarding
  padding (the anti-gaming guards must still apply).

## Acceptance test

The same 30 corpus files re-scored under the profile must show: (1) no `grade=None`, no null
eval dims, no eval-suite warning; (2) a real spread (good files B/A, sloppy ones C/D — not all
within one band); (3) `SKILL.md`/`CLAUDE.md`/`.cursorrules`/`system_prompt` golden scores
unchanged; (4) a golden-score regression test committed for the AGENTS.md corpus.

## Dual-use of the dogfood batch

The 30-file scoring run is also the seed for a one-shot **"State of AGENTS.md 2026"** launch
data point (a single post/data hook — explicitly NOT a perpetual crawler/index, which the
tournament refused as a second full-time job).
