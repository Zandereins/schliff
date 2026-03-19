# SkillForge 🔨

> **Autonomous skill improvement engine** — the autoresearch loop applied to Claude Code skills.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Claude Code Skill](https://img.shields.io/badge/Claude_Code-Skill-blue?logo=anthropic&logoColor=white)](https://docs.anthropic.com/en/docs/claude-code/skills)
[![Based on](https://img.shields.io/badge/Based_on-Karpathy's_Autoresearch-orange)](https://github.com/karpathy/autoresearch)

---

## The Problem

You have a Claude Code skill. It kind of works. But:

- It doesn't trigger for the right prompts
- Output quality is inconsistent
- Edge cases crash or produce garbage
- It's bloated with instructions Claude already knows
- You don't know what "good" looks like, let alone how to measure it

**SkillForge fixes this.** Set a goal, start the loop, walk away.

## How It Works

SkillForge applies [Karpathy's autoresearch pattern](https://github.com/karpathy/autoresearch) — constraint + metric + autonomous iteration — to the meta-problem of **improving skills themselves**.

```
You provide: a skill to improve
SkillForge does: analyze → baseline → [improve → verify → keep/discard → log → repeat]
You get: a measurably better skill + detailed improvement report
```

**The loop:**

```
LOOP (FOREVER or N iterations):
  1. Review current skill + eval results + improvement log
  2. Pick ONE improvement based on gap analysis
  3. Apply atomic change to SKILL.md or references
  4. Git commit (before verification)
  5. Run eval suite → compute quality score
  6. Score improved → keep. Worse → git revert. Crash → fix or skip.
  7. Log result to skillforge-results.tsv
  8. Repeat.
```

Every improvement stacks. Every failure auto-reverts. Progress is tracked.

## Quality Dimensions

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| **Structure** | 15% | Frontmatter, progressive disclosure, organization |
| **Trigger accuracy** | 25% | Activates for right prompts, silent for wrong ones |
| **Output quality** | 25% | Following the skill produces correct results |
| **Edge coverage** | 15% | Handles unusual inputs gracefully |
| **Token efficiency** | 10% | Minimal instructions, maximum effect |
| **Composability** | 10% | Works well with other skills |

## Quick Start

### 1. Install

```bash
git clone https://github.com/Zandereins/skillforge.git

# Project-local
cp -r skillforge/skills/skillforge .claude/skills/skillforge
cp -r skillforge/commands/skillforge .claude/commands/skillforge

# Or global
cp -r skillforge/skills/skillforge ~/.claude/skills/skillforge
cp -r skillforge/commands/skillforge ~/.claude/commands/skillforge
```

### 2. Analyze a Skill

```
/skillforge:analyze
Target: .claude/skills/my-skill/SKILL.md
```

### 3. Improve Autonomously

```
/skillforge
Target: .claude/skills/my-skill/SKILL.md
Goal: Improve trigger accuracy from ~60% to 90%+
Iterations: 30
```

### 4. Check Results

```
/skillforge:report
```

## Commands

| Command | What It Does |
|---------|-------------|
| `/skillforge` | Full autonomous improvement loop |
| `/skillforge:analyze` | Deep skill analysis with recommendations |
| `/skillforge:bench` | Establish quality baseline (iteration #0) |
| `/skillforge:eval` | Run evaluation suite |
| `/skillforge:report` | Generate improvement summary |

## Example: Improving a Deploy Skill

```
/skillforge
Target: .claude/skills/deploy/SKILL.md
Goal: All test cases pass, trigger accuracy 90%+
```

SkillForge will:

1. **Analyze** — read the skill, score structure, find gaps
2. **Baseline** — score all 6 dimensions as iteration #0
3. **Loop** — make one change per iteration:
   - Iteration 1: Expand trigger description with synonym → +5 trigger → **keep**
   - Iteration 2: Add error handling for missing Dockerfile → +3 edge → **keep**
   - Iteration 3: Compress verbose setup instructions → -1 quality → **discard** (auto-revert)
   - ...continues until goal met or interrupted...

## Architecture

```
skillforge/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── skills/
│   └── skillforge/
│       ├── SKILL.md                ← Core skill
│       ├── references/
│       │   ├── improvement-protocol.md
│       │   ├── metrics-catalog.md
│       │   └── skill-patterns.md
│       ├── scripts/
│       │   ├── analyze-skill.sh    ← Structural linter
│       │   └── score-skill.py      ← Quality scorer
│       └── templates/
│           ├── eval-suite-template.json
│           └── improvement-log-template.tsv
└── commands/
    └── skillforge/
        ├── analyze.md
        ├── bench.md
        ├── eval.md
        └── report.md
```

## Design Principles

Extracted from [Karpathy's autoresearch](https://github.com/karpathy/autoresearch):

1. **Constraint = Enabler** — Bounded scope (one skill), fixed metrics (6 dimensions), atomic changes
2. **Metrics Must Be Mechanical** — If you can't score it with a script, you can't improve it autonomously
3. **One Change Per Iteration** — Atomic. If it breaks, you know exactly why
4. **Automatic Rollback** — Failed changes revert instantly via `git revert`
5. **Git as Memory** — Every kept change committed, agent reads history to learn patterns
6. **Separate Strategy from Tactics** — Human sets the goal, agent executes iterations

## Chaining with skill-creator

SkillForge and Anthropic's `skill-creator` are complementary:

- **skill-creator** builds v1 — captures intent, writes the draft, runs initial test cases with human review
- **SkillForge** grinds v1 to production — autonomous loop, mechanical metrics, overnight improvement

**Recommended workflow:** `skill-creator` → build v1 → `skillforge` → grind to 90%+ → ship

## Key Difference from Existing Autoresearch Skills

Existing autoresearch skills improve **code, content, or configurations**. SkillForge improves **skills themselves** — it's a meta-skill that makes other skills better. This is the missing piece: a systematic way to iterate on the instructions that guide Claude's behavior.

## Inspiration & Credits

- **[Andrej Karpathy](https://github.com/karpathy)** — [autoresearch](https://github.com/karpathy/autoresearch): the original 630-line autonomous ML experiment loop
- **[Udit Goenka](https://github.com/uditgoenka)** — [autoresearch](https://github.com/uditgoenka/autoresearch): generalized autoresearch for Claude Code
- **[Anthropic](https://anthropic.com)** — [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills system

## Contributing

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
