# Detectors miss the thing itself when the file states it instead of describing it

**Status:** specified · **Branch:** `fix/structural-signal-detection` · **Found:** 2026-08-13, on `main` at `fc487fb`, schliff v8.11.1

Four detectors — one in `efficiency`, three in `composability` — search for an English
*phrasing*. A file that provides the *thing* rather than a sentence about it scores zero on
all four. This is one defect class with four sites, not four defects.

## Symptom

`skills/schliff/SKILL.md` scores 87.4 [A] with two weak dimensions. Neither is caused by
missing content.

```
$ schliff score skills/schliff/SKILL.md
  efficiency     ███████░░░   72/100  fair
  composability  █████░░░░░   46/100  poor
```

### efficiency 72 — 14 command lines counted as zero

`_RE_ACTIONABLE_LINES` (`scripts/scoring/patterns/base.py:55`) matches English imperative verbs
at line start. Executed against the file's body:

```
=== ACTIONABLE LINES MATCHED ===
  53: 3. Apply them, then `uvx schliff score <file>` to confirm the delta.
  71: Use when measuring or gating the quality or honesty of an instruction

=== COMMAND-BEARING LINES NOT COUNTED ===  -> 14
  11: - `uvx schliff score <file>` — score one instruction file, ...
  27: $ uvx schliff score SKILL.md
  51: 1. `uvx schliff doctor --skill-dirs <dir>` — find the worst file.
```

`signal_count` is 16 where the content supports ~40; `density` lands at 2.97 and misses the
conciseness bonus threshold of 3.0 by 0.03. A line that *is* an executable command is the most
actionable line a document can contain, and it scores nothing because it starts with a backtick.

The incentive runs backwards: writing *"Run the score command"* earns points, writing
`uvx schliff score` does not. For a tool whose stated value is anti-gaming, that is a defect
against the core claim.

### composability 46 — three detectors miss content that is literally present

Five checks of 10 points each report `no match`. Three of them fire against text that is in
the file:

| Check | Line | Text present | What the regex demands |
| --- | --- | --- | --- |
| `ERROR_BEHAVIOR` | 84 | "Errors go to stderr as one line with a non-zero exit." | `on error` / `if X fails` |
| `VERSION_COMPAT` | 37 | "Pin the version in CI: `uvx schliff@8.8.2`" | `version >= N` / `minimum version` |
| `DEPENDENCY_DECL` | 25 | "These run anywhere `uv` is available" | wordlist python/node/npm/pip/git/jq/bash/ruby/go — **`uv` absent** |

30 of the 54 lost points are demonstrably misassigned.

## Scope

**In scope:** `_RE_ACTIONABLE_LINES` (efficiency) and the three composability detectors above.

**Out of scope:** `_RE_IDEMPOTENCY` and `_RE_NAMESPACE_ISOLATION`. Measured across
`benchmarks/corpus/v1` (21 files), hit rates are error 4/21 · idempotency 1/21 · dependency 3/21
· namespace 4/21 · version_compat 0/21 — but neither idempotency nor namespace has a single
demonstrated false negative. No measurement accuses them, so they are not touched. Tidying
around a fix is how this repo has introduced defects before.

**A non-conclusion, recorded so it is not re-derived:** `version_compat` at 0/21 is *not* a dead
detector. Checked — the 17 real SKILL.md files in the corpus carry no version information at all;
the `v8.0`/`v8.1` hits live only in corpus metadata (README, LABELS) and denote schliff releases.
The detector measures a real absence there correctly. Its false negative is at line 37 of
schliff's own file, and that one alone justifies the change.

## Requirements

1. A line carrying an executable shell command counts as an actionable signal, regardless of how
   it begins — bullet, numbered item, `$` prompt, or inline backtick span.
2. `ERROR_BEHAVIOR` recognises a stated error contract: exit status and/or stderr as the failure
   channel.
3. `DEPENDENCY_DECL` recognises a declared tool prerequisite without depending on a closed
   wordlist of tool names.
4. `VERSION_COMPAT` recognises a version pin (`tool@1.2.3`) as a compatibility statement.
5. No file's score may fall. See *Verification*.
6. `skills/schliff/SKILL.md` is not edited. It is the instrument here, not the target.

## Technical decisions

**Structural, not lexical.** Detect the thing, not a phrasing of it. This is the only approach
that does not reproduce the defect class — a longer wordlist is the same design with more entries,
and the next file that phrases it differently falls through again.

**Location: existing pattern modules, no new module.** Command-line recognition next to
`_RE_ACTIONABLE_LINES` in `patterns/base.py`; the three signals in `patterns/skill_md.py`.
`efficiency` asks "does this line carry a command", `composability` asks "does this file name an
error contract" — two questions, not a shared abstraction. A `scoring/signals.py` would be a seam
that exists only because we drew it.

**`command_resolution.py` is not reusable — measured, not assumed.** It extracts only resolvable
families (make, npm/yarn/pnpm, script paths) because its purpose is resolution against a repo:

```
$ _extract_commands(SKILL.md body)  ->  extracted: 0
```

**Anti-gaming: inherit, do not invent.** Command lines feed the same signal pool as
`actionable_lines`, under the existing `min(…, 20)` cap and the existing dedup — but keyed on the
**normalised command**, not on line text. Without that, `uvx schliff score` counts three times
(command list, example, workflow).

**Normalisation keeps subcommands, drops arguments and version pins.** Verified the hard way: a
first draft truncating to two tokens collapsed all eight `uvx schliff …` invocations into one
signal. `uvx schliff score <file>` normalises to `uvx schliff score`; `uvx schliff@8.8.2 verify`
and `uvx schliff verify` are the same command.

**Minimum form: at least two tokens.** A single word in backticks is a tool mention, not a
command line. Without this, "These run anywhere `uv` is available" contributes `uv` as a command —
a false positive the first measurement produced immediately.

## The counterexample pair refuted the design — measured 2026-08-13

The pair was built and run. It did not settle the weight question; it invalidated the approach
the weight question assumed.

**Red is redder than predicted.** This spec previously claimed both files would sit at efficiency
72, indistinguishable. Wrong — they differ, in the wrong direction:

```
$ schliff score tests/fixtures/command-signal/deserves.md --format skill
  efficiency  78/100      actionable_lines: 1   words: 411   density: 3.16
$ schliff score tests/fixtures/command-signal/dump.md --format skill
  efficiency  84/100      actionable_lines: 1   words: 350   density: 4.29
```

`actionable_lines: 1` in **both** — the detector sees the same thing in 7 documented commands and
in 7 trivial ones. The dump scores **6 points higher** purely because it is shorter.

**No weight rescues it.** Prototyped the agreed design (dedup on normalised command, minimum two
tokens) and swept the weight. deserves.md has 9 distinct commands, dump.md has 8:

| weight | deserves | dump | |
| --- | --- | --- | --- |
| today | 79 | 84 | dump wins |
| ×1 | 88 | 93 | dump wins |
| ×2 | 96 | 100 | dump wins |
| ×3 | 100 | 100 | ceiling, tie |

**Root cause, one level below the detector:** `density = signal_count / total_words`
(`efficiency.py:155`). The dump wins because it is shorter. Every word of explanation lowers the
density, so the formula penalises documenting. Adding a command signal type scales that problem
instead of fixing it — the detector fix is necessary and not sufficient.

**The rejected option is the only one that separates them.** Counting only *documented* commands
(command plus explanatory text on the same line) — rejected during design in favour of inheriting
the existing mechanism — is the sole variant where the good file wins, and only from ×2:

| weight | deserves | dump | |
| --- | --- | --- | --- |
| ×1 | 88 | 89 | dump wins |
| ×2 | 96 | 93 | deserves wins |
| ×3 | 100 | 96 | deserves wins, at the ceiling |

The margin is thin (3 points at ×2) and deserves.md hits 100 at ×3, so the separation rests on
the denominator staying as it is. Dedup is also still missing from that prototype: deserves.md's 9
include `imgaudit scan` and `imgaudit policy` twice.

**Open, for decision:** whether to count only documented commands, or to change the denominator
so length is not itself a penalty. Not decided unilaterally — the second option reaches into the
scoring formula every dimension consumer depends on, and the monotonicity invariant (requirement 5)
is not obviously survivable there.

## Verification

**Red command — built and red, 2026-08-13.**
`skills/schliff/tests/fixtures/command-signal/{deserves,dump}.md`, same section structure, same
frontmatter, differing only in whether the commands are real and documented:

```
$ schliff score .../deserves.md --format skill | grep efficiency   ->  78/100
$ schliff score .../dump.md     --format skill | grep efficiency   ->  84/100
```

Red = the dump outscores the documented file. Green = `deserves.md` rises **and** overtakes
`dump.md`. Both files score 4/7 dimensions (no eval suite beside them), so the composite is capped
at 42 % and is not the measure here — efficiency is.

**Regression, with a hard invariant:** score all 21 files in `benchmarks/corpus/v1` before and
after. **No file may fall.** This fix removes false negatives — it only ever adds recognition. A
file that drops means the change reaches further than the measurement accuses, which is a bug in
the fix, not a finding about the file. The invariant doubles as protection for users running
`uvx schliff verify --min-score N` in CI.

**Not admissible as evidence:** schliff's own composite moving from 87.4. Every change here raises
it. The proof has to come from files nobody wrote for this test.

## Result — implemented and measured 2026-08-13

Full suite: **2115 passed**. Monotonicity held on every substrate; **no file fell anywhere**.

| substrate | files | rose | fell |
| --- | --- | --- | --- |
| `benchmarks/corpus/v1` | 21 | 0 | 0 |
| `docs/launch/corpus/agents` | 30 | 5 | 0 |
| installed skills under `~/.claude` | 299 | 16 (6 distinct) | 0 |
| composability, all three combined | 350 | 18 | 0 |

The benchmark corpus moving **0** is itself a finding: it contains no list line with a backticked
command at all, so it cannot validate this change. The evidence comes from the other two.

Verified by hand, not by count — the AGENTS.md movers document real commands
(`composer install|test|analyse`, `make credo|lint-js|server`, `pnpm build|format|check:all`,
`npm run dev|create-widget`, `git add .|commit|push`).

**Own files:** SKILL.md efficiency 72 → 95, composability 46 → 76, composite 87.4 → **93.0**.
AGENTS.md unchanged at 95.6 [S].

**Four defects the field measurement found that fixtures did not.** Each is pinned by a test:

1. A dependency table aligned with trailing spaces inside backticks
   (`` `coverlet.collector     ` : … ``) read as "program + argument" and credited a package
   name as a command.
2. `token.split("@")` turned the scoped package `@vercel/microfrontends` into an empty token, so
   `npx @a/x run` and `npx @b/y run` collapsed onto one identity (`npx  compile`).
3. `\s` in the dependency pattern crosses newlines: `…needs them.\n5. Next step` matched as
   "needs \<tool\> \<version\>" against the next line's list number.
4. `[\w.-]+@\d+\.\d+` has no literal prefix, so the unbounded run is **O(n²)** — 18.1 → 72.2 →
   288.0 ms, ratio 4.00× per doubling. Caught by `test_patterns_scale_linearly`, bounded to 64.

The golden distribution in `test_agents_md_profile.py` was re-baselined (mean 61.53 → 61.99, one
C→B) with the five movers named in the test comment.

## B — the denominator, measured (not implemented)

Confirmed as a real defect, and it is not a bloat penalty.

`signal_count` is capped on every term: `min(actionable,20)*3 + min(examples,3)*5 +
min(why,5)*2 + min(verification,5)*2`. Its **maximum is 95**. The denominator, `total_words`, is
unbounded. So:

- `density ≥ 10` (score 95) is unreachable above **950 words**
- `density ≥ 3` (the conciseness bonus) is unreachable above **3167 words**

— regardless of quality. Across 349 files, correlation between word count and efficiency is
**−0.477**, and the median falls monotonically: 70 (300–600 words) → 61 → 58 → **42** (>2400).

The decisive evidence is the files sitting at the absolute cap:

| file | words | signal_count | efficiency |
| --- | --- | --- | --- |
| `skill-creator` | 5151 | **95 (maximum)** | 42 |
| `hydra` | 11110 | **95 (maximum)** | 44 |
| `skill-development` | 3143 | 89 | 51 |

`skill-creator` emits the most signal the formula can represent and scores 42, while a
350-word file of `ls -la` and `echo done` scores 96. That is a structural ceiling, not a
judgement about density. 21 files are at the actionable cap, where further documented commands
change nothing.

### B measured in full — 2026-08-13, after A landed

**A correction to an earlier draft of this section.** It claimed A had halved the length
effect (correlation −0.245, `skill-creator` at 62). Both numbers came from a hand-rebuilt
copy of the scoring curve that omitted the bloat penalty (`total_words > 2000 and
density < 3 → −15`). Measured against the real `score_efficiency`, correlation after A is
**−0.477**, unchanged, and `skill-creator` scores **42**. A did not reduce B at all. The
relative ranking of the variants below survives — every variant was computed on the same
incomplete curve — but the cap value had to be recalibrated, see below.

**The counter-hypothesis is refuted.** If long files were simply worse, every dimension would
sag together. Median score by length, efficiency against the mean of structure, clarity and
composability:

| words | n | efficiency | other three dims |
| --- | --- | --- | --- |
| 0–300 | 40 | 65 | 68 |
| 300–600 | 69 | 70 | 72 |
| 600–1200 | 99 | 61 | 71 |
| 1200–2400 | 100 | 58 | 74 |
| >2400 | 41 | **42** | **74** |

The other three *rise* with length (68 → 74). Efficiency falls (70 → 42). The gap widens from
3 points to 32. That is a length effect, not a quality effect.

**Scope: 182 of 349 files (52 %)** cannot reach score 95 at any quality, because
`max(signal_count) = 95` against an unbounded denominator. 21 sit at the actionable cap where
further documented commands change nothing.

**Four denominator variants, same criteria:**

| variant | corr(len) | median | files that fall | files ≥95 | skill-creator | hydra |
| --- | --- | --- | --- | --- | --- | --- |
| today | −0.245 | 63 | 0 | 18 | 62 | 59 |
| cap denominator at 1500 | **−0.004** | 65 | **0** | **18** | 82 | 86 |
| scale the signal caps with length | −0.206 | 63 | 0 | 18 | 67 | 68 |
| sqrt denominator | +0.056 | 67 | **75** | 12 | 79 | 76 |

`sqrt` fails the monotonicity invariant outright. Scaling the caps barely moves the
correlation — the caps were never the main term, the denominator is.

**Cap calibration, redone against the real scorer** (the first pass used the incomplete curve
above and put the zero crossing at 1500; it is not there):

| cap | none | 2500 | 2000 | 1750 | **1500** | 1250 | 1000 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| corr(len) | −0.477 | −0.347 | −0.280 | −0.251 | **−0.204** | −0.073 | +0.090 |
| files ≥95 | 18 | 18 | 18 | 18 | **18** | 22 | 23 |
| files that fall | 0 | 0 | 0 | 0 | **0** | 0 | 0 |

The zero crossing is near **1150**, not 1500. Caps below ~1400 buy the remaining correlation
by inflating the top band (18 → 22 → 23 files at ≥95), which trades a length bias for a score
bias and moves a ceiling that nothing measured asks to move.

**1500 is the conservative end**: it halves the length effect (−0.477 → −0.204) and leaves the
top band exactly where it was. The residual is partly a *second* length effect not addressed
here — the bloat penalty keys on raw `total_words`, so it fires on long files whose density the
cap has already corrected.

The counterexample pair still holds: `deserves.md` 98 > `dump.md` 96.

**A prediction in this spec was wrong.** It said the monotonicity invariant was "unlikely to
survive" a denominator change. It survives by construction: `min(words, cap) ≤ words`, so
density can only rise, so no score can fall. Measured 0 fallers, as the algebra requires.

Still not implemented — this section is the measurement, and the decision is Franz's.

## Follow-up, agreed but not in this branch

`schliff doctor` counts test fixtures and vendored directories as installed skills —
`doctor skills/` reports `2 skills scanned | 2 healthy` and `~9,888 tokens` in a repo with one
skill, because `tests/fixtures/self-skill-baseline/SKILL.md` is scanned. A SKILL.md also sits
under `playground/.venv/lib/python3.12/site-packages/`; in a user's repo that would be
`node_modules` and `.venv`. Next after this.

Two smaller items, unowned: `commands/schliff/analyze.md` step 7 documents
`run-eval.sh <skill> --eval-suite <suite>`, which exits `Error: unknown option --eval-suite` — the
real signature is positional. And `doctor`'s "Total context cost" sums SKILL.md plus
`references/*.md` (`shared.py:142`) while the score beside it measures only the SKILL.md, so the
same file reads 7,748 tokens in one output and 1,044 in the other. That one is a labelling
question, not an arithmetic error.
