# Schliff Launch — Twitter/X Thread

> 7 tweets. Each ≤280 characters. Copy-paste ready.

---

## Tweet 1 — Hook

AI coding agents are only as good as their instruction files. I scored 100+ public SKILL.md and CLAUDE.md files. 73% score below C. The most common problem: they tell the agent WHAT to do but never define WHEN to activate or HOW to fail. Here's what I found.

## Tweet 2 — The Problem

Instruction files degrade silently. Triggers overlap, instructions contradict ("always X" vs "never X"), no edge cases defined, hedging wastes tokens. There was no linter for this.

## Tweet 3 — The Solution

Schliff: deterministic quality scoring for AI instruction files. 7 dimensions. Zero dependencies. No LLM needed. Same input, same score, every time. pip install schliff && schliff score path/to/SKILL.md. Works with SKILL.md, CLAUDE.md, .cursorrules, AGENTS.md.

## Tweet 4 — Demo

A vague deployment helper goes from 54 [D] to 98 [S] in 18 autonomous iterations. Structure: 70->100. Triggers: 0->100. Quality: 0->95. Efficiency: 35->93. The scorer is the ruler. Claude is the craftsman. [DEMO GIF PLACEHOLDER]

## Tweet 5 — Data

The "State of AI Instructions" report: 61% of public skills score 0/100 on triggers, quality, AND edges. Average score: 47 [D]. Most common fix: adding an eval-suite unlocks 3 unmeasured dimensions. Top skills use <300 tokens with higher scores than 1000+ token files.

## Tweet 6 — Try It

Try it in 10 seconds: pip install schliff && schliff demo. Score your files: schliff score SKILL.md. Get fixes: schliff suggest SKILL.md. Scan all skills: schliff doctor. 732 tests. MIT license. Zero dependencies.

## Tweet 7 — CTA

The Codecov for AI instruction files. github.com/Zandereins/schliff. If you maintain skills for Claude Code, Cursor, or Copilot — your files probably score lower than you think.
