# Report unrunnable assertions instead of counting them as failures

- **Status:** accepted, implementing
- **Date:** 2026-07-29
- **Follows:** #156 (`73b53e3`) — the re-derived eval suite and the static ERE gate

## Goal

`run-eval.sh` cannot currently distinguish an assertion the skill **failed** from an
assertion `grep` **refused to run**. Both become `passed: false`, silently. Make the
second case visible, attribute it to the suite rather than to the skill, and gate
against it where schliff owns the artifact.

## Context: three symptoms, one cause

`scripts/run-eval.sh:265` evaluates every `pattern` assertion as:

```bash
if echo "$SKILL_CONTENT" | $_GREP_TIMEOUT grep -qiE -- "$assertion_value" 2>/dev/null; then
```

`grep` exits 0 on match, 1 on no match, **2 on a pattern it cannot compile**; `timeout`
exits 124. The `if` collapses everything non-zero into one branch and `2>/dev/null`
discards the reason. Measured consequences, all from 2026-07-29:

| symptom | measurement |
| --- | --- |
| 6 assertions dead on CI for months | `main` reported 113/119 on CI, 119/119 locally |
| a whole PR red for an invisible reason | 13/13 locally, 9/13 on CI |
| **a wrong published diagnosis** | claimed `init-skill.py` emits `(?i)` into user suites; it emits `(?i)` into `edge_cases`, which the grep path never reads, and `\w{4,}` into `test_cases` |

The third is the one that decided this work. The swallow does not only produce dead
tests, it produces **confident wrong statements about dead tests**, because guessing is
the only option left.

The ReDoS guard above the call does not cover this: `validate_regex_complexity("[")`
returns `(True, "ok")`. It rejects expensive patterns, not invalid ones.

## Decisions

**D1 — An unrunnable assertion is `errored`, not `failed`.** It keeps `passed: false`
and gains an `error` field, but leaves the pass-rate denominator and is **not** written
to `.schliff/failures.jsonl`.

*Why:* the pass rate answers "how much of what the suite asks does the skill deliver?"
An assertion that cannot execute asks nothing. Counting it blames the skill for a defect
in the suite — and that mis-attribution has a real consumer today: failed assertions are
appended to `failures.jsonl` (`run-eval.sh:423-433`), which `/schliff:triage` clusters
and turns into proposed SKILL.md fixes. A broken regex would generate advice about a
file that is not the problem.

**D2 — Blocking only where schliff owns the suite.** `test-self.sh` asserts
`errored == 0`. For a user's own suite the count is reported, not enforced.

*Why:* D1 shrinks the denominator, so a suite could rot toward unrunnability while its
pass rate *improves* — 1 runnable assertion out of 13 reads 100%. That is precisely the
"a gate that pins output constant cannot detect loss" failure this project has already
paid for. Enforcing it in schliff's own CI closes it where we can fix it; enforcing it
for users would break someone's CI over a typo in their suite while their skill is fine,
and would break `run-eval.sh`'s exit contract (`:514` — exit 0 means *pass rate
improved*, not *evaluation succeeded*).

**D3 — Timeouts (`124`) are treated as `errored` too.** A pattern that did not finish
did not answer the question either.

**D4 — `contains` / `excludes` get the same exit-code handling.** They use `grep -qiF`,
where a compile error is not reachable and rc 2 means I/O trouble. Uniform handling is
cheaper to read than a justified special case, and an I/O failure should not read as
"the skill lacks this string".

**D5 — The generator is not touched yet.** `init-skill.py` writes `\w{4,}` into
`test_cases`. It runs clean on both locally available greps (ugrep, BSD, rc=0) and `\w`
is a documented GNU extension — unlike `\d`, which GNU does not implement. So it is
probably fine, and *probably* is the word this spec exists to eliminate. Decide after
the first measurement, not before.

**D6 — The measurement path is a new integration step.** `test-integration.sh` already
generates real suites (17.1, 17.6) and checks that the **JSON is well-formed**. It never
runs one. Step 17.7 executes a generated suite and asserts `errored == 0` — turning the
generator's contract from *shape* into *property*, and answering D5 on the next CI run.

It asserts immediately rather than merely reporting: a red run here is the finding we
want, and a number nobody asserts is a number nobody reads.

## Non-goals

- No release. The one verified external adopter drives `uvx schliff score` / `verify`;
  `run-eval.sh` is not on that path. Rides `[Unreleased]`.
- `parallel_runner.py`'s cwd-derived repo root stays open. It is unreachable from every
  shipping entry point (`/schliff:auto` no-ops it, the CLI does not expose it), so it is
  a deletion candidate, not a hardening candidate.
- The ERE gate's strictness about `\w` is not revisited here — see D5.

## Output contract change

`pass_rate` gains `errored`; `binary_results[]` entries may carry `error`. Both are
additive. The only consumer outside `run-eval.sh` itself is `test-integration.sh:179`,
which reads `type`.

## Verification

- Red-test: put `[` in a suite → `errored: 1`, `test-self.sh` red, the assertion absent
  from `failures.jsonl`, and the pass rate computed over the remaining 12.
- Full local gate set, all seven CI steps.
- After merge, read 17.7's output on CI for the D5 answer.
