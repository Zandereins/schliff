# Corpus Aggregation Stats

Total files processed: 120
Successfully scored: 120
Errors: 0

Source corpus: `docs/launch/corpus/{skill,claude,agents,cursor}/` (30 files each, harvested from public GitHub repos).
Raw scores: `docs/launch/corpus/scores/_summary.json`.

## Headline Numbers

- **% below C (<70):** 59.2%
- **Mean composite:** 61.69 (median 62.5, stdev 9.8)
- **% with no eval suite shipped alongside the instruction file:** 100.0% (see Part 1 — data integrity check)
- **<300 token files (n=12):** avg 51.27
- **300–2000 token files (n=69):** avg 64.50 — the "sweet spot"
- **>2000 token files (n=39):** avg 59.92
- **Ceiling lift from adding a perfect eval suite:** +22.2 points mean (61.7 → 83.9)

## Grade Distribution

| Grade | Count | % |
|-------|-------|---|
| B | 2 | 1.7% |
| C | 47 | 39.2% |
| D | 61 | 50.8% |
| E | 8 | 6.7% |
| F | 2 | 1.7% |

## Data Integrity — "100% no eval suite" claim

We verified the claim against the source repos. For every one of the 30 skill repos (100% of the skill corpus) plus 30 sampled repos across claude/agents/cursor formats, we listed the contents of the directory holding the instruction file via `gh api repos/OWNER/REPO/contents/...` and searched for `eval-suite.json`, `eval-suite-*.json`, or `evals/` directories.

**Result: 0 / 60 sampled repos** ship an eval suite adjacent to the instruction file. The "100%" figure is not an artifact of scoring — it reflects the reality of the corpus. schliff's scorer correctly returned `-1` (unmeasured) for `triggers`, `quality`, and `edges` because there was literally nothing to measure against.

**Recommended wording change for `state-of-ai-instructions.md`:**

Replace any phrasing that could read as "we chose not to measure" with one of these:

- Short form: "100% of files ship without a companion eval suite (verified against source repos, n=60 sampled)."
- Long form: "Across all 120 files and a 60-repo verification sample, not a single instruction file was accompanied by an eval suite (`eval-suite.json` or `evals/`). schliff's `triggers`, `quality`, and `edges` dimensions therefore return unmeasured for the entire corpus — because the evidence does not exist in the public artifact, not because we declined to look."

The claim is valid as stated; the wording upgrade just pre-empts a natural reader objection.

## Per-Dimension Averages (measured dimensions only)

| Dimension | N measured | Mean | Median |
|-----------|-----------|------|--------|
| structure | 120 | 76.54 | 80.0 |
| triggers | 0 | — | — |
| quality | 0 | — | — |
| edges | 0 | — | — |
| efficiency | 120 | 52.80 | 53.0 |
| composability | 120 | 30.39 | 30.0 |
| clarity | 120 | 97.50 | 100.0 |

Only 4 of 8 dimensions have data; `security` is opt-in, and the three eval-dependent dimensions are universally unmeasured (see above).

## Per-Format Composite Averages

| Format | N | Avg composite | Median |
|--------|---|---------------|--------|
| skill | 30 | 55.43 | 57.35 |
| cursor | 30 | 62.63 | 61.65 |
| claude | 30 | 63.87 | 64.25 |
| agents | 30 | 64.83 | 66.15 |

## Per-Format Dimension Breakdown (4 × 4 table)

Means per measured dimension, by format:

| Format | structure | efficiency | composability | clarity |
|--------|----------:|-----------:|--------------:|--------:|
| skill  |      63.3 |       51.0 |          28.4 |    94.6 |
| claude |      80.2 |       53.1 |          33.1 |    98.0 |
| agents |      83.2 |       55.2 |          29.7 |    99.4 |
| cursor |      79.5 |       51.8 |          30.4 |    98.0 |

**Winner per dimension:**
- structure: `agents` (83.2) — AGENTS.md files tend to be well-organized with explicit headings.
- efficiency: `agents` (55.2) — agents beats the others, but by <5 points; all formats have significant fluff.
- composability: `claude` (33.1) — still poor absolutely; CLAUDE.md authors handoff-declare marginally better.
- clarity: `agents` (99.4) — functionally tied with claude/cursor (98.0); skill lags by ~5 points.

**Loser:** `skill` in all four dimensions. SKILL.md files in the corpus are the youngest format (rolled out Oct 2025) and show the least editorial maturity — especially `structure` (−17 vs agents) where frontmatter violations and missing headers dominate.

## Score Distribution Histogram (10-point buckets)

```
   0-9 |   1 | #
 10-19 |   0 |
 20-29 |   0 |
 30-39 |   2 | ##
 40-49 |   7 | ######
 50-59 |  35 | ##############################
 60-69 |  53 | #############################################
 70-79 |  22 | ###################
 80-89 |   0 |
90-100 |   0 |
```

Distribution is tight, unimodal, and centered on D (60–69). **Zero files score B+ on structural dimensions alone** — the composite ceiling without eval data is effectively 78 (observed max: `rob9206/DynoAI_3/.cursorrules` at 78.0).

## Correlation — File Length vs Composite Score

- Pearson r (tokens vs composite): **−0.22**
- Pearson r (log(tokens) vs composite): **+0.11**
- Spearman ρ (rank correlation): **+0.01**

Interpretation: the relationship is **not monotonic** — it's an inverted-U. Segmented means:

| Bucket | n | Mean composite |
|--------|---|---------------:|
| <300 tokens | 12 | 51.27 |
| 300–2000 tokens | 69 | **64.50** |
| >2000 tokens | 39 | 59.92 |

The "short files score worse" framing is directionally correct for the <300 tail (12 files), but the full story is different: files in the 300–2000 range score best, and the score drops again above 2000 tokens because `efficiency` penalizes verbosity. The negative Pearson r is an artifact of long-tail heavy files pulling the regression line down, not of a genuine "longer = better" or "shorter = worse" rule.

**Recommended framing:** "Length has a sweet spot. Files under 300 tokens can't give the scorer enough to measure (mean 51); files over 2000 tokens lose efficiency points to filler (mean 60); the 300–2000 range clears 64 on average. The Pearson correlation coefficient (−0.22) misrepresents this as a linear relationship — Spearman ρ (0.01) is closer to the truth."

## Outlier Analysis — `SukinShetty/Nemp-memory` (composite 0.0)

The full file is 210 bytes, 52 tokens:

```yaml
---
name: nemp-memory
description: Persistent local memory for AI agents. Save, recall, and search project decisions as local JSON. Zero cloud, zero infrastructure.
metadata: {"openclaw": {"always": true}}
---
```

It's a frontmatter stub — no body, no headings, no procedure, no examples. All four measurable dimensions score 0:

- `structure`: 0 (no body, no H2s, no anchoring sections)
- `efficiency`: 0 (signal-to-noise undefined when signal is a one-liner)
- `composability`: 0 (no scope declarations)
- `clarity`: 0 (nothing to be clear about — the pattern scorer emits 0 instead of 100 when there's effectively no prose)

**Is the 0.0 fair?** Yes. The file makes no attempt to be a usable skill document — it's a package manifest masquerading as a SKILL.md. A scorer that awarded partial credit for "well, at least the frontmatter parses" would obscure exactly the failure mode the launch report is documenting: authors publishing SKILL.md files without writing the skill. The 0.0 is a feature, not a bug.

It's also the only file in the corpus that scored 0 — the next-lowest is 34.0. The distribution is not pathologically weighted by this outlier.

## What-If Analysis — Ceiling Lift from a Perfect Eval Suite

If every file in the corpus were accompanied by a theoretically-perfect eval suite (triggers=100, quality=100, edges=100), holding all other dimensions constant:

| Metric | Current | With perfect eval | Δ |
|--------|--------:|------------------:|---:|
| Mean composite | 61.69 | **83.87** | **+22.18** |
| Min lift (per file) | — | — | +12.70 |
| Max lift (per file) | — | — | +57.90 |
| Files at grade B or better | 2 (1.7%) | 106 (88.3%) | +86.6 pp |
| Files below C | 71 (59.2%) | 1 (0.8%) | −58.4 pp |

**Headline number for the report: +22 points on average.** Adding an eval suite is the single highest-leverage change an author can make — not because the scorer "rewards" evals, but because 55% of the weight profile (0.20+0.20+0.15) is inaccessible without one. Writing better prose moves structure/efficiency/composability/clarity by a few points each; shipping evals unlocks more than half the score.

This is the structural case for pushing eval suites as table stakes, not as advanced practice.

## Top 5 / Bottom 5

**Top:**
- 78.0 [B] — `docs/launch/corpus/cursor/rob9206__DynoAI_3__.cursorrules.md.cursorrules`
- 75.4 [B] — `docs/launch/corpus/agents/markov-kernel__databricks-mcp__AGENTS.md.md`
- 74.4 [C] — `docs/launch/corpus/cursor/onigetoc__terminalx-experience__.cursorrules.md.cursorrules`
- 74.0 [C] — `docs/launch/corpus/claude/jxcross__english-practice-streamlit__CLAUDE.md.md`
- 74.0 [C] — `docs/launch/corpus/agents/Brendonovich__MacroGraph__AGENTS.md.md`

**Bottom:**
- 45.0 [E] — `docs/launch/corpus/agents/VCnoC__Claude-Code-Zen-mcp-Skill-Work__AGENTS.md.md`
- 43.1 [E] — `docs/launch/corpus/skill/luofengmacheng__algorithms__skill.md.md`
- 37.5 [E] — `docs/launch/corpus/skill/neatsarab__GAP-Design-System__Skill.md.md`
- 34.0 [F] — `docs/launch/corpus/skill/onimisim2204430__church-digital-engagement-platform__Skill.md.md`
- 0.0 [F] — `docs/launch/corpus/skill/SukinShetty__Nemp-memory__SKILL.md.md` (see outlier analysis above)
