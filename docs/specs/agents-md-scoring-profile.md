# Spec: AGENTS.md scoring profile

Status: RESOLVED — build-ready (awaiting build greenlight)
Date: 2026-06-25
Owner: Franz
Origin: moonshot strategy tournament — wave-rider bet ("agentsmd-lint: the deterministic CI quality gate for AGENTS.md"). The 4 open questions were resolved by an engine-backed subagent panel (Q1/Q2 empirical, Q4 weights, Q3 bands) with adversarial verification over the 30-file corpus.

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

```text
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
| `clarity` | 30 | 98.9 | 100 | 92 | 100 | **saturated (stdev 2.60, corr -0.11) — drop from headline** |
| `composability` | 30 | 29.7 | 30.0 | 20 | 50 | **mis-fit (corr ~0) — drop from headline** |
| `triggers` | 0 | — | — | — | — | **inapplicable** — "when to invoke a skill"; AGENTS.md is always-on |
| `quality` | 0 | — | — | — | — | **inapplicable** — eval-suite-gated |
| `edges` | 0 | — | — | — | — | **inapplicable** — eval-suite-gated |

Root cause: (1) `triggers`/`quality`/`edges` require an eval suite (a SKILL concept) and the
full-denominator composite keeps them in the denominator → permanent 42% cap; (2) the
`composability` scorer encodes SKILL semantics (scope boundaries, I/O contract, handoffs,
namespace, version-compat, idempotency) that a project-context file legitimately lacks; (3)
the warning text hard-codes `/schliff:init` + "add an eval suite", incoherent for an
AGENTS.md author.

## Requirements

- **R1 — defensible spread.** A well-formed AGENTS.md (setup + build/test + code-style + PR
  rules + gotchas) must land in a defensible band (B/A); a sloppy one in C/D.
- **R2 — no SKILL-only output.** The AGENTS.md result must not surface `triggers`/`quality`/
  `edges`, the eval-suite warning, or `/schliff:init` guidance. **Prerequisite:** the file must
  be detected as `fmt == agents.md` (see Implementation surface — today mangled fixture names
  detect as `unknown`).
- **R3 — determinism preserved.** No LLM in the scoring path; reproducible.
- **R4 — no regression elsewhere.** `SKILL.md` / `CLAUDE.md` / `.cursorrules` / `system_prompt`
  scores unchanged (golden-score byte-identity).
- **R5 — locked.** A golden-score regression test pins the new AGENTS.md scores over the
  30-file corpus, including the lower-bound-inclusive band-boundary files.

## Technical decisions (RESOLVED)

### Dimension set for `fmt == agents.md`

Headline composite is computed over **`{structure, efficiency}` only**. Removed from the
**denominator** (still scored and reported as side signals, just not folded into the headline
number):

- eval-gated `triggers`, `quality`, `edges` — inapplicable (no eval suite for a project doc);
- `clarity` (Q4) — saturated on the corpus (mean 98.87, stdev 2.60, corr -0.11 with
  composite); any weight injects a near-constant ~99 offset that compresses spread without
  separating good from sloppy docs;
- `composability` (Q1) — measures SKILL invocable-unit semantics a project-onboarding doc
  legitimately lacks (mean 29.67, range 20-50, 10/30 floor at exactly 20 passing zero positive
  checks, `no_version_compat` fails 30/30, corr ~0 with structure/efficiency). Redefining it
  (cross-file refs / modularity) is the over-build trap and is explicitly **not** done.
- `security` / `runtime` remain opt-in side signals as today.

The per-dimension scorers for the dropped dims **still run** (so `guards.py` and the
side-signal report stay intact); they are excluded from the headline denominator only.

### Composite weights (Q4)

`fmt == agents.md` composite = **`0.5 * structure + 0.5 * efficiency`**, renormalized over
those two dims only. Both discriminate (structure 50-95, efficiency 25-95), are distinct
(inter-corr 0.718), and 50/50 avoids over-weighting the noisier efficiency dim (stdev 17.07,
hostage to the char/4 density proxy). Result over the 30-file corpus: **mean 73.90, median
77.25, min 37.5, max 95.0, stdev 12.74, range 57.5**. Rejected: `clarity`-inclusive equal-3
(collapses 20/30 into the A band), and 0.4/0.6 efficiency-heavy (marginally higher raw spread
but hostage to the density proxy — rejected at the tie per the edge-case-correct rule).

### Token budget (Q2)

Keep `FORMAT_TOKEN_BUDGETS['agents.md'] = 3000`. It is **advisory-only**: it feeds the
separate `token_budget` JSON block in `cli.py`, **not** the efficiency dimension (density-only)
and **not** the composite — changing it moves both by 0. 3000 lands in the empty gap between
the 25-file dense cluster (≤2079 tokens) and the 5-file long tail (≥3219), flagging exactly
the 5 genuinely-long files (25 ok / 0 warning / 5 over). Do **not** lower below 2079 (would
warn on normal-length real files) or raise above 3219 (would stop flagging the long tail). The
budget/efficiency-low-tail co-variation is coincidental — do not market it as a density proxy.

### Grade bands (Q3)

Reuse the **global** bands unchanged: S≥95, A≥85, B≥75, C≥65, D≥50, E≥35, F<35 (lower-bound
inclusive). `score_to_grade` is format-agnostic; reuse preserves cross-format comparability (a
'B' means the same across all formats) — the cross-tool guarantee the AGENTS.md wedge sells.
The 50/50 composite spans 6 of 7 bands (**S=2, A=2, B=12, C=7, D=6, E=1, F=0**) with a
monotone, face-valid ordering (meltano/underway S@95.0; kudu B@84.5; gordonwatts stub D@52.5;
VCnoC bloat E@37.5), so the spec's condition for agents-specific bands is not met.

### Implementation surface

- **BLOCKING PREREQUISITE (R2), verified:** the engine classifies the corpus fixtures
  (basenames `*__AGENTS.md.md`) as `format='unknown'` (budget 1500). Confirmed: the same
  content named `AGENTS.md` detects as `agents.md`; `--format agents` also works; the composite
  is identical (29.6) across all three because the budget is inert (Q2) — so the per-dim stats
  above are valid regardless, BUT the profile (composability/clarity exclusion + weights, gated
  on `fmt==agents.md`) is a **no-op on the fixtures until they route to `agents.md`**. Fix
  first: copy the 30 fixtures to canonical `AGENTS.md` basenames in per-repo subdirs (or harden
  `detect_format`). The golden test must be written against `agents.md`-detected scores, never
  the `unknown` ones.
- `skills/schliff/scripts/scoring/registry.py:74-79` — give `agents.md` its **own**
  `HEADLINE_EXCLUDED` frozenset = `_HEADLINE_EXCLUDED_INSTRUCTION | {"composability", "clarity"}`.
  Do **not** mutate the shared `_HEADLINE_EXCLUDED_INSTRUCTION` (line 74) — that would leak into
  skill.md/claude.md/cursorrules and break their byte-identity. Excluding from the denominator
  (not weight=0) is required so the composite renormalizes over `{structure, efficiency}`;
  weight=0 would leave the dim in the denominator and re-introduce a cap.
- The agents.md profile weights (`structure` 0.5, `efficiency` 0.5) live in the per-format
  weight table in `registry.py` / `scripts/scoring/`.
- `scripts/scoring/formats.py` — `FORMAT_AGENTS_MD` and the 3000 budget already exist; no change.
- Golden-score fixtures: the 30 files in `docs/launch/corpus/agents/` (routed to `agents.md`).

## Risks

- **Byte-identity trap:** editing the shared `_HEADLINE_EXCLUDED_INSTRUCTION` instead of giving
  `agents.md` its own frozenset would silently drop composability/clarity from
  skill.md/claude.md/cursorrules too. The `agents.md` entry must get its OWN frozenset.
- **Format-routing no-op:** if the build skips the format-detection prerequisite, every change
  is inert and the golden test pins the wrong (unknown-format) numbers.
- **Advisory-budget surprise:** a reviewer expecting the 3000 budget to lift the efficiency low
  tail will be wrong — it gates nothing. State advisory-only explicitly in the PR.
- **Denominator now only structure+efficiency:** if a future larger/differently-sampled corpus
  shows the efficiency char/4 density proxy misranking a dense-but-unstructured doc above a
  well-organized one, revisit by adding the Option-B operational-coverage dimension — **not** by
  repartitioning the bands (breaks cross-format comparability).
- **Boundary semantics:** two files sit exactly at 95.0 (S) and several near 85.0; the R5 golden
  test must pin these so a future off-by-one in the `score >= threshold` comparator is caught.

## Acceptance test

The 30 corpus files, **routed to `agents.md`**, re-scored under the profile must show: (1) no
`grade=None`, no null eval dims, no eval-suite warning; (2) the resolved distribution (mean
73.90, median 77.25, stdev 12.74; bands S=2, A=2, B=12, C=7, D=6, E=1, F=0); (3)
`SKILL.md`/`CLAUDE.md`/`.cursorrules`/`system_prompt` golden scores unchanged; (4) a
golden-score regression test committed for the AGENTS.md corpus including the band-boundary
files.

## Fast-follow (deliberate later increment, not an open question)

One AGENTS.md-native **operational-coverage** dimension (presence of runnable setup/build/test
commands, code-style, PR/commit rules, gotchas) — the differentiated signal that powers the
PR-comment fix-path ("add a Build & Test section: +N"). Add only if a larger corpus shows the
2-dim composite misranks; do **not** build a wide new scorer suite (over-build trap).

## Dual-use of the dogfood batch

The 30-file scoring run is also the seed for a one-shot **"State of AGENTS.md 2026"** launch
data point (a single post/data hook — explicitly NOT a perpetual crawler/index, which the
tournament refused as a second full-time job).
