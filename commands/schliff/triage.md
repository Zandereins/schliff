---
name: schliff:triage
description: >
  Cluster logged failures by skill and failure type, identify top issues,
  and auto-generate eval cases and SKILL.md fixes for the most impactful
  failures. Reads from .schliff/failures.jsonl.
---

# /schliff:triage

Cluster and prioritize logged failures, then generate targeted fixes.

## Instructions

1. Locate the failure log:
   ```bash
   cat .schliff/failures.jsonl 2>/dev/null | head -5
   ```
   If empty or missing: "No failures logged yet. Use `/schliff:log-failure` to record issues, or failures are auto-logged during eval runs."

2. Load and parse all failure entries. Each entry has:
   ```json
   {"skill": "skill-name", "failure_type": "trigger|quality|edge|crash", "description": "what went wrong", "timestamp": "ISO-8601", "context": "optional details"}
   ```

3. Cluster failures by `skill` + `failure_type`. Count occurrences per cluster.

4. Sort clusters by count (descending). Present the top issues:
   ```
   === Schliff Failure Triage ===

   Total failures: N (across M skills)

   | # | Skill | Type | Count | Sample Description |
   |---|-------|------|-------|--------------------|
   | 1 | deploy | trigger | 12 | "Triggered on non-deploy requests" |
   | 2 | debug | quality | 8 | "Missing root cause analysis step" |
   | 3 | tdd | edge | 5 | "Crashed on empty test file" |
   ```

5. For the top 3 clusters, generate targeted fixes:
   - **Trigger failures**: Generate new negative trigger entries for the eval suite
   - **Quality failures**: Identify the missing instruction or example in the SKILL.md
   - **Edge failures**: Generate edge case entries for the eval suite
   - **Crash failures**: Identify the unhandled input and suggest a guard clause

6. If `text-gradient.py` is available, run it to generate concrete patches:
   ```bash
   python3 scripts/text-gradient.py /path/to/SKILL.md --focus "failure_description" --json
   ```

7. Present recommended actions:
   ```
   Recommended Actions:
   1. [skill-name] Add 3 negative triggers to eval-suite.json (trigger cluster)
   2. [skill-name] Add error handling for empty input (edge cluster)
   3. [skill-name] Add step for root cause analysis (quality cluster)
   ```

8. Offer to auto-apply the highest-impact fix:
   "Should I apply fix #1 now? This will update the eval suite with new negative triggers."

## Notes

- Failures are logged by `/schliff:log-failure` or automatically during eval runs
- The session hook (`session-injector.js`) surfaces untriaged failures at session start
- After fixes are applied, re-run `/schliff:eval` to verify improvement
