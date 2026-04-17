# Reddit Launch Posts

> Prepared 2026-03-30, refreshed 2026-04-17. Copy-paste ready. Adjust tone/length per subreddit norms.

---

## Post 1 — r/ClaudeAI

**Title:** Most public SKILL.md / CLAUDE.md files are broken — I scored 120 of them and the fix lifts the average +22 points

**Body:**

If you use CLAUDE.md or SKILL.md files with Claude Code, you've probably noticed they degrade over time. Instructions drift, scope boundaries disappear, critical constraints get buried. The agent still follows them — just worse.

I built **[schliff](https://github.com/Zandereins/schliff)** — a deterministic quality scorer for AI instruction files. It analyzes SKILL.md, CLAUDE.md, .cursorrules, and AGENTS.md across 7 dimensions (structure, triggers, quality, edges, efficiency, composability, clarity) using static analysis (TF-IDF heuristics, sqrt density curves, antonym pair detection, entropy analysis). No LLM in the scoring path.

**Findings from scoring 120 public files (30 per format):**

- **100% of files ship without an eval suite** — three dimensions (triggers, quality, edges) stay unmeasured, locking 45% of the possible composite
- **59% grade below C.** Mean composite: 61.7 (median 62.5)
- **Composability is the real weak spot** — mean 30.4 of 100 across the corpus. Files tell agents what to do, almost never where to stop
- **AGENTS.md files score highest on average (64.8); SKILL.md lowest (55.4)** — structured formats don't help if frontmatter is skipped
- The gap between a D-grade and S-grade file is usually 4-6 targeted edits, not a rewrite — start with an eval suite

**How to try it:**

```bash
pip install schliff
schliff score CLAUDE.md          # single file score
schliff report SKILL.md          # markdown quality report
schliff doctor                   # scan all installed skills, health grades
```

The autonomous improvement loop (via `/schliff:auto` in Claude Code) can take a file from 54 [D] to 98 [S] by iterating edits against the scoring engine — no LLM needed for the scoring itself.

There's also a pre-commit hook and GitHub Action for CI integration, so scores can't silently regress.

**Stats:** Zero dependencies (pure Python stdlib), MIT license, Python 3.9+.

Happy to score anyone's SKILL.md or CLAUDE.md live in the comments — just paste a link.

---

## Post 2 — r/Python

**Title:** schliff: a zero-dependency Python CLI that lints AI instruction files (SKILL.md, CLAUDE.md, .cursorrules) — stdlib only

**Body:**

I've been building **[schliff](https://github.com/Zandereins/schliff)** — a CLI tool that scores AI agent instruction files (SKILL.md, CLAUDE.md, .cursorrules, AGENTS.md) across 7 quality dimensions (structure, triggers, quality, edges, efficiency, composability, clarity). The interesting part from a Python perspective: it's pure stdlib with zero dependencies.

**Technical approach:**

- TF-IDF heuristics to detect boilerplate and low-signal content
- Sqrt density curves for section length vs. information density scoring
- Antonym pair detection to find contradicting instructions
- Entropy analysis across document structure
- Anti-gaming detection (6 patterns) so you can't just keyword-stuff your way to a high score

The scoring engine is ~2,000 lines of pure stdlib Python with no ML/LLM in the scoring path. Everything runs deterministically — same file always produces the same score.

**Why stdlib only?** These files live in every project root. Adding a dependency tree for a linter that should be fast and portable felt wrong. `re`, `math`, `collections`, `json` — that's the whole stack.

**Tooling integration:**

```bash
pip install schliff
schliff score CLAUDE.md                    # single file
schliff report SKILL.md                    # markdown quality report
schliff suggest SKILL.md                   # ranked fixes with impact estimates
```

- Pre-commit hook: see `schliff verify` with `--min-score` and `--regression`
- GitHub Action available for CI gating

Python 3.9+, MIT licensed. Feedback on the architecture welcome — especially if you've built similar stdlib-only analysis tools.

GitHub: https://github.com/Zandereins/schliff

---

## Post 3 — r/MachineLearning

**Title:** [P] Deterministic scoring for AI agent instruction files — no ML needed, 7-dimension static analysis

**Body:**

AI coding agents (Claude Code, Cursor, Copilot) rely on natural-language instruction files (SKILL.md, CLAUDE.md, .cursorrules, AGENTS.md) to steer behavior. These files have no validation — they degrade silently as projects evolve.

**[schliff](https://github.com/Zandereins/schliff)** is a deterministic scoring tool that evaluates these files across 7 dimensions (structure, triggers, quality, edges, efficiency, composability, clarity) using classical NLP and information-theoretic methods. No learned model in the scoring path.

**Approach:**

1. **TF-IDF heuristics** — measures term specificity within instruction files to flag boilerplate and low-information-density sections
2. **Sqrt density curves** — models the relationship between section length and information payload; penalizes padding
3. **Antonym pair detection** — identifies contradicting instructions within the same file (e.g., "always use X" vs. "never use X" in different sections)
4. **Entropy analysis** — evaluates structural coherence and information distribution across document sections
5. **Anti-gaming detection** — 6 pattern detectors prevent score manipulation:
   - Keyword stuffing (high term frequency, low document relevance)
   - Artificial section inflation
   - Duplicate content across sections
   - Semantic padding (filler phrases that add no constraint)
   - Contradictory instruction injection
   - Structure mimicry without substance

**Key findings from scoring 120 public instruction files (30 per format: SKILL.md, CLAUDE.md, AGENTS.md, .cursorrules):**

- 100% of files ship without an eval suite — three dimensions (triggers, quality, edges) stay locked at zero, so 45% of the possible composite weight is unmeasured by default
- Mean composite is 61.7 (median 62.5); 59% grade below C. Grade distribution is concentrated at D (50.8%) with a thin tail at B (1.7%) and no A or S files in the corpus
- Composability is the weakest measured dimension (mean 30.4/100). Structure (76.5) and clarity (97.5) score well; scope definition does not
- Format does matter: AGENTS.md averages 64.8, CLAUDE.md 63.9, .cursorrules 62.6, SKILL.md 55.4

The scoring methodology is documented in detail: [docs/SCORING.md](https://github.com/Zandereins/schliff/blob/main/docs/SCORING.md)

The autonomous improvement loop iterates edits against the deterministic scorer until convergence — demonstrated improvements from 54/100 to 98/100 on real-world files.

Zero dependencies, pure Python stdlib, MIT license.

GitHub: https://github.com/Zandereins/schliff
