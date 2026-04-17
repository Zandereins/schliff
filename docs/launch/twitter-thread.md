# Schliff Launch — Twitter/X Thread

> 7 tweets. Each ≤280 characters. Copy-paste ready.

---

## Tweet 1 — Hook

I scored 120 public AI instruction files across 4 formats (SKILL.md, CLAUDE.md, AGENTS.md, .cursorrules). 59% grade below C. 100% ship with no eval suite — locking 45% of the possible score by construction. Here's what the data says.

## Tweet 2 — The Problem

Instruction files degrade silently. Triggers overlap, scope dissolves, edge cases stay undefined, hedging wastes tokens. Existing linters (agnix, AgentLinter) validate rule sets. Schliff scores on a 0-100 scale and closes the loop.

## Tweet 3 — The Solution

Schliff: deterministic quality scoring for AI instruction files. 7 dimensions. Zero dependencies. No LLM needed. Same input, same score, every time. pip install schliff && schliff score path/to/SKILL.md. Works with SKILL.md, CLAUDE.md, .cursorrules, AGENTS.md.

## Tweet 4 — Demo

A vague deployment helper goes from 54 [D] to 98 [S] in 18 autonomous iterations. Structure: 70->100. Triggers: 0->100. Quality: 0->95. Efficiency: 35->93. The scorer is the ruler. Claude is the craftsman.

*(Attach demo GIF when posting — `demo/schliff-demo.gif` in repo.)*

## Tweet 5 — Data

State of AI Instructions (n=120): 100% ship without a companion eval suite. Adding one lifts mean score +22 points. Weakest dimension: composability (30/100). Best format: AGENTS.md (64.8). Worst: SKILL.md (55.4). Mean composite: 62 [D].

## Tweet 6 — Try It

Try it in 10 seconds: pip install schliff && schliff demo. Score your files: schliff score SKILL.md. Get fixes: schliff suggest SKILL.md. Scan all skills: schliff doctor. MIT license. Zero dependencies.

## Tweet 7 — CTA

The Codecov for AI instruction files. github.com/Zandereins/schliff. If you maintain skills for Claude Code, Cursor, or Copilot — your files probably score lower than you think.
