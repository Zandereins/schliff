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

3. If `duplicate_copies` is non-empty, report it **above** the table — the CLI
   renderer prints it there, and the two surfaces should not disagree on shape.
   The same skill installed twice (typically a plugin present in both
   `plugins/cache/` and `plugins/marketplaces/`) is counted once:

   ```
   N skills are installed more than once (M extra copies, counted once).
   Which copy is counted is arbitrary — name every path in the group and let
   the reader pick the one they control before acting on it.
   ```

   Do not explain the whole `skills_discovered` − `skills_found` gap as
   duplicates: a skill that fails to score widens it too. The duplicate share is
   the sum over `duplicate_copies[].also_installed_at`; the rest is `failed`.
   Result rows carry an `also_installed_at` too, but only on rows that scored —
   summing those undercounts whenever a duplicated skill failed.

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
