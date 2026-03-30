# Reddit Launch Posts

> Prepared 2026-03-30. Copy-paste ready. Adjust tone/length per subreddit norms.

---

## Post 1 — r/ClaudeAI

**Title:** I built a linter for SKILL.md and CLAUDE.md files — scored 100+ public skills, 73% are below C

**Body:**

If you use CLAUDE.md or SKILL.md files with Claude Code, you've probably noticed they degrade over time. Instructions contradict each other, sections bloat, critical constraints get buried. The agent still follows them — just worse.

I built **[schliff](https://github.com/Zandereins/schliff)** — a deterministic quality scorer for AI instruction files. It analyzes SKILL.md, CLAUDE.md, .cursorrules, and AGENTS.md across 8 dimensions (structure, triggers, quality, edges, efficiency, composability, clarity, security) using static analysis (TF-IDF heuristics, sqrt density curves, antonym pair detection, entropy analysis). No LLM in the scoring path.

**Surprising findings from scoring 100+ public skills:**

- 73% of public SKILL.md files score below C grade — most lose points on contradiction detection and structural coherence
- Files with more than 800 lines almost always score worse than shorter, focused ones
- Copy-pasted boilerplate is the #1 score killer — TF-IDF catches repeated low-signal phrases instantly
- The gap between a D-grade and S-grade file is usually 4-6 targeted edits, not a rewrite

**How to try it:**

```bash
pip install schliff
schliff score CLAUDE.md          # single file score
schliff report SKILL.md          # markdown quality report
schliff doctor                   # scan all installed skills, health grades
```

The autonomous improvement loop (via `/schliff:auto` in Claude Code) can take a file from 54 [D] to 98 [S] by iterating edits against the scoring engine — no LLM needed for the scoring itself.

There's also a pre-commit hook and GitHub Action for CI integration, so scores can't silently regress.

**Stats:** 732 tests, zero dependencies (pure Python stdlib), MIT license, Python 3.9+.

Happy to score anyone's SKILL.md or CLAUDE.md live in the comments — just paste a link.

---

## Post 2 — r/Python

**Title:** schliff: a zero-dependency Python CLI that lints AI instruction files (SKILL.md, CLAUDE.md, .cursorrules) — 732 tests, stdlib only

**Body:**

I've been building **[schliff](https://github.com/Zandereins/schliff)** — a CLI tool that scores AI agent instruction files (SKILL.md, CLAUDE.md, .cursorrules, AGENTS.md) across 8 quality dimensions (structure, triggers, quality, edges, efficiency, composability, clarity, security). The interesting part from a Python perspective: it's pure stdlib with zero dependencies.

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

732 tests, Python 3.9+, MIT licensed. Feedback on the architecture welcome — especially if you've built similar stdlib-only analysis tools.

GitHub: https://github.com/Zandereins/schliff

---

## Post 3 — r/MachineLearning

**Title:** [P] Deterministic scoring for AI agent instruction files — no ML needed, 8-dimension static analysis

**Body:**

AI coding agents (Claude Code, Cursor, Copilot) rely on natural-language instruction files (SKILL.md, CLAUDE.md, .cursorrules, AGENTS.md) to steer behavior. These files have no validation — they degrade silently as projects evolve.

**[schliff](https://github.com/Zandereins/schliff)** is a deterministic scoring tool that evaluates these files across 8 dimensions (structure, triggers, quality, edges, efficiency, composability, clarity, security) using classical NLP and information-theoretic methods. No learned model in the scoring path.

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

**Key findings from scoring 100+ public instruction files:**

- Instruction quality follows a power law — a small number of files are well-structured, the vast majority are not
- Contradiction rate increases roughly linearly with file length beyond ~500 lines
- Files maintained by single authors score significantly higher on structural coherence than committee-edited files

The scoring methodology is documented in detail: [docs/SCORING.md](https://github.com/Zandereins/schliff/blob/main/docs/SCORING.md)

The autonomous improvement loop iterates edits against the deterministic scorer until convergence — demonstrated improvements from 54/100 to 98/100 on real-world files.

732 tests, zero dependencies, pure Python stdlib, MIT license.

GitHub: https://github.com/Zandereins/schliff
