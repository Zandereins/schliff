---
name: schliff:auto
description: >
  Run the autonomous self-driving improvement loop. Scores the skill, generates
  improvement gradients, applies deterministic patches, re-scores, and keeps or
  reverts changes automatically. Stops on plateau detection or target reached.
---

# /schliff:auto

Run the autonomous, script-driven improvement loop on a skill.

## Instructions

1. Identify the target skill path from the user's message. If not provided, ask:
   "Which skill should I auto-improve? Give me the path to its SKILL.md."

2. Verify prerequisites:
   - SKILL.md exists and is readable
   - An eval suite exists (`eval-suite.json` in the skill directory)
   - The skill directory is inside a git repository (required for revert-on-regression)

   If eval suite is missing: "Run `/schliff:init <path>` first to generate an eval suite."

3. Run the autonomous improvement loop. The driver is not on the `uvx` command
   surface — it ships as a script inside this plugin directory, so give its path
   from the schliff checkout root. The script resolves its own imports, so any
   working directory is fine:

   ```bash
   python3 skills/schliff/scripts/auto-improve.py /path/to/SKILL.md --json
   ```

4. Monitor output and present progress as it runs. With `--verbose` the driver
   prints one line per iteration and a summary block at the end — report what it
   actually emitted, do not reformat it into invented numbers:

   ```
   Iter  1:  ██████░░░░░░░░░░░░░░  29.3/100  [-0.7]  ✗ discard (composability)

     Schliff Auto-Improve Complete
     ──────────────────────────────────────────────────
     Score:  29 → 29/100  ██████░░░░░░░░░░░░░░  (+0.0)  [F]
     Iters:  3  |  Kept: 0  |  Time: 0s
     Stop:   max_iterations
   ```

5. After completion, show the summary from the JSON output.

## Flags

- `--max-iterations N`: Maximum number of improvement iterations (default: 30)
- `--dry-run`: Show what would be changed without modifying files
- `--json`: Emit the run summary as JSON
- `--verbose` / `-v`: Print each iteration to stderr as it happens

There is no resume flag. Re-running on the same skill appends to the state file
below rather than truncating it, and iteration numbers continue upward from the
last recorded run — so an interrupted session's iterations stay readable, but a
second run is a second run, not a continuation of the first one's decisions.

## Stopping Conditions

The loop stops automatically when:

- Composite score reaches 98+
- Every measured dimension reaches 90+ (dimensions reported as `-1` are unmeasured
  and do not count)
- EMA-based ROI stays below 0.1 across the last 5 keep/discard iterations
- Three consecutive iterations error — the file is treated as not patchable
- Maximum iterations reached

## Where the run is recorded

- `<skill-dir>/.schliff/auto-improve-state.jsonl` — one line per iteration:
  `iteration`, `status` (`baseline` / `keep` / `discard` / `error`), `composite`,
  `dimensions`, `delta`, `patch_applied`, `timestamp`. This is the loop's own
  state file. It is not the same file as `verify --history`, which defaults to
  `.schliff/history.jsonl` and records gate results, not iterations.
- `~/.schliff/meta/episodes.jsonl` — cross-session memory. Before iterating, the
  loop recalls the top 3 past episodes for this skill; after a run it stores the
  outcome. This is what makes a second session on the same skill start informed
  rather than cold.

## Sequential only

When the loop detects it is stuck — 5+ consecutive discards, or a gap to target
above 15 points — it reports the condition and **keeps going sequentially**. It
does not branch, and it creates no git worktrees. If you see
`Triggering parallel branching…` in the output, that is the trigger firing, not
work being distributed. Do not promise the user parallel candidate branches here.

## Notes

- Each iteration makes ONE atomic change, scores, and keeps or reverts
- File changes are NOT auto-committed to git — commit yourself to preserve them
- Deterministic patches (frontmatter fixes, TODO cleanup) are applied directly
- Non-deterministic improvements may invoke Claude for generation
- Use `--dry-run` to preview without modifying files
