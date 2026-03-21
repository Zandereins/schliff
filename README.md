# SkillForge

**The self-driving skill engine for Claude Code.**

Point it at a SKILL.md. Walk away. SkillForge improves it autonomously — applies fixes, learns which strategies work, stops when ROI drops, and remembers across sessions. Zero human input.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests: 51/51](https://img.shields.io/badge/Tests-51%2F51_passing-brightgreen)](skills/skillforge/scripts/test-integration.sh)
[![Score: 99.9](https://img.shields.io/badge/Structural_Score-99.9%2F100-blue)](skills/skillforge/scripts/score-skill.py)
[![v5.0](https://img.shields.io/badge/Version-5.0-F59E0B)](CHANGELOG.md)
[![Claude Code Skill](https://img.shields.io/badge/Claude_Code-Skill-8A2BE2)](https://docs.anthropic.com/en/docs/claude-code/skills)

---

## Why SkillForge

| What exists today | What SkillForge does |
|:---|:---|
| Manual skill editing by feel | **Auto-Apply** — deterministic patches apply themselves, no LLM needed |
| Blind iteration (guess, check, revert) | **Strategy Predictor** — learns which strategies work BEFORE trying |
| Static scores disconnected from reality | **Runtime Scoring** — 7th dimension validates actual Claude behavior |
| Skills as isolated files | **Mesh Evolution** — detects conflicts AND generates fixes automatically |
| Failures vanish when session ends | **Episodic Memory** — remembers learnings across weeks of sessions |
| One change at a time, sequential | **Parallel Branching** — 3 strategies via git worktrees, keep the best |

---

## The Self-Driving Loop

```
$ python3 scripts/auto-improve.py my-skill/SKILL.md

--- Iteration 1 ---
Applying: [structure] missing_name → insert_before at line 1
Score: 62.5 → 68.0 (delta: +5.5) ✓ Keep

--- Iteration 2 ---
Applying: [composability] no_scope_boundaries → append
Score: 68.0 → 72.0 (delta: +4.0) ✓ Keep

--- Iteration 3 ---
Applying: [efficiency] filler_phrases → remove_regex
Score: 72.0 → 70.5 (delta: -1.5) ✗ Discard (revert)

...

Stopping: marginal ROI < 0.2 for 3 consecutive windows

Auto-Improve Complete
  Iterations:  18
  Improvements: 12
  Score:       62.5 → 94.3 (+31.8)
  Stop reason: roi_diminishing
```

No Claude session needed. No human in the loop. Deterministic patches (frontmatter, noise removal, TODO cleanup) are applied directly. The system reverts regressions, logs everything, and stops when returns diminish.

---

## Quick Start

**Prerequisites:** Python 3.9+, Bash, Git, jq

### Install (project-local)

```bash
git clone https://github.com/Zandereins/skillforge.git
cp -r skillforge/skills/skillforge .claude/skills/skillforge
cp -r skillforge/commands/skillforge .claude/commands/skillforge
```

### Install (global — all projects)

```bash
git clone https://github.com/Zandereins/skillforge.git
cp -r skillforge/skills/skillforge ~/.claude/skills/skillforge
cp -r skillforge/commands/skillforge ~/.claude/commands/skillforge
```

### Verify

```bash
cd skillforge/skills/skillforge
python3 scripts/score-skill.py SKILL.md --json           # Score any skill
python3 scripts/auto-improve.py SKILL.md --dry-run       # Preview auto-improve
python3 scripts/text-gradient.py SKILL.md --top 5         # See ranked fixes
python3 scripts/skill-mesh.py --json                      # Scan for conflicts
python3 scripts/episodic-store.py --test                   # Verify memory store
bash scripts/test-integration.sh --no-runtime-auto         # 51/51 passing
```

### Use in Claude Code

```
/skillforge                          # Autonomous improvement loop
/skillforge:auto                     # Self-driving auto-improve (no prompts)
/skillforge:analyze                  # What's wrong with my skill?
/skillforge:mesh                     # Check all skills for conflicts
/skillforge:mesh-evolve              # Conflicts + auto-generated fixes
/skillforge:predict                  # Which strategy will work best?
/skillforge:recall                   # What worked last time for similar skills?
```

---

## v5.0 — The Self-Driving Engine

### 6 Breakthrough Features

#### 1. Auto-Apply Gradients

60-70% of all improvements are deterministic — frontmatter fixes, noise removal, TODO cleanup. These don't need an LLM. `text-gradient.py --apply` patches them directly.

```bash
python3 scripts/text-gradient.py SKILL.md --apply          # Apply fixes
python3 scripts/text-gradient.py SKILL.md --apply --dry-run # Preview first
```

#### 2. Strategy Predictor

Before trying a strategy, predict its success rate from cross-session data. Groups history by `(domain, strategy_type, gap_bucket)` and computes `P(keep | strategy)`.

```bash
python3 scripts/meta-report.py --json   # Shows predictor + calibration data
```

#### 3. Runtime Scoring (7th Dimension)

Opt-in dimension that invokes Claude with test prompts and checks actual output. Auto-calibrates dimension weights from runtime correlations.

```bash
python3 scripts/score-skill.py SKILL.md --json --runtime   # Include runtime dim
```

#### 4. Mesh Evolution

Mesh doesn't just detect problems — it generates fixes. Negative boundaries for overlap, scope-narrowing for collisions, skill stubs for broken handoffs.

```bash
python3 scripts/skill-mesh.py --json --incremental   # Cached, only recomputes changes
```

#### 5. Episodic Memory

Lightweight semantic search over past improvements. TF-IDF recall across sessions. Size-capped with automatic consolidation.

```bash
python3 scripts/episodic-store.py --recall "trigger accuracy low" --top-k 5
python3 scripts/episodic-store.py --synthesize "trigger improvement"
python3 scripts/episodic-store.py --stats
```

#### 6. Parallel Branching + ROI Stopping

When stuck (5+ discards) or gap > 15 points: try 3 strategies in parallel via git worktrees, keep the best. Stop automatically when ROI drops below threshold.

```bash
python3 scripts/parallel-runner.py SKILL.md --auto --json   # Auto-pick top 3
python3 scripts/parallel-runner.py SKILL.md --dry-run        # Preview plan
```

---

## Quality Dimensions

7 dimensions (6 core + runtime opt-in), weights auto-calibrate from data:

| Dimension | Default Weight | Measures | Limitation |
|:---|:---:|:---|:---|
| **Structure** | 15% | Frontmatter, organization, progressive disclosure | Cannot assess instruction correctness |
| **Trigger Accuracy** | 20% | Keyword overlap with eval prompts (TF-IDF) | Does not predict actual Claude triggering |
| **Output Quality** | 20% | Eval suite coverage and assertion breadth | Does not verify runtime output quality |
| **Edge Coverage** | 15% | Edge case definitions in eval suite | Does not verify handling at runtime |
| **Token Efficiency** | 10% | Information density, signal-to-noise ratio | Cannot assess content usefulness |
| **Composability** | 5% | Scope boundaries, handoff points | Cannot verify multi-skill interaction |
| **Runtime** *(opt-in)* | 15% | Actual Claude output vs assertions | Expensive, requires `claude` CLI |

Weights auto-calibrate from `~/.skillforge/meta/calibrated-weights.json` when runtime data is available. Override with `--weights "triggers=0.4,structure=0.3"`.

---

## Commands

| Command | Purpose |
|:---|:---|
| `/skillforge` | Full autonomous improvement loop |
| `/skillforge:auto` | Self-driving auto-improve (deterministic patches) |
| `/skillforge:analyze` | Deep analysis with gap identification |
| `/skillforge:bench` | Establish quality baseline |
| `/skillforge:eval` | Run evaluation suite |
| `/skillforge:report` | Generate improvement summary with diffs |
| `/skillforge:mesh` | Scan all skills for conflicts and overlaps |
| `/skillforge:mesh-evolve` | Mesh + auto-generated fix actions |
| `/skillforge:predict` | Predict best strategy from history |
| `/skillforge:recall` | Search episodic memory for relevant learnings |
| `/skillforge:triage` | Cluster failures, auto-generate fixes |
| `/skillforge:log-failure` | Manually log a skill failure |

---

## Architecture

```
skillforge/
├── skills/skillforge/
│   ├── SKILL.md                      # Core skill definition (99.9/100)
│   ├── eval-suite.json               # 25+ assertions, triggers, edge cases
│   ├── scripts/
│   │   ├── auto-improve.py           # Self-driving autonomous loop (v5.0)
│   │   ├── score-skill.py            # 7-dimension scorer + auto-weights
│   │   ├── text-gradient.py          # Scorer inversion → fix list + auto-apply
│   │   ├── skill-mesh.py             # Conflict detection + evolution actions
│   │   ├── meta-report.py            # Strategy predictor + auto-calibration
│   │   ├── episodic-store.py         # Cross-session TF-IDF memory (v5.0)
│   │   ├── parallel-runner.py        # Git worktree parallel experiments (v5.0)
│   │   ├── run-eval.sh               # Eval runner + meta emission
│   │   ├── progress.py               # Convergence + strategy + episode emit
│   │   ├── runtime-evaluator.py      # Live Claude invocation testing
│   │   └── test-integration.sh       # 51 integration tests
│   ├── hooks/                        # SessionStart failure surfacing
│   ├── references/                   # Improvement protocol, metrics catalog
│   └── templates/                    # Eval suite + log templates
├── commands/skillforge/              # Slash commands
└── .claude-plugin/                   # Plugin manifest
```

### Data Flow

```
SKILL.md → score-skill.py → text-gradient.py → auto-improve.py
                ↓                                      ↓
         meta-report.py ← strategy-log.jsonl ← progress.py
                ↓                                      ↓
    calibrated-weights.json              episodic-store.py → episodes.jsonl
                                                       ↓
                                         parallel-runner.py (when stuck)
```

---

## Self-Score

SkillForge scores itself — dogfooding the tool it builds.

| Metric | Value |
|:---|:---|
| Structural Score | **99.9 / 100** |
| Dimensions measured | **6/7** (runtime opt-in) |
| Binary assertions | **25/25 passing** |
| Integration tests | **51/51 passing** |
| Journey | v1.0 (62.5) → v5.0 (99.9) across 5 major versions |

---

## What Makes This Different

No existing tool combines all 6 patterns:

1. **Auto-Apply** (inspired by Ralph-Loop) — gradients apply themselves
2. **Strategy Prediction** (inspired by ECC-Instincts) — learn before trying
3. **Runtime Truth** (inspired by GSD Nyquist) — scores based on real behavior
4. **Mesh Evolution** (inspired by CARL Domains) — skill library self-organizes
5. **Episodic Memory** (inspired by Episodic Memory Plugin) — compound knowledge
6. **Parallel Branching** (inspired by GSD Multi-Agent) — 3x search space

Autoresearch repos iterate blindly. Skill-Creator generates once. SkillForge iterates, learns, remembers, and scales — autonomously.

---

## Ecosystem

**Complementary tools:**
- **[skill-creator](https://github.com/anthropics/courses/tree/master/claude-code/09-skill-creator)** builds v1 → **SkillForge** grinds v1 to production
- **[autoresearch](https://github.com/karpathy/autoresearch)** (Karpathy) — the original autonomous experiment loop
- **[autoresearch](https://github.com/uditgoenka/autoresearch)** (Goenka) — generalized autoresearch for Claude Code

**Workflow:** `skill-creator` → build v1 → `/skillforge:auto` → autonomous grinding → ship

---

## Contributing

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
