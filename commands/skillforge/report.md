---
name: skillforge:report
description: >
  Generate a comprehensive improvement report for a skill that has been
  through one or more SkillForge improvement cycles. Summarizes baseline
  vs current scores, lists top impactful improvements, shows experiment
  velocity, and recommends next steps.
---

# /skillforge:report

Generate a post-improvement summary report with advanced analytics.

## Instructions

1. Read `skillforge-results.jsonl` from the skill directory.

2. Parse all iterations and compute:
   - Baseline scores (iteration 0)
   - Current best scores (highest composite from kept iterations)
   - Total iterations run
   - Keep/discard/crash ratio
   - Per-dimension improvement delta and trend (improving/stable/declining)
   - Binary eval pass rates across kept experiments
   - Experiment velocity (experiments per hour)

3. Identify top 5 most impactful improvements by:
   - Sorting kept iterations by delta (composite score change)
   - Including timestamp, commit hash, description, and delta

4. Generate the report in markdown format:

```markdown
# SkillForge Improvement Report

## Skill: [name]
## Date: [today]
## Iterations: [N total] ([K kept] / [D discarded] / [C crashed])

### Executive Summary

**Experiment Velocity:** [X.X experiments/hour]
**Time Elapsed:** [HH:MM:SS]
**Success Rate:** [X%] (kept / total)

### Score Summary

| Dimension | Baseline | Current | Delta | Trend |
|-----------|----------|---------|-------|-------|
| Structure | XX | XX | +XX | ↑/→/↓ |
| Triggers | XX | XX | +XX | ↑/→/↓ |
| Quality | XX | XX | +XX | ↑/→/↓ |
| Edges | XX | XX | +XX | ↑/→/↓ |
| Efficiency | XX | XX | +XX | ↑/→/↓ |
| Composability | XX | XX | +XX | ↑/→/↓ |
| **Composite** | **XX** | **XX** | **+XX** | **↑** |

### Binary Eval Performance

Latest 5 kept iterations (pass rate):
- Exp [N]: [X/Y]
- Exp [N]: [X/Y]
- ...

### Top 5 Most Impactful Improvements

1. **Exp [N]** [commit] — [description]
   - Composite: XX → XX (+X.X)
   - Timestamp: [ISO]

2. **Exp [N]** [commit] — [description]
   - Composite: XX → XX (+X.X)
   - Timestamp: [ISO]

... (up to 5)

### What to Try Next

Based on analysis of kept experiments:

- **Focus Areas:** [dimension with largest remaining gap or steepest decline]
- **Momentum:** [Current streak info: N consecutive keeps/discards]
- **Recommendation:** [Specific actionable suggestion based on patterns]
  - If improving: Continue optimizing [dimension]
  - If stable: Try novel approach in [dimension]
  - If declining: Investigate regression in [dimension], revert recent changes

### Raw Metrics

- Total duration: [HH:MM:SS]
- Average per iteration: [SS.S]s
- Peak composite: XX/100 (exp [N])
- Current streak: [N] [keeps/discards]

---

*Report generated: [ISO timestamp]*
```

5. Save the report as `skillforge-report.md` in the skill directory.

6. If `present_files` is available, share the report with the user.

## Implementation Details

### Parsing JSONL Format

Each line in `skillforge-results.jsonl` is a JSON object:
```json
{
  "exp": 0,
  "timestamp": "2026-03-19T10:30:45Z",
  "commit": "abc1234f...",
  "scores": {
    "structure": 85.5,
    "triggers": 92.0,
    "quality": 78.5,
    "edges": 81.0,
    "efficiency": 88.0,
    "composability": 75.0
  },
  "pass_rate": "18/20",
  "composite": 86.8,
  "delta": 2.5,
  "status": "keep",
  "description": "improved trigger logic",
  "duration_ms": 45200
}
```

### Computing Trends

For each dimension across kept iterations:
- Split experiments into early half and late half
- Calculate average score for each half
- Classify as: improving (+2% or more), stable (within 2%), declining (-2% or more)

### Top Impactful Improvements

Sort kept iterations by `delta` field (composite score change from previous kept baseline):
1. Select top 5 by magnitude
2. Display in order of experiment number (chronological)
3. Include commit hash for traceability

### Experiment Velocity

Calculate as:
```
velocity = (total_experiments) / (total_duration_seconds / 3600)
```

Shows how many experiments per hour the improvement loop is achieving.

### Recommendations Algorithm

1. **If current composite >= 90:** Celebrate progress, focus on edge cases
2. **If improving trend on all dimensions:** Continue current strategy
3. **If one dimension declining:** Investigate regression, review recent changes
4. **If stable across dimensions:** Consider novel approaches
5. **If high crash rate (>10%):** Review crash logs, simplify hypotheses
6. **If low keep rate (<25%):** Improve hypothesis generation or scoring

