---
name: schliff:doctor
description: >
  Run a health check on all installed skills. Scans skill directories, scores
  each skill structurally, and produces a summary table with grades and
  actionable recommendations. Zero arguments needed.
---

# /schliff:doctor

Run a comprehensive health check on all installed skills.

## Instructions

1. Run the doctor script:

   ```bash
   python3 scripts/doctor.py --json
   ```

2. Parse the JSON output and present results as a readable table:

   ```
   === Schliff Doctor ===

   Scanning installed skills...

   | Skill | Score | Grade | Issues | Action |
   |-------|-------|-------|--------|--------|
   | my-skill | 85 | A | 0 critical | Healthy |
   | debug | 62 | C | 2 warnings | Run /schliff:analyze |
   | deploy | 45 | D | 3 critical | Needs improvement |

   Summary: X skills scanned, Y healthy, Z need attention
   ```

3. If `duplicate_copies` is non-empty, report it under the table. The same skill
   installed twice (typically a plugin present in both `plugins/cache/` and
   `plugins/marketplaces/`) is counted once, so `skills_found` is lower than
   `skills_discovered` — say so, or the drop looks like skills went missing:

   ```
   N skills are installed more than once (M extra copies, counted once).
   Which copy is counted is arbitrary — name every path in the group and let
   the reader pick the one they control before acting on it.
   ```

4. For skills with grade D or F, suggest specific next steps:
   - "Run `/schliff:init <path>` to set up improvement tracking"
   - "Run `/schliff:analyze <path>` for detailed gap analysis"

5. If `--verbose` flag is provided, show per-dimension breakdowns for each skill.

## Flags

- `--verbose`: Show per-dimension scores for each skill
- `--skill-dirs DIR...`: Override default scan directories

## Notes

- Default scan directories: `~/.claude/skills/` and `.claude/skills/`
- Uses structural scoring only (no runtime eval needed)
- Quick to run — takes ~5-10 seconds for most installations
