---
title: "The State of AI Instructions: I Scored 120 Public Files. The Mean Grade Is a D."
description: "A deterministic quality audit of 120 public AI instruction files (SKILL.md, CLAUDE.md, AGENTS.md, .cursorrules). Mean grade D, 59% below C — and the single highest-leverage fix is one almost nobody ships."
date: 2026-05-29
tags: [ai, agents, claude, tooling, schliff]
canonical: https://fpaul.dev/state-of-ai-instructions
---

Everyone is writing instructions for AI agents now — `CLAUDE.md` in the repo root,
`SKILL.md` for Claude Code skills, `AGENTS.md` for Codex, `.cursorrules` for Cursor.
We treat them like prose: write once, ship, never look back. So I asked a boring
question — **how good are they, actually?** — and answered it with numbers instead
of vibes.

I built [**Schliff**](https://github.com/Zandereins/schliff), a deterministic
quality scorer for instruction files (think "a linter for `SKILL.md`"), and ran it
over 120 public files pulled from GitHub. Deterministic means no LLM in the loop:
the same file gets the same score every time, on any machine. Here's what the data
says.

> **TL;DR** — Mean grade across 120 files: **D**. 59% score below C. The single
> change worth more than all the prose editing combined — adding a companion eval
> suite — is shipped by **zero of 60** sampled repositories.

## How I measured it

- **Tool:** Schliff — a deterministic scorer across seven weighted dimensions
  (structure, triggers, quality, edges, efficiency, composability, clarity).
- **Sample:** GitHub code-search top results per filename (`SKILL.md`, `CLAUDE.md`,
  `AGENTS.md`, `.cursorrules`), 30 per format after repo-level dedup — 120 files
  total. This is **popularity-weighted, not random**: these are the files people
  actually find and copy.
- **Honesty checks:** files under 50 bytes excluded (empty stubs); every file
  scored against its native format; collection date 2026-04-17.

Reproducible by design — same file, same score, no model calls.

## Finding 1: The category ships untested

Three of the seven dimensions — **triggers** (does it activate at the right time),
**quality** (does following it produce correct output), **edges** (does it handle
error cases) — can only be measured against a companion *eval suite*: a small file
of trigger phrases, quality assertions, and edge cases. It doesn't have to be in
any special format; it just has to exist.

It almost never does. I went back to 60 source repositories and looked for an eval
file in *any* shape:

| Check | Result |
|---|---|
| `eval-suite.json` next to the file | 0 / 60 |
| an `evals/` or `fixtures/` sibling | 0 / 60 |
| any `*-test.*` / `*-spec.*` alongside | 0 / 60 |

Zero. Not "people used a different format" — the entire category ships untested.
That leaves **55% of the possible score structurally unmeasurable**. Modeling a
perfect eval suite onto every file lifts the mean composite from **61.7 to 83.9
(+22 points)** and moves files at grade B-or-better from 1.7% to 88%.

Prose editing nudges a dimension a few points. Shipping evals unlocks more than
half the score. **Evals should be table stakes, not advanced practice.**

## Finding 2: Composability is the real weakness

Of the dimensions every file *can* be scored on, one is consistently broken:

| Dimension | Mean (of 100) |
|---|---|
| clarity | 97.5 |
| structure | 76.5 |
| efficiency | 52.8 |
| **composability** | **30.4** |

Instruction files tell an agent what to *do* and almost never define their *edges*:
when to stop, what they don't own, how to hand off. A three-line section —
`Does: X. Does not: Y. Hands off to: Z.` — typically moves composability from 30 to
70 in a single edit. It's the cheapest 40 points in the file.

## Finding 3: Length has a sweet spot (and it's not "shorter")

| Length | Avg composite |
|---|---|
| < 300 tokens | 51.3 |
| 300–2000 tokens | **64.5** |
| > 2000 tokens | 59.9 |

The folk rule "shorter is better" and the contrarian "longer is more thorough" are
both wrong. The rank correlation between length and score is ≈ 0. Short files don't
give the reader enough to work with; long files bleed efficiency to hedging and
repetition. It's not shorter or longer — it's **structured, up to a point.**

## Finding 4: Format matters, but not how you'd guess

| Format | Avg composite |
|---|---|
| AGENTS.md | 64.8 |
| CLAUDE.md | 63.9 |
| .cursorrules | 62.6 |
| SKILL.md | 55.4 |

The surprise is `SKILL.md` *last* — the newest format, often shipped without
frontmatter or headings. `AGENTS.md`, written mostly by Codex users following a
tighter convention, has denser prose and more consistent structure. Format doesn't
make a bad file good; frontmatter, scope sections, and an eval suite do.

## The distribution

```
   0-9 |  1 | #
 30-39 |  2 | ##
 40-49 |  7 | ######
 50-59 | 35 | ##############################
 60-69 | 53 | #############################################
 70-79 | 22 | ###################
 80+   |  0 |
```

Tight, unimodal, centered on D. **Not one file cleared the A threshold** — the
structural-only ceiling in this corpus is ~78. The A/S range is only reachable with
an eval suite attached.

## Three edits that take a D to a B in ten minutes

1. **Add an eval suite.** Unlocks the three locked dimensions (55% of the weight).
   Worth ~+22 points on its own.
2. **Add a scope section.** `Does / Does not / Hands off to`. Composability 30 → 70.
3. **Cut the hedging.** "try to" → the direct instruction; "you might want to" →
   "do X when Y". Efficiency +10.

## What this doesn't measure

The rubric is opinionated — seven dimensions, one view of "instruction-as-spec"
quality. Files optimized for other goals (persona voice, prompt-injection hardening,
creative latitude) will legitimately score lower without being worse on their own
terms. The corpus is popularity-weighted, not random; a random sample would likely
score *lower*, not higher. And eval-suite verification was sampled (n=60), not
exhaustive. The numbers describe a real gap, not a verdict on any single file.

## Score your own

Schliff is open source (MIT), zero-dependency, and deterministic:

```bash
pip install schliff
schliff score path/to/SKILL.md      # or CLAUDE.md, AGENTS.md, .cursorrules
schliff doctor                      # scan every installed Claude Code skill
```

Or wire it into CI as a PR quality gate with the
[Schliff GitHub Action](https://github.com/Zandereins/schliff). The full dataset,
methodology, and re-runnable pipeline are in the
[repository](https://github.com/Zandereins/schliff).

*Data collected 2026-04-17 via GitHub code search; scored deterministically with
Schliff. The "give it the final polish" tool is named after the German* Schliff —
*the finishing cut.*
