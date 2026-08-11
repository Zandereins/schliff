# Plan — Plugin-Kanal-Experiment

Decided in a grilling session on 2026-08-11. Six decisions, recorded in the summary at the
bottom of this file. This plan executes steps 1–5 of that summary; step 6 (submitting to
third-party marketplaces) is explicitly out of scope and waits for Franz's go-ahead.

## Context

schliff is ROUTE B — maintained-but-parked. A demand bet was cashed RED on 2026-08-04, but its
measuring instrument had been switched off, so the demand question was left *unanswered* rather
than answered. This experiment answers it, with a pre-registered kill criterion, and doubles as
a reputation artifact because the pre-registration is the part nobody can supply after the fact.

Measured on 2026-08-11 (14-day window, snapshot preserved in the task 1 brief):

- **111 views from 32 unique visitors.**
- Referrers: `github.com` 9 uniques, Google 2, DuckDuckGo 1 — **three humans arrived via search**.
- **No referrer traffic from awesome-claude-code**, although schliff is listed there twice.
- 1579 clones / 330 uniques — CI noise; the test matrix clones five times per run.
- 13 stars, 1 fork. The fork is `webbrain-one`, an account with 13 728 repos created
  2026-06-21: a mass-fork bot, not a user.

The gap the experiment attacks: `.claude-plugin/marketplace.json` exists and is complete, so
schliff is installable as a Claude Code plugin — and the README never says so. It offers
`pip install` and `uvx` for a Claude Code tool whose audience installs via `/plugin`.

## Global Constraints

- **Zero runtime dependencies.** The repo's own description promises it. Anything added here
  uses the Python standard library or the already-present `gh` CLI. No new package in
  `pyproject.toml`.
- **Nothing leaves the machine.** No push, no PR, no submission to any third-party repository.
  This plan ends with commits on the local branch `feat/plugin-channel-experiment`.
- **Repo conventions bind:** `ruff check skills/schliff/scripts/` clean; markdownlint clean for
  tracked `.md` (run from the repo root, where the ignore patterns apply); the full unit suite
  green via `/usr/bin/python3 -m pytest tests/unit` from `skills/schliff`.
- **No claim without execution.** Every assertion about behaviour is backed by a command that
  was run, with its output. This is the house rule that produced the last three releases.
- **The measurement is perishable.** GitHub serves a rolling 14-day traffic window. A snapshot
  taken on 2026-08-11 already exists (see Task 1); nothing may overwrite or discard it.

## Task 1 — Traffic collector

Write `scripts/collect-traffic.sh` (repo root `scripts/`, beside the existing `scripts/launch/`).
It appends one JSON object per run to `docs/experiments/plugin-channel/traffic.jsonl`.

Requirements:

- Uses `gh api` for `traffic/views`, `traffic/clones`, `traffic/popular/referrers`,
  `traffic/popular/paths`, plus repo-level `stargazers_count`, `forks_count`,
  `subscribers_count`.
- One line per run, with a top-level `collected_at` in UTC ISO-8601 and the raw API payloads
  nested under named keys. Raw payloads, not derived numbers: the analysis can change later,
  the observation cannot be retaken.
- **Idempotent per day:** running it twice on the same date must not append a second line for
  that date. Overwrite the day's line or skip — either is fine, but say which in a comment and
  make the behaviour visible in the test.
- Fails loudly: `set -euo pipefail`, and a non-zero exit if `gh` is missing or unauthenticated.
- POSIX-portable `grep`/`sed` usage only — the repo already carries a regression test
  (`test_install_version.py`) for GNU-only escapes in shipped shell scripts, and that rule
  applies here.

Seed the file with the 2026-08-11 baseline, which is already captured as raw JSON at
`/private/tmp/claude-501/-Users-franzpaul-schliff/13c97124-3f48-4e0a-8b20-f23ec43a3f4a/scratchpad/baseline/`
(`views.json`, `clones.json`, `popular_referrers.json`, `popular_paths.json`, `repo.json`).
The seeded line carries `collected_at` of the snapshot moment and a `"note": "baseline"` field.

Add a test at `skills/schliff/tests/unit/test_collect_traffic.py` that asserts the script's
POSIX portability the same way `test_install_version.py` does, and that the seeded JSONL parses
and contains the baseline line. Do not invoke `gh` from the test.

## Task 2 — Pre-registered specification

Write `docs/specs/2026-08-11-plugin-channel-experiment.md` in the house spec style (see
`docs/specs/2026-08-07-credential-gate-decision-brief.md` for tone and structure).

It must state, before any measure is taken:

- The hypothesis in one sentence, and what would falsify it.
- The baseline numbers from the Context section above, with their collection date.
- **Gate 1 — distribution.** At least one of N qualified marketplaces merges a submission
  within 21 days of submission. N and the qualified list come from Task 4. Failure verdict:
  `RED-DISTRIBUTION` — a finding about the channel, not about demand.
- **Gate 2 — demand.** Within 30 days of the first acceptance: at least one qualitative signal
  from a stranger (issue, question, PR, or a mention that is not a bot) **or** unique visitors
  ≥ 3× baseline (≥ 96 per 14-day window). Failure verdict: `RED-DEMAND` — and that one is
  final, because it is measured.
- Why the two verdicts are separated: the 2026-08-04 bet died at the gatekeeper and never
  reached the demand question, which is what made its verdict unusable.
- What is deliberately *not* done: no announcement round, no second Show HN. The 2026-07-13
  finding stands — a post from a cold account has no reach, and content was never the problem.
- How it will be judged and by whom, so the result cannot be reinterpreted afterwards.

## Task 3 — README: the plugin path first

Rewrite the installation section of `README.md` so the Claude Code plugin path is the **first**
option a reader meets, before `uvx` and `pip install`.

- Show the actual command a user types. Verify it against the real mechanism before writing it:
  `.claude-plugin/marketplace.json` is in the repo root, so the marketplace source is the
  repository itself. Do not guess the syntax — check how an installed marketplace in
  `~/.claude/plugins/` is declared, and state in the report what you verified it against.
- Keep `uvx` and `pip install` — CI users and pre-commit users need them. This is a reordering
  and an addition, not a removal.
- The README hero block is a reproducible promise: it shows live `schliff score AGENTS.md`
  output including the version banner. If your edit touches it, re-verify byte-equality against
  the real command and report the diff.
- Markdownlint must stay clean from the repo root.

## Task 4 — Qualify the distributors

Research only. Produce `docs/experiments/plugin-channel/distributors.md`.

Qualification criterion, applied identically to every candidate: a marketplace qualifies when
**at least two distinct external authors have merged PRs in the last 90 days**. "External"
means not the repository owner. The point is to measure demand, not gatekeeper willingness —
submitting to repositories that never merge outside contributions would repeat the design flaw
that made the 2026-08-04 bet uninformative.

- Start from these, already measured on 2026-08-11 — re-verify rather than trusting the numbers:
  `trailofbits/skills-curated` (480★, merged PRs from 4 distinct authors),
  `obra/superpowers-marketplace` (1204★, **0** distinct external authors across 46 open),
  `MadAppGang/claude-code` (278★, 1 author, last push 2026-03-15).
- Search for further candidates (`gh search repos "claude-code plugin marketplace"` and
  variations). Cover at least ten candidates in total.
- For each: stars, last push, count of distinct external authors with merged PRs in 90 days,
  whether a documented submission process exists (CONTRIBUTING, issue template, README section),
  and a QUALIFIED / NOT QUALIFIED verdict with the number that decided it.
- End with the qualified list and its count — this is the N that Task 2's Gate 1 refers to.
- Note explicitly if fewer than three qualify: that is itself a finding about the channel and
  must not be smoothed over.

## Out of scope

Submitting to any marketplace. Pushing the branch. Opening a PR. Publishing anything. Those
follow only after Franz reviews the result.

## The six decisions this plan implements

1. **Goal:** a measurable demand experiment *and* a reputation artifact — both.
2. **Instrument:** GitHub traffic plus referrers, saved regularly against the 14-day expiry.
3. **Measure:** own README first, third-party distributors second — a maintainer who opens a
   README with no plugin path sees a Python package, not a Claude Code plugin.
4. **Kill criterion:** two gates, separate verdicts, `RED-DISTRIBUTION` ≠ `RED-DEMAND`.
5. **Reputation:** the pre-registered spec now; an article only once a result exists.
6. **Gate 1:** qualify distributors first, then fix N — measuring against repositories that
   never merge outside work is not a measurement.
