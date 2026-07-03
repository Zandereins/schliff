# Field case study: Hydra (multi-perspective review council)

**Target:** [Zandereins/hydra](https://github.com/Zandereins/hydra) — a production
Claude Code skill (1,000+ line SKILL.md orchestrating up to 10 agents).
**Engine:** released `schliff==8.4.0` from PyPI. **Date:** 2026-07-03.
**Change PR:** [hydra#34](https://github.com/Zandereins/hydra/pull/34).

## Result

| | Score | Grade | Driver |
| --- | --- | --- | --- |
| Baseline (7 dims, eval suite) | 71.0 | C | edges 82, composability 56, efficiency 47 |
| After | 76.5 | B | edges **100**, composability **81** |

Every applied change was **purely additive** — no operational instruction or
bash block was touched:

- **edges 82 → 100:** the eval suite now ships in the repo, extended with two
  edge cases that pin *real, documented* behaviors instead of invented ones —
  the state.json tamper guard (`malformed_input`) and windowed review on huge
  diffs (`scale_extreme`).
- **composability 56 → 81:** explicit positive+negative scope block, dependency
  declaration (bash/git; Codex CLI for deep mode; gtimeout), and the
  idempotency guarantee (timestamped reports, never mutates reviewed code) —
  all statements verified true before writing.

## Informed decline (as important as the fixes)

`efficiency` stayed at 47: the SKILL.md is ~14k tokens against the 1,000-token
budget. Hydra inlines its orchestration bash **deliberately** — extracting it
to `references/` would trade runtime correctness risk for a score. A measured
decline, documented instead of gamed. It also surfaces a real product
limitation: the token budget treats orchestrator mega-skills and leaf skills
identically.

## What the field study gave back to schliff

1. **Bug found:** the dead-marker detector false-positives on the word
   "placeholder" in instructional prose ("Replace all `{{...}}` placeholders…")
   and advises deleting load-bearing instructions —
   [schliff#93](https://github.com/Zandereins/schliff/issues/93). Same defect
   class as the operational_coverage prose-homonym hole fixed in #83.
2. **Calibration insight:** a single token budget per format cannot express the
   leaf-skill vs. orchestrator-skill difference.

## Method (reproducible)

```bash
pip install schliff==8.4.0
schliff score SKILL.md --eval-suite eval-suite.json   # in the hydra repo
schliff suggest SKILL.md --eval-suite eval-suite.json
```

Discipline: measure first and let the tool set priorities; only truthful
statements enter the file; declines are documented with reasons; every number
above is current-engine output, not memory.
