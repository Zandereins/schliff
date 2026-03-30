# Show HN: Schliff -- Quality scorer for AI instruction files

## Post

**Title:** Show HN: Schliff -- Quality scorer for AI instruction files

---

AI instruction files -- CLAUDE.md, .cursorrules, AGENTS.md, SKILL.md -- silently degrade as teams edit them over months. Nobody notices until agents start hallucinating or ignoring constraints.

Schliff is a deterministic, zero-dependency quality scorer for these files. It evaluates across 7 dimensions (structure, triggers, quality, edges, efficiency, composability, clarity) using only Python 3.9+ stdlib. No LLM, no API key, no network calls.

What it finds that surprises people:

- **Copy-paste examples that inflate perceived quality.** Deduplication detection drops one file from 94 to 43 after removing repeated blocks that added bulk but no signal.
- **"Always X" vs "never X" contradictions** hiding across sections of long instruction files, invisible to human reviewers.
- **Hedging language** ("you might want to consider", "it could be helpful to") that wastes agent tokens and weakens directives.
- **Missing scope boundaries** that cause agents to hallucinate responsibilities outside their intended domain.

Schliff detects 6 gaming vectors -- keyword stuffing, padding, repetition, structural inflation, contradictory filler, and scope bleed -- so scores reflect actual instruction quality, not surface polish.

The optional autonomous improvement loop (requires Claude Code, invoked via `/schliff:auto`) can take a file from 54 [D] to 98 [S] grade in a single pass, rewriting weak sections while preserving intent. This is opt-in and not required for scoring.

Integrate into CI like Codecov -- fail PRs that drop instruction quality below your team's threshold.

We scored 100+ public skill files and found 73% grade below C -- most AI instruction files in the wild have significant quality gaps.

732 tests, MIT licensed, no API key needed: https://github.com/Zandereins/schliff

What dimensions matter most for instruction quality?

---

## Comment Strategy

Prepared responses for the 5 most likely HN questions.

### 1. "Why not just use a linter like ruff?"

Ruff and similar linters check syntax and style of *code*. Schliff scores the *semantic quality* of natural-language instruction files. These are fundamentally different problems. A linter can tell you a markdown file is well-formed. It cannot tell you that your instructions contradict themselves in section 3 vs section 7, that 40% of your content is duplicated filler, or that your scope boundaries are missing -- causing agents to invent responsibilities. Think of it as the difference between checking Python syntax and measuring whether your docstrings actually help someone use the API.

### 2. "This seems over-engineered for a markdown file"

It would be, if these files stayed small. In practice, team-maintained instruction files grow to 500-2000 lines over months. At that scale, contradictions creep in, sections get copy-pasted between projects, and nobody audits whether directives still make sense together. The 73% below-C finding from scoring 100+ public files is not because people write bad instructions -- it is because nobody has tooling to catch the decay. A one-time review does not help. CI-integrated scoring does.

### 3. "Why deterministic instead of LLM-based scoring?"

Three reasons. First, reproducibility: the same file always produces the same score, so you can track quality over time and gate PRs on it. An LLM evaluator gives different scores on different runs. Second, speed: scoring takes milliseconds, not seconds. Third, zero infrastructure: no API keys, no costs, no rate limits, no data leaving your machine. The optional LLM-based improvement loop is a separate step -- scoring itself is pure computation.

### 4. "How does this compare to prompt engineering tools?"

Prompt engineering tools help you write prompts for API calls -- single-shot inputs to an LLM endpoint. Schliff scores persistent instruction files that shape agent behavior across entire sessions or codebases. Different artifact, different failure modes. A prompt might be too vague; an instruction file might have 12 contradictions across 800 lines. The scoring dimensions (structure, triggers, quality, edges, efficiency, composability, clarity -- plus optional security) are specific to long-lived instruction documents, not ephemeral prompts.

### 5. "Score inflation / gaming?"

This was a design priority from day one. We implemented 6 anti-gaming detection vectors: keyword stuffing, padding with empty content, repetition of blocks, structural inflation through unnecessary nesting, contradictory filler that adds words without meaning, and scope bleed. If you try to game the score by adding bulk, the anti-gaming dimension actively penalizes you. We have seen files drop 30+ points when gaming detection kicks in. The goal is to make the score trustworthy enough for CI gates -- if it were gameable, it would be useless.
