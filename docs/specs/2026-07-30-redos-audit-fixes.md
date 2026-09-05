# Bounded quantifiers: closing the ReDoS class found by the 2026-07-30 audit

Status: D1, D1a, D2, D5, D6 implemented (PR 1). D3 implemented (PR 2).
D9 implemented, D10 declined (PR 3). D7 implemented (PR 4). D8 declined.
Date: 2026-07-30
Baseline: `main` @ `ab41827`

## Goal

Close every reachable super-linear regex path found by the whole-repo security audit,
without moving a single score, and add a gate so the next one cannot land.

## Context

A trust-boundary audit of `ab41827` produced seven findings. Three of them (F1, F2, F3)
are the same defect in **five** patterns, and it is not the textbook one: **an unbounded
quantifier followed by a required literal**. No nesting, no overlapping alternation.

Four of those five are in this PR's scope; the fifth is `manifest._FM` (D3). A **sixth**
pattern, `_RE_SKILL_AS_OBJECT`, was not an audit finding at all — the new empirical gate
found it on its first run, which is the clearest evidence for that gate's value and is
not credited to the audit.

Both figures below use **one** denominator: the 167 unique compiled patterns reachable
across the engine's 21 pattern-bearing modules, measured on `main`.

- Static shape-triage flagged **62 of 167** and isolated neither of the two that
  mattered. Restricted to `scoring/patterns/*` (102 patterns) a stricter rule still
  flagged 47. Noise, not signal.
- An empirical fuzz — warm each pattern, time `.search()` against 25 pathological filler
  alphabets at doubling lengths, keep ratio ≥ 3.0 — narrowed the same 167 to **32
  candidates** and then to the reachable ones, in a single run.

`[\w/]+` before a required `\.` backtracks one character per start position, so it
is O(n²) on its own. The same shape appears as `[a-z]*[a-z]*[a-z]*` before `/`, as
`\d+` before a required word, and as `\s*` allowed to span the `\n` record
separator.

The headline number: **162.6 s of CPU for one unauthenticated `POST /api/score`**
at 25,883 bytes — inside `MAX_SKILL_CHARS` = 32 KB, whose own comment claims the cap
bounds "any residual O(n^2) hot path to well under a second".

### Why this is not a repeat report

v8.6.3 bounded a tail slice in `clarity.py` for exactly this reason, and the module
docstring has asserted the invariant ever since:

> Runs in the DEFAULT scorer set for every instruction-file format … It therefore
> executes on untrusted content up to the 1MB read cap, so its regex/loops must stay
> linear (see the bounded tail slice below).

That fix covered sub-check #1. Sub-checks #2 and #4, in the same function, were left
unbounded. **A per-sub-check fix does not generalise itself.**

## Requirements

1. Every reachable super-linear path measured in the audit becomes linear. Two numbers,
   deliberately different: the **measured** post-fix ratio must be ≈2.0 per doubling,
   while the **gate** trips at 3.0 — the slack is flake margin for a loaded CI runner,
   not tolerance for a slower fix. Actuals came in at 1.92–2.12.
2. **Zero score movement** on real data — proven, not asserted.
3. **Recall preserved** — every malicious shape that was detected before is still
   detected. Two-sided acceptance, because a one-sided "corpus byte-identical" gate
   is what let the #149 regression through. D1a shows why this requirement is not
   optional: the first attempt at this fix violated it.
4. A regression gate. **Not** "fails CI on a new unbounded quantifier" — that was the
   original wording and it describes the repo-wide static rule this spec later rejected
   on measurement (D6). What ships instead: the empirical gate fails on super-linear
   *growth* across 224 patterns, and the deterministic gate fails if any of the five
   bounded spellings is removed or tightened below its corpus maximum. An unbounded
   quantifier that happens to be harmless is not flagged by either, on purpose.
5. No change to the `grep` matcher in `run-eval.sh` (dialect-regression risk).

## Technical decisions

### D1 — Bound the quantifier; calibrate the bound from the corpus

Bounds are measured, not guessed. Longest real run per quantifier over 380 real
instruction files (installed skills, plugin payloads, `benchmarks/`, `docs/`, the
project's own files):

| quantifier | longest real run | bound chosen | headroom |
| --- | --- | --- | --- |
| `[\w/]+` (`_RE_SPECIFIC_REF`) | 58 | 256 | 4.4× |
| `[\w/.-]+` (`_RE_CONCRETE_CMD`) | 118 | 256 | 2.2× |
| `` [^`]+ `` (backtick span) | 1151 | 2000 | 1.7× |
| `\w+` after a dot | 50 | 128 | 2.6× |
| `[\w-]+` (`_RE_SKILL_AS_OBJECT`) | 19 | 64 | 3.4× |
| `[a-z]*` (`rm` flags) | 2 | 12 | 6× |
| `\d+` (digit run) | 27 | 12 → see D5 | — |

A first guess of 120 would have sat one character above a real 118-char token and
would have **truncated** a real 1151-char backtick span. That is the whole argument
for calibrating: the failure mode of a guessed bound is a silent score change.

### D1a — Bound ONLY the quantifier that causes the blowup, never whitespace

Found in self-review of the first commit, before it was pushed. That commit also bounded
`rm\s+` to `rm\s{1,8}`, `\s*` to `\s{0,8}` and similar, "for consistency" with the flag
runs and digit runs that were the real quadratic source. Enumerating the evasion classes
rather than sampling them showed the cost:

| whitespace run between `rm` and `-rf /` | 8.8.2 | first commit |
| --- | --- | --- |
| 1–8 spaces or tabs | detected | detected |
| **9, 10, 16, 40, 100** spaces | detected | **missed** |
| **9+ tabs** | detected | **missed** |

Five detections lost in a security detector, for no gain: that whitespace run is prefixed
by the literal `rm`, which limits how many start positions it is reachable from, so it
never contributed to the blowup. Verified after reverting it — `_RE_SEC_DANGEROUS_CMD`
stays linear (1.92–2.04× per doubling) even with a whitespace-run payload, and 0
detections are lost against 8.8.2.

This is the #149 defect class reproduced by me: narrowing a matcher without enumerating
its evasion classes, then checking only that the corpus verdict did not move. A corpus
check cannot see an evasion the corpus does not contain. The rule that follows:

> Bound the quantifier the measurement blames. Leave every other quantifier alone, and
> prove the bound costs nothing by walking the evasion dimension, not by sampling it.

Gate: `TestDangerousCmdWhitespaceIsNotBounded` walks whitespace-run length 1…100 for
spaces and tabs, on both sides of the flag cluster. Mutation-tested — re-introducing the
exact `\s{1,8}` mistake turns 11 assertions red.

Also refuted in the same review, by measurement rather than by argument: `\d{1,12}` in
`_RE_LENGTH_EXTENDED` does **not** lose the 27-digit case, because the match may start
anywhere inside the digit run. The suspicion was reasonable and wrong.

### D2 — The bound alone is NOT sufficient for `clarity` check #2

Measured on the 162 s payload:

| variant | time | findings |
| --- | --- | --- |
| today (unbounded, per-match) | 159,939 ms | 200 |
| bound only | 11,906 ms | 200 |
| bound + hoist | **58.9 ms** | 200 |

The residual O(m·n) is the match-independent work sitting inside
`for match in matches`: the `context` join, the `_RE_BACKTICK_REF` test, and the
`_RE_SPECIFIC_REF` search do not depend on `match`, so they run once per vague
reference instead of once per line. Hoisting them is output-identical by
construction, and verified so on 250 real files (0 differing vague-reference lists).

Rejected: slicing `context` / `rest` to a fixed window. It is a second behaviour
change on top of a fix that already measures score-neutral, and D1+D2 make it
unnecessary.

### D3 — `manifest.py`: read the head, drop the unused body

`_FM = r"^---\s*\n(.*?)\n---\s*\n"` is O(n²) because `\s*` may consume newlines:
every `\s*` length restarts the lazy `(.*?)` scan.

**The class must exclude the newline — and nothing else.** Review of this fix caught the
first attempt, `[ \t]*\r?`, losing **four** shapes 8.8.2 parsed: form feed, vertical tab,
NBSP and em space. Material rather than cosmetic, because
`manifest` reports resolved state: frontmatter it fails to parse makes a
`disable-model-invocation: true` skill read as **LOADED** and drops the description that
carries the per-turn cost. That is D1a's rule violated a second time, in a different file
— narrowing a class without enumerating the dimension.

`[^\S\n]*` — whitespace except newline — is the class that keeps every shape and still
cannot restart the lazy scan: **0 divergences** from 8.8.2 across all 14 enumerated
separators (the first attempt had 4), 1.5 ms at 64 KB, linear.

**The first count published for this was six, and it was wrong.** That enumeration ran
against in-memory strings; `parse_frontmatter` reads through `path.open("r")`, i.e.
universal newlines, which collapses every CR-based shape before the regex sees it. The
mutation test disagreed with the hand-run enumeration — four red, not six — and the read
path was the difference. A probe against a substrate the code does not use is not a probe,
and the error went in the direction that flattered the finding. Consequence recorded in
code and pinned by `TestUniversalNewlineContract`: the `\r` inside `[^\S\n]` is harmless
but not load-bearing here, and `newline=""` would change which separators are equivalent. Every code point the class
admits was probed individually for a revived blowup (`\r`, `\f`, `\v`, U+2028, U+2029,
U+0085, NBSP, U+001C, mixed): 1.97–2.07× per doubling, none above the 3.0 threshold.
Gated by `TestFrontmatterWhitespaceClassIsNotNarrowed`, which asserts both the parse and
the disabled-skill consequence for all 14; re-introducing the over-narrowing turns 8
assertions red.

Independently, `manifest.py:54` reads with a raw `read_text()` — no
`MAX_SKILL_SIZE`, unlike every other reader in the engine. Both call sites do
`fm, _ = parse_frontmatter(...)`: **the returned body is never used.** So the fix is
not a size cap on a full read — it is to read a bounded head and drop the body from
the signature. That removes the unbounded read, the quadratic trigger, and a dead
return value at once.

Head size calibrated, not guessed: across 248 real skills, commands and plugin payloads
the frontmatter block runs a median of 694 characters, p95 4,476, max 15,711 (vercel's
`ai-sdk`). 65,536 carries 100% of them with 4× headroom, and a test pins it above that
maximum — truncating a real artifact's frontmatter would make its description silently
read as empty.

**Characters, not bytes.** `read(n)` on a text handle counts code points, so on CJK
frontmatter this reads up to 4× as many bytes — still bounded. The constant was first
named `_FM_READ_BYTES`, which promised a guarantee the call does not make; renamed
`_FM_READ_CHARS`, and the calibration figures above are character counts because that is
what `m.end()` measured.

**Measured:** through the shipping CLI on one hostile 64 KB skill, 30.77 s → 0.22 s.
`manifest --json` over the real install is byte-identical to `main` (same sha256, 109
artifacts, 8,240 resident tokens, 19 findings).

**Three of this fix's own tests were non-discriminating**, every one found by mutation
rather than by rereading it, and one of them twice:

1. `test_oversized_file_is_not_read_whole` asserted only that the constant was small and
   that parsing still worked, so it passed with the bounded read reverted to a full
   `read_text()` — a full read yields the same mapping. It now instruments `Path.open` and
   asserts the actual `read(n)` argument.
2. Nothing pinned the head against the corpus maximum, so shrinking it to 8 KB passed.
   That assertion now exists, mirroring D1's bound checks.
3. `test_carriage_returns_never_reach_the_regex`, written specifically to catch a switch to
   `newline=""`, opened the file *itself* and asserted no CR in its own buffer — a property
   of the test's read, not the production one. It stayed green on that exact mutation. The
   repair inspected `kwargs` only, so it stayed green a **second** time for the same
   mutation spelled positionally. Arguments are now normalised through
   `inspect.signature(...).bind(...)`; both spellings turn it red.

A test that cannot fail on the defect it names is not a test — and an assertion a spelling
can walk around is not an assertion. Across this whole spec, every instance of this class
was found by a mutation test and none by rereading the test.

### D4 — F3 is a reachability correction, not a gate change

`shared.py:215-219`: the `system_prompt` branch of `build_scores` is an early return
that iterates every scorer and never consults `include_security`. Proven at the
shipping CLI — `score sp.txt --json` on a `.txt` with a role line emits
`security: 100`; the same content as `SKILL.md` emits none.

So the standing claim "the security dimension is reachable from no shipping entry
point" holds for the skill.md family and is **false for `system_prompt`**.

We do **not** start honouring `include_security` there: for `system_prompt`,
`security` is a documented CORE headline dimension (weight 0.15, `docs/ARCHITECTURE.md`),
so computing it is correct and suppressing it would move composites. What was wrong
is that the behaviour was accidental and undocumented. Therefore:

- pin it with a test, so it is a contract rather than an artefact;
- treat `security.py` and `output_contract.py` as **live** code on that path — their
  two quadratics get bounded under D1, not deferred as dead weight.

### D5 — `_RE_LENGTH_EXTENDED` needs both branches bounded

First measurement only exercised the leading `max(imum)?…` branch and showed no
blowup. The culprit is the second branch, `\d+\s*(words?|…)`. Bounding both:
11,657 ms → 18.3 ms at 16 KB (636×), linear, 0 verdict differences over the corpus,
and all four real phrasings still matched. Recorded because the incomplete first
measurement is exactly the trap this project keeps hitting: a probe against a
fragment is not a probe.

The digit bound is 12, below the measured 27-char run. That run is a digit sequence
somewhere in prose, not a length constraint; the corpus verdict check (0
differences) is the authority here, not the raw maximum.

### D6 — Two gates, static and empirical

**As built** (this section replaces an earlier draft that specified a repo-wide static
rule with an allowlist; that design was prototyped and rejected on measurement — see
"rejected" below. The spec is the source of truth, so it records what shipped):

- `test_patterns_are_bounded.py` — deterministic, zero false positives. For each of the
  five bounded patterns it asserts (a) the **presence** of each bounded spelling, and
  (b) that each bound stays **above the corpus maximum it was calibrated from** (58, 118,
  1151, 50, 19). Every assertion mutation-tested: un-bounding a pattern, tightening a
  bound below its measured maximum, and truncating the backtick span each turn it red.
- `test_patterns_scale_linearly.py` — empirical, 224 compiled patterns across 30 modules
  × 25 filler alphabets at doubling lengths, ratio < 3.0. Two-stage: a flagged filler is
  re-measured with more repetitions **and at a second doubling**, and only fails if both
  doublings are super-linear. The healthy margin is 1.3–2.4× against a 3.0× threshold,
  which is too thin to rest on one sample — a single sample under load did flake once
  during development. Verified red-capable (4.20×, 4.02× confirmed) and green four times
  over under four busy cores.

  *Amendment 2026-08-21 (#210):* the ratio is calibrated — divided by the ratio of a
  known-linear literal scan on the same input — and the threshold is 1.5 on that scale.

  *Amendment 2026-09-05:* the calibrator itself flaked. It took one timing window per
  input size and returned as soon as the window cleared the floor, which a scheduler
  stall does by itself; measured on the macOS runner, a linear scan calibrated at 7.29
  and, back-computed from a 0.93x raw doubling reported as 4.96x, at 0.19, and because the value is cached per input pair one stall distorted every
  pattern (seven red attempts in eleven days, all `test-macos`, all traceable to the
  divisor). The calibrator now takes the fastest of three windows and accepts a window
  size only once the fastest window clears the floor. Pinned by a test that injects a
  30 ms clock stall into one window: 628 before, ~2.0 after. Not reproducible on a
  laptop under eightfold load (spread 1.66–2.02), so the field verification is repeated
  CI runs, not a local loop.

**Rejected, with the measurement:** a repo-wide static rule flagging "any unbounded
quantifier on a character class" marked 47 of the 102 patterns in `scoring/patterns/*`
(measured on `main`); the refinement "…with no
required literal prefix, since a literal limits the number of start positions" still
marked 11, including `_RE_BACKTICK_REF`, where a leading backtick does limit start
positions. Each further refinement needs its own justification, and a gate whose
allowlist is longer than its findings is the thing it exists to prevent. The repo-wide
sweep is therefore the empirical test's job.

**Coverage, and what it does not cover.** The first draft of the empirical gate covered
11 modules and 138 patterns while the audit harness that found the defects covered 25
and 224 — a gate narrower than the harness it replaces is not a regression guard. Widened
to 30 modules (0 additional findings, so the coverage was free), imports no longer behind
a `try/except` that could shrink coverage silently, and a count assertion that fails if
the collection ever shrinks.

The remaining blind spot is real: **the gate reaches exactly as far as its filler
alphabet.** `manifest._FM` (D3) is quadratic on a frontmatter-shaped input at 3.95× per
doubling and none of the 25 generic fillers trip it — they come in at 1.85×, below the
absolute floor. The frontmatter filler therefore lands **with** the D3 fix, where it is
red-before-green rather than red-on-main. The `_MIN_ABS_SECONDS` floor has the same
character: it suppresses noise, and would also suppress a quadratic with a very small
constant at this input size.

### D9 — `score.py`: a negative Content-Length is an invalid header, not a small one

`read_len = min(content_length, MAX_CONTENT_SIZE)` evaluates to `-1` when the header is
`-1`, and `rfile.read(-1)` reads to EOF — so the cap the line's own comment promises
("Read at most MAX_CONTENT_SIZE bytes regardless of the declared Content-Length") is
bypassed. Measured by driving `do_POST` with an instrumented `rfile`: **3,145,832 bytes
read against a 512,000-byte cap.** `web/leaderboard/api/submit.py` already had the `< 0`
half of its guard; this endpoint did not.

Rejected as `400 Invalid Content-Length header` rather than folded into the `413` branch:
the endpoint already has that exact 400 for an unparseable header, and a negative length
is the same category of defect.

Bounded in practice by Vercel's own body limit, and whether the edge forwards a negative
Content-Length at all is **unverified** — establishing that would mean probing production.
So this is defence in depth and an asymmetry between two sibling endpoints, not a
demonstrated live exploit.

Tests drive `do_POST` rather than grepping the source, and each asserts the **reason**, not
just the status: before the guard a negative length already returned 400, from the
truncated-JSON branch, so a status-only assertion would have passed on the unfixed code.
An over-broad `<= 0` guard is caught too — it keeps every status identical and only steals
the empty-body message, which a status-only assertion cannot see. Both were found by
mutation.

### D10 — F7 (badge cache-buster) DECLINED, with the measurement

`badge.py` reads only `repo` from the query string; other parameters are ignored by the
handler but are part of the CDN cache key, so `?repo=o/n&x=N` mints unlimited distinct keys
that each re-run the scorer. The proposed fix was to reject unknown parameters.

Declined, because the severity was derived from D1. Post-fix cost of the worst payload an
attacker can put in an AGENTS.md at the 32 KB cap:

| payload | before D1 | after D1 |
| --- | --- | --- |
| benign 32 KB | — | 87.9 ms |
| the 4.75 s shape | 4,750 ms | 122.7 ms |
| the 162 s shape | 162,600 ms | 96.0 ms |

120 ms per request is ordinary request cost, not amplification. And the marginal harm over
"attacker enumerates real public repos" is about zero: the CDN cache only ever protected a
*single* repo key, and there is no shortage of repos. Changing public behaviour — a URL with
a stray parameter would start returning a grey badge — is not worth that.

Recorded rather than silently dropped, so the decline is auditable. Revisit if D1 is ever
relaxed, since this finding's severity is a function of that one.

### D7 — `run-eval.sh`: make the missing guard visible, do not touch the matcher

`_GREP_TIMEOUT` is set only `if command -v timeout || gtimeout`. Both are absent on
a stock macOS, so the 2 s guard is inert and its `124)` branch is dead code there.

Measured refutation of the underlying worry: the sink does not backtrack. GNU grep,
BSD grep 2.6.0 and ugrep 7.5.0 are all DFA-based and stayed flat (0.044–0.050 s) on
patterns `validate_regex_complexity` accepts (`a*a*a*…b`, `a{1,10}{1,10}b`,
`(\w+\s?)*$`). The guard is defense-in-depth, not load-bearing.

So: one stderr note when no timeout binary exists, and a comment recording why the
matcher stays. A portable Python fallback is rejected — swapping ERE for Python `re`
is what left six assertions dead on CI for months.

### D8 — F6 declined, with the measurement

`playground/public/index.html:1476-1490` auto-scores a `#content=` deeplink 300 ms
after load. Its entire severity was derived from F1: after D1+D2 the scoring cost is
linear (58.9 ms for the former 162 s payload), and the endpoint is unauthenticated,
so there is no CSRF privilege and no XSS (textarea sink, sha256-pinned CSP). No code
change; recorded here so the decline is auditable.

## Rollout

PR 1 (this spec's D1, D2, D5, D6) → PR 2 (D3) → release v8.9.0 → `vercel --prod`
for the playground → PR 3 (F4 + F7, playground) → PR 4 (D7).

Release is justified under the project's own rule — a build that used to hang now
completes, so a gate's runtime behaviour changes — and the GitHub Action installs
`schliff` latest, which is the fork-PR path that carries the worst blast radius.

## Open questions

None blocking. `_RE_SEC_BASE64_CMD` and its siblings in `patterns/base.py` carry
`[^\n]*` spans that the v8.6.3 pass already bounded to `{0,200}`; the new static gate
will confirm that mechanically rather than by reading.
