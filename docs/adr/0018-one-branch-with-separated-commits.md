# ADR 0018: F3, F1 and F4 ship on one branch with separated commits

- Status: accepted · supersedes the pull-request split in ADR 0017
- Date: 2026-08-07

## Context

ADR 0017 decided "three separate pull requests — F3 (the gate), F1 (the gradient
target check and the split), F4 (the redaction patterns) — landing in one release",
reasoning that a security gate with an Action change needs a different review from a
regex addition in `evolve/sanitize.py`.

The work is now done and that reasoning has not survived contact with it. The three
items turned out to share a spine rather than sit side by side: F4's real gap was only
visible once F3's detector forced the distinction between a precise detection set and an
aggressive redaction set (ADR 0013), and F1's target guard is what makes F3's
"score-neutral" claim checkable at all, because a gradient that reaches the wrong file
can move a score no gate is watching. Split across three pull requests, each reviewer
would see a third of the argument.

The rest of ADR 0017 is unaffected: still one minor release, still 8.11.0, still
score-neutral, still a CHANGELOG entry under BREAKING BEHAVIOUR.

## Decision

One branch, `docs/skillopt-import-adrs`, with one commit per item and a commit message
that carries that item's reasoning. The version bump stays out of it: this repo does the
bump as its own `chore(release):` commit touching `pyproject.toml`,
`.claude-plugin/plugin.json`, `skills/schliff/__init__.py`, `README.md`, `docs/README.md`
and the CHANGELOG, which is a release step rather than a feature step.

## Why

The unit a reviewer needs is the argument, not the file. Six commits on one branch put
the decisions and the code that implements them in one place, in order, and each commit
message states what the red test proved before the fix existed. That is a better review
artifact than three pull requests that each open mid-sentence.

It also matches how the decisions were actually made — as one chain, revised twice by
adversarial review — rather than pretending they were three independent pieces of work.

## Rejected

**Three pull requests, as ADR 0017 decided.** Splits an argument that reads as one, and
would land F4 as an isolated regex change whose justification lives in a different pull
request.

**One pull request with one squashed commit.** Loses the per-item reasoning, which is the
part worth keeping — several of these commits record a test that passed for the wrong
reason before it was rewritten.
