# Show HN: Schliff -- Deterministic quality scorer for AI instruction files

## Post

**Title:** Show HN: Schliff -- Deterministic quality scorer for AI instruction files

---

A developer used schliff to optimize the SKILL.md for [agent-review-panel](https://github.com/wan-huiyan/agent-review-panel), a multi-agent code review tool. The file went from 1,331 lines to 340 -- 75% fewer tokens. Score improved from 75 to 86. They A/B tested it on a 1,132-line document: identical review quality. Two separate optimization rounds -- they came back for more. The process is documented in their [HOW_WE_BUILT_THIS.md](https://github.com/wan-huiyan/agent-review-panel/blob/main/HOW_WE_BUILT_THIS.md).

I didn't know about this until I saw schliff in their Acknowledgements section.

Schliff is a deterministic quality scorer for AI instruction files -- CLAUDE.md, .cursorrules, AGENTS.md, SKILL.md. It evaluates 7 dimensions (structure, triggers, quality, edges, efficiency, composability, clarity) using Python 3.9+ stdlib only. No LLM, no API key, scores in milliseconds.

What it catches: copy-paste blocks that inflate scores without adding signal (one file dropped from 94 to 43 after dedup), "always X" vs "never X" contradictions hiding across sections, hedging language that wastes tokens, missing scope boundaries that cause agents to hallucinate responsibilities. It detects 6 gaming vectors so scores reflect actual quality, not surface polish.

The optional evolution engine (`pip install schliff[evolve]`) applies deterministic patches first, then uses an LLM for what rules can't fix. A demo file went from 54 to 98 in 18 iterations.

We scored 100+ public instruction files -- 73% grade below C.

MIT licensed: https://github.com/Zandereins/schliff

Happy to hear what dimensions you think matter most for instruction quality.

---

## Comment Strategy

Prepared responses for the 5 most likely HN questions.

### 1. "Why not just use a linter like ruff?"

Ruff checks syntax and style of *code*. Schliff scores the *semantic quality* of natural-language instruction files. A linter can tell you a markdown file is well-formed. It cannot tell you that your instructions contradict themselves in section 3 vs section 7, that 40% of your content is duplicated filler, or that your scope boundaries are missing -- causing agents to invent responsibilities.

### 2. "This seems over-engineered for a markdown file"

It would be, if these files stayed small. In practice, team-maintained instruction files grow to 500-2000 lines over months. At that scale, contradictions creep in, sections get copy-pasted between projects, and nobody audits whether directives still make sense together. The 73% below-C finding is not because people write bad instructions -- it is because nobody has tooling to catch the decay.

### 3. "Why deterministic instead of LLM-based scoring?"

Reproducibility: the same file always produces the same score, so you can track quality over time and gate PRs on it. Speed: scoring takes milliseconds, not seconds. Zero infrastructure: no API keys, no costs, no rate limits, no data leaving your machine. The optional LLM-based evolution engine is a separate step -- scoring itself is pure computation.

### 4. "How does this compare to prompt engineering tools?"

Prompt engineering tools help with single-shot API inputs. Schliff scores persistent instruction files that shape agent behavior across entire sessions. Different artifact, different failure modes. A prompt might be too vague; an instruction file might have 12 contradictions across 800 lines.

### 5. "Score inflation / gaming?"

Design priority from day one. 6 detection vectors: keyword stuffing, padding, repetition, structural inflation, contradictory filler, scope bleed. Files drop 30+ points when gaming detection kicks in. The goal is scores trustworthy enough for CI gates.
