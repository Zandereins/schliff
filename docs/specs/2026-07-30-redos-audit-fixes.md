# Bounded quantifiers: closing the ReDoS class found by the 2026-07-30 audit

Status: implementing
Date: 2026-07-30
Baseline: `main` @ `ab41827`

## Goal

Close every reachable super-linear regex path found by the whole-repo security audit,
without moving a single score, and add a gate so a fifth one cannot land.

## Context

A trust-boundary audit of `ab41827` produced seven findings. Four of them are the
same defect, and it is not the textbook one: **an unbounded quantifier followed by
a required literal**. No nesting, no overlapping alternation — which is why static
shape-triage flagged 105 of 169 compiled patterns and isolated neither of the two
that mattered. An empirical fuzz (warm each pattern, time `.search()` against ~25
pathological filler alphabets at doubling lengths, keep ratio ≥ 3.0) narrowed 169
patterns to 32 candidates and then to the reachable ones in a single run.

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

1. Every reachable super-linear path measured in the audit becomes linear
   (ratio ≤ 2.5 per doubling).
2. **Zero score movement** on real data — proven, not asserted.
3. **Recall preserved** — every malicious shape that was detected before is still
   detected. Two-sided acceptance, because a one-sided "corpus byte-identical" gate
   is what let the #149 regression through.
4. A regression gate that fails CI on a new unbounded quantifier.
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
| `\w+` after a dot | 50 | 64 | 1.3× |
| `[a-z]*` (`rm` flags) | 2 | 12 | 6× |
| `\d+` (digit run) | 27 | 12 → see D5 | — |

A first guess of 120 would have sat one character above a real 118-char token and
would have **truncated** a real 1151-char backtick span. That is the whole argument
for calibrating: the failure mode of a guessed bound is a silent score change.

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
every `\s*` length restarts the lazy `(.*?)` scan. `^---[ \t]*\r?\n…` is 32,823×
faster at 64 KB with a byte-identical verdict **and** `group(1)` on every real shape
including CRLF and unterminated frontmatter.

Independently, `manifest.py:54` reads with a raw `read_text()` — no
`MAX_SKILL_SIZE`, unlike every other reader in the engine. Both call sites do
`fm, _ = parse_frontmatter(...)`: **the returned body is never used.** So the fix is
not a size cap on a full read — it is to read a bounded head and drop the body from
the signature. That removes the unbounded read, the quadratic trigger, and a dead
return value at once.

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

- `test_patterns_are_bounded.py` — deterministic, gates: no compiled pattern in
  `scoring/patterns/*` carries an unbounded quantifier before a required literal.
  Allowlist entries each carry a reason; no blank skips.
- `test_patterns_scale_linearly.py` — empirical: every compiled pattern against the
  filler alphabets at doubling lengths, ratio < 3.0. Generous threshold so a loaded
  CI runner does not flake, while still catching the 4.0× class.

The static test alone is insufficient — the first heuristic written for this audit
flagged 105 of 169 patterns and isolated neither real one. The empirical test alone
is timing-based. Both, or the gate is theatre.

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
