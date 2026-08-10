# ADR 0017: Score-neutral behaviour changes ship as a minor release

- Status: accepted
- Date: 2026-08-06

## Context

The credential gate introduces a new failure condition: a build that is green today can turn
red tomorrow. `action.yml:22-25` shows `schliff-version` defaulting to `''`, so Action users
pick up the change on their next run without acting. Pre-commit users are pinned through
`rev:` and move only when they bump.

That looks like grounds for a major. It is not, because of what the change deliberately does
not touch.

## Decision

Ship as **8.11.0**, a minor. Three separate pull requests — F3 (the gate), F1 (the gradient
target check and the split), F4 (the redaction patterns) — landing in one release.

The policy this sets: score-neutral changes ship as minors; a change that moves the composite
would be a major.

Required alongside the release:

- a CHANGELOG entry under an explicit **BREAKING BEHAVIOUR** heading, not under *Added*
- a CLI test proving the red path: `verify` exits non-zero on a credential fixture. The
  matching `action-selftest.yml` fixture is a **post-release follow-up** and cannot be part of
  this release — see ADR 0014 for why
- the README pinning recommendation raised to the new version
- the **three version constants** moved in lockstep, since
  `tests/unit/test_version_consistency.py` asserts all three are equal and fails the build
  otherwise: `pyproject.toml:7`, `.claude-plugin/plugin.json:3`, and
  `skills/schliff/__init__.py:3` — the last is the value `schliff version` actually prints
  (`cli.py:1009`, reading `__version__` per `cli.py:41`), and an earlier draft omitted it
- separately, the **README/docs occurrences** including the badge cache-bust. These are
  cosmetic and untested, which is why they are not one of the three constants

## Why

ADR 0011 made the gate score-neutral precisely so the version contract would survive it.
Composites, badges, comparisons and every pinned `--min-score` threshold behave identically
before and after. What changes is one narrow failure condition that fires only where a
structurally valid vendor token is present — and there, a red build is the correct answer, not
a contract violation.

New detection rules in minor releases is the established convention for linters; Ruff ships
them the same way. A major would signal that scores or interfaces moved, provoking exactly the
migration anxiety that score-neutrality was chosen to avoid.

The CHANGELOG heading carries the honesty the version number does not. Filing a new red-build
condition under *Added* would be the mislabelling this project's conventions exist to prevent.

Three PRs rather than one because the gate — with its Action change and self-test fixture —
needs a fundamentally different review from a regex addition in `evolve/sanitize.py`.

## Rejected

**Major 9.0.0.** Signals a score or interface break that did not happen, and invites everyone
to audit a migration that consists of nothing.

**One combined PR.** Bundles an unrelated regex change into a review that should concentrate on
a security gate and a CI surface.

**Three separate releases.** Three lockstep version bumps and three badge cache-busts for two
internal changes nobody can observe from outside.
