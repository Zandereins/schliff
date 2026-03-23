---
name: schliff:log-failure
description: >
  Log a skill failure for later triage. Records the failure with context
  to .schliff/failures.jsonl for clustering and analysis by /schliff:triage.
---

# /schliff:log-failure

Manually log a skill failure for later triage and analysis.

## Instructions

1. Ask the user for failure details (if not provided in the message):
   - **Skill name**: Which skill failed?
   - **Failure type**: One of `trigger` (wrong activation), `quality` (bad output), `edge` (unhandled input), `crash` (error/exception)
   - **Description**: What went wrong? (1-2 sentences)
   - **Context** (optional): Any additional details (input that caused it, expected vs actual behavior)

2. Validate the failure type is one of the known types:
   ```
   trigger | quality | edge | crash
   ```
   If unknown, suggest the closest match.

3. Construct the failure entry:
   ```json
   {
     "skill": "skill-name",
     "failure_type": "trigger|quality|edge|crash",
     "description": "what went wrong",
     "context": "additional details or null",
     "timestamp": "2026-03-22T15:30:00Z",
     "triaged": false
   }
   ```

4. Append to the failure log:
   ```bash
   mkdir -p .schliff
   echo '<JSON_ENTRY>' >> .schliff/failures.jsonl
   ```

5. If the file exceeds 1 MB, warn the user:
   ```
   Warning: failures.jsonl is getting large. Consider running /schliff:triage
   to process and archive resolved failures.
   ```

6. Confirm the log entry:
   ```
   Failure logged:
   - Skill: [name]
   - Type: [type]
   - Description: [description]

   Run /schliff:triage to cluster and prioritize all logged failures.
   ```

## Notes

- Failures are stored in `.schliff/failures.jsonl` (project-scoped)
- The session hook automatically surfaces 3+ untriaged failures at session start
- Run `/schliff:triage` to cluster failures and generate fixes
- Each entry includes `"triaged": false` — triage marks entries as processed
