# State of AI Instructions 2026

> We scored 120 public AI instruction files with schliff. **Mean grade: D. 59% below C.** Adding an eval suite — which zero of 60 sampled source repos ship — would lift the mean **+22 points**. Here's the data.

## Executive Summary

The first large-scale, deterministic quality audit of public AI instruction files reveals a consistent pattern: most files are written once and never measured. Across 120 scored files from four formats, the mean composite is **61.69 (median 62.5)** — the grade boundary between D and C. 59% of files fall below C. Not a single file in the verification sample (n=60 source repos) ships a companion eval suite, which leaves three of schliff's seven dimensions structurally unmeasured.

The gap between "has instructions" and "has measurable instructions" is wider than expected. The single highest-leverage change — adding an eval suite — is worth more than all the prose editing combined.

## Methodology

- **Tool:** schliff v7.1.0 — deterministic quality scorer, 7 dimensions. See `docs/SCORING.md` for the rubric
- **Sampling:** GitHub code-search results per filename (`SKILL.md`, `CLAUDE.md`, `AGENTS.md`, `.cursorrules`), capped at 30 per format after repo-level dedup. Ranked by GitHub's default relevance — **popularity-weighted, not random**. A random-sampled rerun is tracked as follow-up work
- **Format matching:** Every file scored against its native format flag (`CLAUDE.md → --format claude.md`, etc.). The eval-suite requirement applies per format; `triggers`/`quality`/`edges` are dimensions every schliff format scores, not SKILL.md-specific
- **Filters:** Files under 50 bytes excluded (empty stubs and placeholder commits). No other content filtering
- **Eval-suite verification:** 60 source repos sampled via `gh api`; each directory containing the instruction file inspected for `eval-suite.json`, `eval-suite-*.json`, `evals/`, `fixtures/`, and `*-test.json`. **Zero of 60 ship any companion eval artifact** — the "100% no eval" finding is not an artifact of the scoring setup
- **Reproducibility:** Deterministic scoring — same file, same score, every run. No LLM in the loop. Pipeline in `scripts/launch/` (collect → score → aggregate), re-runnable end-to-end
- **Collection date:** 2026-04-17
- **Sample size:** 120 scored files (30 × 4 formats)

## Key Findings

### Finding 1: The Category Ships Untested

> Across all 120 files and a 60-repo verification sample, not a single instruction file was accompanied by an eval suite. Adding one would lift the mean composite by **+22 points** (61.7 → 83.9).

Three of schliff's seven dimensions — `triggers`, `quality`, `edges` — require a paired eval file (any JSON of trigger phrases + quality assertions + edge cases; schliff defines a format but the structure is neutral). Without one, those dimensions return unmeasured and drop out of the composite. That's 55% of the total weight.

We didn't just score without evals; we went back to the source repos to check whether evals existed in any form:

| Check | Result |
|---|---|
| `eval-suite.json` adjacent to file | 0 / 60 |
| `eval-suite-*.json` adjacent | 0 / 60 |
| `evals/` sibling directory | 0 / 60 |
| `fixtures/` sibling directory | 0 / 60 |
| Any `*-test.*` or `*-spec.*` alongside | 0 / 60 |

The finding isn't that authors skipped schliff's format — it's that the entire category ships untested.

| Dimension | Measured in | Mean score | Median |
|-----------|------------:|-----------:|-------:|
| structure | 120 / 120 | 76.5 | 80.0 |
| triggers | **0 / 120** | — | — |
| quality | **0 / 120** | — | — |
| edges | **0 / 120** | — | — |
| efficiency | 120 / 120 | 52.8 | 53.0 |
| composability | 120 / 120 | 30.4 | 30.0 |
| clarity | 120 / 120 | 97.5 | 100.0 |

**What-if a perfect eval suite were attached to every file?**

| Metric | Current | With perfect eval | Δ |
|--------|--------:|------------------:|---:|
| Mean composite | 61.69 | **83.87** | **+22.18** |
| Files at grade B or better | 2 (1.7%) | 106 (88.3%) | +86.6 pp |
| Files below C | 71 (59.2%) | 1 (0.8%) | −58.4 pp |

Prose editing moves individual dimensions by a few points each. Shipping evals unlocks more than half the score. Evals should be table stakes, not advanced practice.

### Finding 2: Composability Is the Real Weakness

> Mean composability across the corpus: **30.4 / 100.**

Every file we measured scored `structure` (76.5 avg) and `clarity` (97.5 avg) comfortably above the midpoint. Composability — scope boundaries, error behavior, handoff points — averaged **30.4**, the lowest of any measured dimension. Instruction files tell agents what to do but almost never define their edges: when to stop, what they don't own, how to hand off.

A three-line "Scope" section (`Does: X. Does not: Y. Hands off to: Z.`) typically moves composability from 30 to 70 on a single edit.

### Finding 3: Length Has a Sweet Spot

> Files in the 300–2000 token range average 64.5. Files under 300 tokens average 51.3. Files over 2000 tokens average 59.9.

A common folk rule says shorter is better. A contrarian rule says longer is more thorough. The data supports neither — length is inverted-U.

| Bucket | N | Avg composite |
|--------|---:|--------------:|
| <300 tokens | 12 | 51.3 |
| 300–2000 tokens | 69 | **64.5** |
| >2000 tokens | 39 | 59.9 |

Short files can't give the scorer enough to measure (they lose on structure and composability). Long files lose `efficiency` points to hedging and repetition. Spearman ρ between token count and composite is +0.01 — no rank correlation. The relationship isn't "shorter is better" or "longer is better"; it's "structured is better, up to a point."

### Finding 4: Format Matters, But Not How You'd Guess

> AGENTS.md files score highest on average (64.8). SKILL.md files score lowest (55.4).

| Format | N | Avg composite | Median |
|--------|---:|--------------:|-------:|
| AGENTS.md | 30 | 64.8 | 66.2 |
| CLAUDE.md | 30 | 63.9 | 64.3 |
| .cursorrules | 30 | 62.6 | 61.7 |
| SKILL.md | 30 | 55.4 | 57.4 |

Per-dimension breakdown reveals where each format wins:

| Format | structure | efficiency | composability | clarity |
|--------|----------:|-----------:|--------------:|--------:|
| AGENTS.md | 83.2 | 55.2 | 29.7 | 99.4 |
| CLAUDE.md | 80.2 | 53.1 | 33.1 | 98.0 |
| .cursorrules | 79.5 | 51.8 | 30.4 | 98.0 |
| SKILL.md | 63.3 | 51.0 | 28.4 | 94.6 |

The surprise is SKILL.md at the bottom across every dimension — especially `structure` (−20 points vs AGENTS.md). Public SKILL.md files are the youngest format (rolled out late 2025) and often skip frontmatter, headings, or both. AGENTS.md files, mostly written by Codex users following the AGENTS.md convention, have denser prose and more consistent organization.

Format doesn't make a bad file good. Frontmatter, scope sections, and an eval suite do.

### Finding 5: The Security Blind Spot

> Almost no public instruction files address prompt injection or tool-use boundaries.

Security scoring exists as a separate module (`scoring/security.py`) but is not part of the default composite. As agents increasingly have write access to codebases, this gap is worth noting even outside the scored dimensions.

## Score Distribution

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

| Grade | Range | Count | % of corpus |
|-------|-------|------:|------------:|
| S | ≥95 | 0 | 0.0% |
| A | ≥85 | 0 | 0.0% |
| B | ≥75 | 2 | 1.7% |
| C | ≥65 | 47 | 39.2% |
| D | ≥50 | 61 | 50.8% |
| E | ≥35 | 8 | 6.7% |
| F | <35 | 2 | 1.7% |

Distribution is tight, unimodal, centered on D. Zero files cleared the A threshold — the structural-only ceiling in this corpus is ~78 (observed max: `rob9206/DynoAI_3/.cursorrules` at 78.0). The A/S range is reachable only with an eval suite attached.

## Top-Scoring Public Files

| Rank | Score | Grade | Format | File |
|:---:|------:|:-----:|--------|------|
| 1 | 78.0 | B | .cursorrules | [rob9206/DynoAI_3](https://github.com/rob9206/DynoAI_3/blob/main/.cursorrules) |
| 2 | 75.4 | B | AGENTS.md | [markov-kernel/databricks-mcp](https://github.com/markov-kernel/databricks-mcp/blob/main/AGENTS.md) |
| 3 | 74.4 | C | .cursorrules | [onigetoc/terminalx-experience](https://github.com/onigetoc/terminalx-experience/blob/main/.cursorrules) |
| 4 | 74.0 | C | CLAUDE.md | [jxcross/english-practice-streamlit](https://github.com/jxcross/english-practice-streamlit/blob/main/CLAUDE.md) |
| 5 | 74.0 | C | AGENTS.md | [Brendonovich/MacroGraph](https://github.com/Brendonovich/MacroGraph/blob/main/AGENTS.md) |

All five cleared 70 on structure + efficiency + clarity alone. None had eval suites; each would jump to the A or S range with one added.

## Common Anti-Patterns (from dimension analysis)

| Anti-Pattern | Score Impact |
|---|---|
| No companion eval suite (3 dimensions drop out) | -55 pts of composite weight |
| Missing scope / error boundaries | composability ≈ 30 avg (of 100) |
| Hedging and filler language | efficiency ≈ 53 avg (of 100) |
| No frontmatter (format-dependent) | structure -15 to -20 pts |
| Stub files without body | sub-300-token files avg 51.3 vs 64.5 for structured files |

## Applying the Data: Three Highest-Impact Changes

> Any D-grade file can reach B in under 10 minutes with three targeted edits.

### 1. Add an eval suite

Unlocks 3 unmeasured dimensions (`triggers`, `quality`, `edges`). Without evals, 55% of the possible composite is locked out. Mean corpus lift: +22 points per file. Use `/schliff:init path/to/SKILL.md` inside Claude Code to bootstrap one, or create `eval-suite.json` manually with trigger phrases, quality assertions, and edge cases.

### 2. Add a scope / composability section

Composability scored 30.4 on average across 120 files — the weakest dimension. A three-line section — `Does: X. Does not: Y. Hands off to: Z.` — typically moves composability 30 → 70 on a single edit.

### 3. Remove hedging language

Efficiency averages 52.8. Find and replace: "try to" → direct instruction, "you might want to" → "do X when Y", "consider" → "check" or "verify". Efficiency score jumps 10+ points.

## Limits of This Measurement

- **Rubric is opinionated.** The 7 dimensions are schliff's rubric. Files that optimize for other goals (prompt-injection hardening, persona voice, creative latitude) will legitimately score lower without being worse on their own terms. The numbers describe instruction-as-spec quality, not instruction quality in every sense
- **Corpus is popularity-weighted, not random.** `gh search code` ranks by GitHub relevance. Random sampling would likely show a lower mean — there's no reason to expect these numbers to flatter the population
- **Eval-suite verification was sampled (n=60), not exhaustive.** A larger verification run is straightforward to re-execute
- **The <50-byte filter** removed empty files and placeholder commits. Document to avoid the objection that we inflated "no eval" by including stubs
- **Security dimension opt-in.** Not part of the composite. Files with stronger security hygiene are not rewarded by the numbers above

## Methodology Details

### Scoring Dimensions

| Dimension | Weight | What It Measures |
|---|---|---|
| Structure | 15% | Frontmatter, sections, organization |
| Triggers | 20% | When does this skill activate? (requires eval) |
| Quality | 20% | Output correctness assertions (requires eval) |
| Edges | 15% | Error cases, boundaries (requires eval) |
| Efficiency | 10% | Token density, no redundancy, no hedging |
| Composability | 10% | Scope boundaries, interop with other skills |
| Clarity | 5% | No contradictions, unambiguous instructions |

### Anti-Gaming

6 detection vectors active to prevent score manipulation through keyword stuffing, structural padding, or synthetic eval suites.

### Reproducibility

```bash
pip install schliff
schliff score <file>        # single file
schliff doctor              # scan all installed skills
schliff report <file>       # markdown quality report
```

The full data-collection pipeline is in `scripts/launch/`:
- `collect_corpus.py` — fetches files via GitHub search
- `score_corpus.py` — runs `schliff score --json` on each file
- `aggregate_stats.py` — produces all numbers above

## About Schliff

**Schliff** is a deterministic quality scorer for AI agent instruction files. 7 dimensions. MIT license. Zero dependencies (core); optional `schliff[evolve]` adds LLM support via litellm for the evolution loop.

- GitHub: [github.com/Zandereins/schliff](https://github.com/Zandereins/schliff)
- Install: `pip install schliff`
- Docs: See repository README

---

*Data collected 2026-04-17 via `gh search code` top results. Re-runnable pipeline in `scripts/launch/`. Raw scores in `docs/launch/corpus/scores/`.*
