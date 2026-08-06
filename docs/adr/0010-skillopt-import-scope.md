# ADR 0010: Import three items from SkillOpt; reject the activation harness

- Status: accepted
- Date: 2026-08-06

## Context

`microsoft/SkillOpt` (MIT, audited 2026-08-06 at `9639719`) trains a skill document as the
state of a frozen agent. A full read of the tree produced four candidate imports:

- **F1** — the keep/revert gate in `auto-improve.py` accepts an edit when schliff's own
  composite rises, the same rubric `text_gradient.py` inverted to generate that edit.
- **F2** — `runtime-evaluator.py:54-69` embeds the skill as untrusted text inside a prompt.
  There is no `--plugin-dir` and no skills-dir install anywhere under
  `skills/schliff/scripts/`, so the skill is force-fed and selection never happens.
  SkillOpt's `adapters/superpowers.py` instead clones a host at a pinned SHA, overlays the
  candidate, and loads it through the real plugin bootstrap.
- **F3** — `scoring/security.py` has negation- and code-block-awareness but zero credential
  patterns. An instruction file with a live API key scores silently.
- **F4** — `evolve/sanitize.py` bounds its GitHub token patterns at exactly 36 characters and
  covers only `ghp_` (`:19`) and `gho_` (`:20`); SkillOpt uses `gh[pousr]_[A-Za-z0-9]{20,}`.
  The ODBC `Pwd=` spelling is absent. *(Two earlier drafts overstated this gap. `AIza` and
  `gho_` are already present at `sanitize.py:25` and `:20`; `Password=` is already redacted by
  the generic assignment catcher at `:41`, which lists `password`/`passwd` in its name
  alternation — executing the shipped `redact_secrets` on a connection string confirms it. The
  verified residual delta is exactly: the `ghu_`/`ghs_`/`ghr_` prefixes, the exact-36 length
  bound, and `Pwd=`.)*

Three further candidates were checked and **refuted**: schliff's `command_resolution.py` is
stricter than SkillOpt's `skill_resolver.py` (it refuses to claim absence without proof),
`auto-improve.py:435` already handles the unmatched-edit case that SkillOpt needed two test
files to fix, and `evolve/sanitize.py` already carries `sk-ant-`, which SkillOpt lacks.

The standing constraint is Route B: schliff is maintained-but-parked, the demand bet was
cashed RED on 2026-08-04, and no active user drives any of these requirements.

## Decision

Build F3, F1 and F4, in that order. Do not build F2.

## Why

The three survivors each have a justification that does not depend on user count. F3 protects
against a harm that does not scale with adoption — a committed credential damages the one
person who has it, immediately and irreversibly. F1 repairs a measurement that reports false
wins, which is a defect in the core promise regardless of who is watching. F4 is a narrow
correctness fix to patterns that already exist.

F3 leads rather than F1 because `auto-improve` is not a subcommand of the shipped CLI — there
is no hit in `cli.py` — and `/schliff:auto` is barred from unattended use until PR-B lands.
The lying gate sits on a path nobody currently runs unsupervised, so its damage is
hypothetical today. F3 sits on `score` and `verify`, which are the surfaces actually in use.

## Rejected

**F2, the activation harness.** It is not an import but a new subsystem: clone, pin, bootstrap,
rule-based judges, evidence collection. It is the most expensive item, it introduces new attack
surface (the evaluated agent gets Bash as the same OS user, so evidence is tamper-*evident*,
not tamper-proof), and it introduces permanent maintenance load through a pinned host that
goes stale. Under Route B none of that is honestly justifiable. The finding it rests on stands
and is recorded — schliff's runtime evaluator measures a fragment, not the substrate — but
recording a finding is not the same as funding its fix.
