# Known gaming limits: disclose, don't patch

Status: decided 2026-10-19 (owner). Score-neutral: no scorer changes.

## Goal

Make the anti-gaming claim in `docs/SCORING.md` true again. Two gaming vectors are open,
and every measured fix fails. So the claim is narrowed, the vectors are documented and
tests pin them, and the conditions for revisiting are written down.

## Context

A review of the next step (2026-10-19) found that a probe padding a skill with
`### Example N` blocks gained +10 `structure`. Isolated, the cause was not the headers or
the blocks but `_RE_REAL_EXAMPLES` (`scoring/patterns/skill_md.py:42-44`), which counts
occurrences. A second review found a sibling vector in `efficiency`. Both were measured
by two multi-agent workflows (`wf_b4c0a515-b2e`, `wf_cf333929-bea`) and the options were
grilled with the owner.

`SCORING.md` promised protection against "repeating near-duplicate instructions".
Efficiency deduplicates on the first 80 characters, lowercased, so lines identical there
are caught. Lines that differ within them, even by one digit, are not.

## The vectors

Re-measured on this branch through the scorer functions:

| Vector | Base | Gamed |
| --- | --- | --- |
| `e.g. e.g.` appended to `benchmarks/anti-gaming/skills/clean-reference.md` | structure 85, efficiency 95, composite 31.9 | structure 95, efficiency 100, composite 34.1 |
| 10 lines `- Check item i` appended to `benchmarks/corpus/v1/phase0-snapshot/01-webapp-testing.SKILL.md` | efficiency 86 | efficiency 100 |

Field maxima, re-measured 2026-10-21 in the PR review with `cli.py score --json`, same
payloads appended to each file. AGENTS files are written as `AGENTS.md` so the format is
detected; under their corpus names they detect as `unknown` and the gains about halve.

| Field | Example vector (`e.g. e.g.`) | Imperative vector (10 lines) |
| --- | --- | --- |
| 263 unique `SKILL.md` under `~/.claude` | max +7.4, mean +1.7, 216 gain | max +6.9, mean +1.9, 244 gain |
| 30-file AGENTS corpus (`docs/launch/corpus/agents/`) | max +15.8, mean +4.1, 23 gain | max +13.0, mean +4.1, 27 gain |
| 15 `SKILL.md` files in `benchmarks/corpus/v1` (`--format skill`) | max +7.9 | max +6.3 |

The v1 row leaves out `08-Nemp-memory.SKILL.md`, which is frontmatter only. Its body is
empty, so it scores 0.0 and any body lifts it (`hello world` alone gives 23.4). Its
apparent gains (+17.9, +29.7) measure that empty-body floor, not the vectors.

The minimum is slightly negative in the first two rows (-0.7 to -0.2) and 0.0 to -0.1
in the v1 row: files already at the ceiling lose a little density. The example gain comes mostly from `efficiency`
(3 markers × 5 signal, `efficiency.py:154`), not from `structure`. On zixindh's AGENTS.md
structure goes 75 → 85 (0.4 × 10 = 4 composite) and efficiency 35 → 94 (about 11.8).
The earlier workflow figure of +6.2 on an agents.md was one file, not the maximum.

The benchmark suite in `benchmarks/anti-gaming/` has no vector for either one.

## Options measured

Field = 284 unique `SKILL.md` under `~/.claude` (sha256-deduplicated) plus the 30-file
AGENTS corpus. Counts are from `wf_cf333929-bea`.

| Counter | Option | Own bypass | Field files lowered |
| --- | --- | --- | --- |
| example | A1/A2: the 10-point tier needs structural examples | 49 characters of fenced lorem, or two varied 5-word blocks | 61-76 SKILL, 9 AGENTS |
| example | B: dedupe prose markers, cap them at 5 | `Example 1: run the linter` / `Example 2: open the log file` | 53-63 SKILL |
| example | C: a marker counts only if the text after it is distinct and has content | two throwaway sentences after `e.g.` | 0-1 |
| imperative | A1/A2: a line needs content tokens | number words, `Check module alpha/beta` | 7-31 SKILL, 0-3 AGENTS |
| imperative | B: novelty or a cap on credit | plausible sentences reach 100 | 1-23 SKILL |
| imperative | E/F: tie lines to headings, or saturating credit | a heading noun; F leaves the maximum alone | 113-141 of 314 |

No option closes its vector: each has the bypass in its row, or (F) leaves the maximum
in place. Every option except example-C lowers legitimate files, which makes it a Major
under ADR 0017; C lowers 0-1 and is still bypassed. A
lexical predicate here moves the gaming to a new string without stopping it.

## Decisions

1. Don't patch either counter. Narrow the claim in `SCORING.md` and add "Known gaming
   limits", which names the class and the measured maximum. The recipes stay here.
2. Pin both vectors in `skills/schliff/tests/unit/test_known_gaming_limits.py`. Each pin
   is mutation-checked: removing the prose markers from `_RE_REAL_EXAMPLES` turns only
   the example pin red. Capping actionable credit at 12 lines turns only the imperative
   pin red. The imperative pin asserts the gain, not the base, because the base also
   earns example credit.
3. Park the Major track. Re-open only when gaming of either kind turns up in a real file
   someone else wrote: the field corpus, a user issue, or Action output. A red-team
   vector of our own doesn't count, because its value is already measured here.
4. Any future predicate counts as a Minor only if it lowers **zero** field files, and
   only if a fresh red-team round finds no bypass under 100 characters that keeps at
   least half the gain.

## Open questions

- A content-meaning check (validity, not lexis) would be the real fix. It's out of
  scope until the re-open condition fires.
