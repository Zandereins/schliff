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

Not designed or implemented here. Any fix reaches the formula every dimension consumer depends
on, and the monotonicity invariant is unlikely to survive it — raising long files means the
distribution moves, which is a scale change, not a false-negative repair.

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
