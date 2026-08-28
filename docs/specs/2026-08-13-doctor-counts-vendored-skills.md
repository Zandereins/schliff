# doctor counts vendored copies as installed skills

**Status:** fixed · **Branch:** `fix/structural-signal-detection` · **Found:** 2026-08-13, on `main` at `fc487fb`

Two walks discover files in a repo tree. One filters vendored directories, the other does not.

```
doctor.py:45      dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]   # AGENTS.md walk
skill_mesh.py:52  for skill_md in skill_dir_path.rglob("SKILL.md"):       # skill walk
```

`EXCLUDED_DIRS` has existed in `shared.py` since before this and is documented as
"shared by sync.py, doctor.py, and any future tree walkers". `discover_skills` is a future
tree walker that never got it.

## Symptom

`schliff doctor .` in this repo, which contains **one** skill:

```
  6 skills scanned | 5 healthy | 1 missing eval suite

  deploy-helper   23  [F]   313 tokens   demo/bad-skill/SKILL.md
  schliff         93  [A]  7748 tokens   skills/schliff/SKILL.md
  schliff         99  [S]  9013 tokens   playground/.venv/lib/python3.12/site-packages/…
  schliff         99  [S]  9013 tokens   playground/.vercel/python/.venv/lib/python3.12/site-packages/…
  schliff         99  [S]  9013 tokens   playground/.vercel/python/cache/uv/archive-v0/LUYK…/…
  schliff         99  [S]  2140 tokens   skills/schliff/tests/fixtures/self-skill-baseline/…

  Total context cost: ~37,240 tokens
```

Three of the six are the same file, vendored into two virtualenvs and a uv cache archive.
They inflate the skill count, the grade distribution ("5 healthy") and the headline
"Total context cost" — 37,240 tokens where the real cost is 7,748.

`doctor` is the entry path: `schliff --help` advertises it under Quick start, and the
scan runs over whatever repo the user is standing in. A repo with `node_modules` produces
the same failure at a larger scale.

## Two things that were assumed and are not true

**`MAX_SCAN_FILES` is not the problem.** `file_count` increments per discovered SKILL.md,
not per file walked, so the 1000-file budget is not consumed by vendored trees. (`rglob`
still walks the whole tree, which is a performance question, not a correctness one, and is
not addressed here.)

**`EXCLUDED_DIRS` alone is not sufficient.** Applied as it stood, it removes two of the
three vendored copies. The third sits at `playground/.vercel/python/cache/uv/archive-v0/…`,
where neither `.venv` nor `site-packages` appears in the path at all.

## Fix

Apply `EXCLUDED_DIRS` in `discover_skills`, keyed on path **segments**, and extend the set by
three entries the measurement demands:

| added | why |
| --- | --- |
| `site-packages` | an installed copy of a skill is not an installed skill |
| `.cache` | uv and friends archive extracted packages under a cache root |
| `.vercel` | build-artifact root; holds the uv archive in this repo |

Segment matching, not substring: a skill legitimately named `cache-warmer` must survive.
Pinned by `test_a_real_skill_named_like_a_cache_dir_still_counts`.

## Verification

Red before the fix, green after — `test_skill_discovery_excludes_vendored.py`, a tmp tree
with one real skill and four vendored copies covering all four shapes (`.venv`,
`node_modules`, the uv archive, and a bare `site-packages` outside any `.venv`).

```
$ schliff doctor .
  3 skills scanned            (was 6)
  Total context cost: ~10,201 tokens   (was ~37,240)
```

The three that remain are the repo's own real files: the skill, the deliberately-bad demo
skill, and the self-baseline test fixture. Excluding those two as well was considered and
rejected — they are the user's own files, and assuming a skill under `tests/` is not a real
skill is an assumption about someone else's layout.

**No real skill is lost.** Over the 299 installed skills under `~/.claude`: `rglob` finds
299, `discover_skills` returns 299, 0 excluded. Every exclusion in this repo carries a
vendored path segment; the count of files excluded *without* one is 0.

Full suite: **2121 passed**. `EXCLUDED_DIRS` is shared, so the three added entries also
apply to `sync.py` and the AGENTS.md walk — same semantics, no test moved.

## Amendment 2026-08-26 — path exclusion does not reach the duplicate-install case

The section above solved *vendored copies* — a skill sitting inside `site-packages` or a uv
cache archive — by extending `EXCLUDED_DIRS`. That fix stands. It does not reach the case
below, and extending the set further would break the measurement rather than repair it.

**The case.** A Claude Code plugin is installed under `~/.claude/plugins/cache/…` and also
appears under `~/.claude/plugins/marketplaces/…`. Both copies are real, both are the same
bytes, and both were counted.

**Measured on a real `~/.claude` at `c651d13`** — this is the single home for these numbers;
the code comments point here rather than restating them:

| | before | after |
| --- | --- | --- |
| skills counted | 159 | 138 |
| headline context cost | 495,928 tokens | 438,597 tokens |
| duplicate groups reported | — | 20 (21 extra copies) |

Measured 2026-08-26 on that installation. **It drifts**: a re-run the next day found 157 files and
19 groups, with `skills counted` and the token total unchanged, because the two files that had
gone were both duplicate copies. Plugins get installed and removed; the numbers above are a dated
observation, not a fixture. What does not drift is the shape — every removed copy takes a group
member with it and leaves the counted total alone, which is the property being claimed.

**Why not `EXCLUDED_DIRS`.** Adding `cache` takes the count from **159 to 50**: the cache *is*
where plugins install, so the exclusion would delete the majority of real skills instead of the
duplicates. The set has already needed three extensions (`site-packages`, `.cache`, `.vercel`);
a path wordlist is complete only until the next package manager. This is the enumeration trap
recorded in the 2026-08-25 amendment to
`docs/specs/2026-08-13-structural-signal-detection.md`, in a different file.

**The rule instead.** `shared.skill_payload_digest` — sha256 over SKILL.md, `references/*.md`
and `eval-suite.json`, length-prefixed. It carries no vendor names and does not grow.

**The key covers what a row's SCORE and COST are derived from, and that was got wrong four
times — each time by re-deriving a domain instead of asking the code that owns it:**

* *Cost.* Hashing SKILL.md alone collapses installs that cost different amounts — two
  byte-identical SKILL.md with different `references/` came to 9,013 and 9,591 tokens. The
  published total then depended on iteration order (keep-first 429,006, keep-last 429,584), and
  keep-first kept a June **backup** while discarding the live
  `~/.claude/skills/schliff/SKILL.md`: the cure deleting the subject of the measurement.
* *Score.* `eval-suite.json` moves a row from 4-of-7 dimensions to 7-of-7. Two byte-identical
  SKILL.md, one with the suite beside it, scored **38.3 [E]** and **93.0 [A]**. Ignoring it let
  path sort order decide which the reader saw — a 55-point swing settled by a string comparison.

* *The loader's own discovery.* The first eval-suite branch copied
  `estimate_token_cost`'s symlink skip. `load_eval_suite` has no such guard — it follows the
  link — so a stow/chezmoi layout was scored 7-of-7 and hashed as if it had no suite, and the
  two copies collapsed again. The digest now calls `load_eval_suite` instead of re-deriving
  where the file is, which makes the domains identical by construction rather than by review.

* *The loader's error contract.* Calling `load_eval_suite` fixed the discovery mismatch and
  created a new one: it caught only `JSONDecodeError`, so a suite that is a directory,
  unreadable, or not UTF-8 raised. That was survivable while its only caller sat inside
  `_score_single_skill`'s `except Exception` — one row went to `failed` — and stopped being
  survivable the moment the digest called it before the scoring loop. One malformed
  `eval-suite.json` anywhere under `~/.claude` turned `doctor` into a traceback. Fixed at the
  loader: every failure degrades to `None`, so digest and score see the same value by
  construction rather than one crashing where the other degraded.

All four are pinned by mutation-verified tests in
`skills/schliff/tests/unit/test_doctor_collapses_duplicate_copies.py`.

**The shape behind all four.** Each was a domain re-derived instead of asked for. The
`references/*.md` enumeration is now `shared._payload_files`, called by both
`estimate_token_cost` and `skill_payload_digest`, so the cost domain and the identity domain
cannot drift apart. The drift was already primed: `estimate_token_cost`'s docstring says "all
files in references/" while its code globbed `*.md`; making the code match would have widened
the cost and not the digest.

**Known limit, deliberately not closed.** The `Issues` column can still differ between two
copies with the same digest: `structure`'s dangling-reference lint resolves declared paths such
as `scripts/run.py` against the skill directory and its plugin/git ancestors, which lie outside
the digest's domain. Measured over the 20 real groups: 0 divergences, and that lint does not
score. Widening the digest to every path a skill might declare is the enumeration trap again;
reporting the union of issues across a group is the fix if a field case ever appears.

**Which copy is counted, and why the row carries no command.** Not arbitrary: `discover_skills`
sorts by path and the first wins, so `plugins/cache/…` beats `plugins/marketplaces/…` and
`~/.claude/skills/…`. That holds for those three absolute paths, i.e. for a scan pointed at
`~/.claude` — **it is not true of the default invocation**; see "Amendment 2026-08-28". Where it
does hold it is a systematic bias toward the one copy a reader should *not* act on — `/schliff:auto` writes `.schliff/` history beside the file, and a plugin cache is
overwritten on the next update. Preferring another member would require a path wordlist, the
enumeration this key exists to avoid, so instead a grouped row states the duplicate rather than
emitting a command against one member. Every path in the group is printed; nothing is deleted
(ADR 0019).

**Symlinked `references/` stay rejected.** `estimate_token_cost` has rejected them since a
shipped security fix, and `_payload_files` inherits that. It was briefly reversed here so a stow
layout would collapse with its plain twin — on the strength of a self-written fixture. Measured
afterwards: **0 symlinks across the 41 skills in the real installation that have a `references/`
directory**. doctor walks other people's directories, so following a link there turns a word
count into a filesystem oracle and reading before the size check turns a link to a huge file into
an OOM; `skill_mesh` confines resolved paths to the scan root for the same reason. The cost was
real and the case was not. If a field case appears, the fix is confinement plus a
`stat().st_size` check before the read, not a bare `resolve()`.

**One reader for every file on the discovery and scoring path.** `discover_skills` reads
SKILL.md and is therefore the *first* file doctor opens — the guard has to start there, not
downstream of it. A FIFO named SKILL.md blocked discovery past eight seconds before the reader
below was ever reached. `read_skill_safe` is deliberately excluded: it reads before checking size
to close the TOCTOU race, and its callers sit inside a handler.

**The reader itself.** `shared._read_bounded` checks *regular file*,
then *size*, then reads — and the ordering of those three is the whole point. `read_text` on a
FIFO blocks forever (measured: still blocked after six seconds) and `st_size` is 0 for one, so a
size gate alone lets it through; reading before the size check raises `MemoryError` on a
multi-gigabyte target, which is neither `OSError` nor `ValueError`. Both were survivable while
every caller sat inside `_score_single_skill`'s handler and stopped being survivable when the
digest began reading before the scoring loop. The same two-line omission produced five defects
here, which is why the check exists once rather than at each call site.

**A suite that is not a JSON object is a broken suite.** `null` parses to `None`, which was
indistinguishable from "no file" and routed the row to `/schliff:init` — the command that
overwrites it. A list or string was accepted outright, while `cli._load_eval_suite_from_args`
rejects the identical content; the auto-discovery half was the permissive one.

**The loader checks size before reading.** `read_text` on a multi-gigabyte target raises
`MemoryError`, which none of the handlers above catch, and the digest calls the loader before the
scoring loop — so one such file ended the run rather than marking one row failed.
`cli._load_eval_suite_from_args` had done `stat().st_size` first since the OOM-safe-loading fix;
the shared loader never received it. It does now.

**A grouped row is not "missing an eval suite".** Its own action says to resolve the duplicate,
and its path is the plugin cache. Counting it as missing put all 20 real groups into "Run
/schliff:init on N skills missing eval suites" — writing into a directory the next plugin update
deletes, and contradicting the row itself. Counted separately as `grouped_duplicates`.

**A broken eval suite is not an absent one.** `load_eval_suite` degrades every failure to `None`
so one bad file cannot end a run — including `RecursionError`, which `json.loads` raises on deeply
nested input below CPython 3.14 and which is neither `OSError` nor `ValueError`. That version
dependence is the dangerous part: the newest CI leg stays green while the oldest tracebacks.
Degrading is not enough on its own, though — "absent" and "present but broken" produce different
rows, so the failure is recorded in `shared.eval_suite_error`, reported per row as
`eval_suite_error`, folded into the digest so the two do not collapse, and the row's action says
to fix the file rather than `/schliff:init`, which would write over it.

**Still open, unchanged by this:** `doctor --json` reports `mesh_issue_count: 0` under
`incremental=True` while a fresh analysis finds 49. Present on `main` before this change.

## Amendment 2026-08-28 — the reporting layer, from review round 10

Nine rounds went to the collapse logic; the tenth found six defects, all of them in what the
report *says* rather than in what it counts. Recorded because five of the six are the same shape:
a sentence that was true of the measured case and stated unconditionally.

**"Usually the plugin cache" is false under the default invocation.** `_default_skill_dirs()` is
`[~/.claude/skills, .claude/skills]`; `~/.claude/plugins` is never scanned by a default run, so
no plugin cache is in the comparison at all. And `.` (0x2E) sorts before `/` (0x2F), so the
relative project path wins:

```
counted: .claude/skills/dup/SKILL.md
also at: /…/home/.claude/skills/dup/SKILL.md
```

The banner then told the reader that this counted path is "usually the plugin cache — act on the
copy you control", i.e. to treat their own working copy as the disposable one. The claim had
**eight homes** (banner, four code comments, two lines of `commands/schliff/doctor.md`, one spec
sentence above) — the #209 pattern again. All are now either qualified with the invocation they
hold for, or state only what is invariant: the counted path is an artifact of sort order.

**A repair reason was truncated by the column widened to keep it.** `"Resolve the duplicate
install first; eval-suite.json: "` is 54 characters, so a 70-wide cap cut `not a JSON object` to
`not a JSON objec`. The width is now `REPAIR_ACTION_WIDTH`, and
`test_repair_action_fits_its_column` derives the longest composed action from the reasons
`load_eval_suite` can actually produce — enumerated out of the module's AST, not hand-listed — so
a new reason fails the test instead of silently truncating. A gate, not a convention.

**"Unreadable" hid the one diagnosis the reader needed.** `_read_bounded` collapsed "not a regular
file", "too large" and `OSError` into a single `None`, so a 2 MB suite was reported as unreadable
and the advice was to repair a file whose only defect was its size. It now returns a short,
path-free reason (path-free because the reason is folded into the identity — the defect recorded
in "Amendment 2026-08-26").

**The size check ran on the path, not on the descriptor.** `is_file()` → `stat()` → `read_text()`
leaves a window in which the path is swapped for a FIFO after it has answered "regular file", and
a party that can plant the FIFO can win that race — so under this function's own stated threat
model the hang stayed reachable. Now `O_NONBLOCK` open, then `fstat` on that descriptor.

A plain FIFO is the **wrong test** for this and was written first: `is_file()` already returns
False for one, so a FIFO fixture stays green against the very mutation it quotes. The
discriminating fixture answers the path-level questions the old shape asked while the object on
disk is a FIFO; under the old shape it blocks, and the instrument is a clock, not an exception.
Verified: the mutation hangs the thread and the test fails after 5.16 s.

**Every `eval-suite.json` was read and parsed twice per run** — once by `skill_payload_digest`,
once by `_score_single_skill` — and every warning printed twice. Cached following the shape
`_file_cache` already uses in the module, with one addition: the key carries an
`(st_mtime_ns, st_size)` stamp. A path-only key made a repaired suite stale and
`test_a_repaired_suite_clears_its_recorded_failure` — an existing test — caught it.

**Grouped rows still drew skill-specific advice.** A duplicated 408-line skill got "Consider
extracting into references/" beside a row whose own action says to resolve the duplicate first,
against a path picked by sort order. Carved out the same way the `/schliff:init` and
`/schliff:auto` tallies already carve it out.

## Amendment 2026-08-28 (2) — round 11

**A constant is not an identity.** When a suite parsed but `json.dumps` raised, the digest absorbed
the literal `"<unserialisable>"`. Two skills sharing a SKILL.md but holding *different*
unserialisable suites therefore got one digest, and the second vanished from the report as a copy
of the first — the failure the `else` branch three lines below it names in the same function. The
marker now comes from `shared.eval_suite_content_id`, a sha256 the loader records over the bytes it
read; the digest reads it rather than re-opening the path, which is the re-derivation this module
has already paid for five times.

The test forces `json.dumps` to raise instead of building a deeply nested fixture: below Python
3.14 `json.loads` recurses first, so the branch is unreachable on the interpreter this suite
usually runs on and a nesting fixture would prove nothing there.

**Two findings from round 11 were deliberately NOT fixed here**, both because they are design
choices rather than mechanical corrections, and neither has a site in the field:

- *`MAX_SKILL_SIZE` is bytes in `_read_bounded` and characters in `read_skill_safe`.* A file
  between the two thresholds is dropped from `doctor` and `mesh` with empty stderr while
  `schliff score` still reads it. Measured over the real 159: largest SKILL.md is 80,431 B /
  80,328 c, a factor of 12 below the limit, 0 files above 200 KB, byte-to-char ratio 1.0013. Real,
  latent, and it moves a DoS boundary — which does not belong in a green PR inside a freeze window.
- *`_payload_files` checks `is_symlink()` on the path, `_read_bounded` then opens that path.* Not a
  regression: `main` had `is_symlink()` followed by `read_text()`, the same check-then-open shape.
  Closing it means `O_NOFOLLOW`, which would also take the symlink-following that `load_eval_suite`
  deliberately has for stow/chezmoi layouts — so it needs a per-caller flag and a decision.

## Amendment 2026-08-28 (3) — round 12, and the sweep that was not one

Four findings, and the instructive part is that **two of them were introduced by the round-11
fix itself**. The finding count stopped falling (7 → 3 → 4) not because the review was grinding
but because new defects were being added at roughly the rate old ones were removed.

**`os.O_NONBLOCK` is Unix-only.** The descriptor-based reader shipped in round 10 referenced it
directly. On Windows the attribute lookup raises `AttributeError` — neither `OSError` nor
`ValueError`, so the reader's own guard does not catch it — and the reader now sits on *every*
scan path, so the first file of any run would traceback. `getattr(os, "O_NONBLOCK", 0)`. The
project treats Windows as in scope elsewhere (`verify.py:155` has an explicit fallback with a
comment saying so) and `pyproject.toml` declares no OS classifier.

**The `<unserialisable>` fix was applied to one branch of two.** Three lines below it, the
`else` branch absorbed only the coarse reason string, so two suites both `malformed` for
different reasons shared a digest and were reported as copies of each other. `eval_suite_content_id`
was already populated on those paths — it is recorded before `json.loads` runs — so the fix was
available and simply not carried across. This is the defect class this document has now recorded
three times: *fix every site of a class, not the one the finding named.*

**The digest phase ran outside every handler.** `_collapse_duplicate_copies` is called before the
scoring loop, and `skill_payload_digest` reaches `read_skill_safe`, which reads before it checks
size and can raise `MemoryError`. `_payload_files` justifies leaving `read_skill_safe` outside the
bounded reader on the grounds that "its callers sit inside a handler" — false for this caller,
exactly where a failure ends the whole run. Wrapped; the fallback reports every copy, the
over-count direction this module has repeatedly recorded as the survivable one.

**A grouped-and-broken row fell through every bucket** and took the report's strongest line with
it. `grouped` is tested before `eval_suite_error`, so such a row incremented neither counter, and
the whole "Recommended next steps" block is gated on those counts — so `do NOT run /schliff:init
on these, it writes over them` was absent from the rendered report. Tracked as
`grouped_broken_eval_suite`, beside the disjoint buckets rather than inside them, so the partition
still holds exactly. Note this is *not* the open question below: the safety warning is separable
from the quality counts, and only the counts are still undecided.

**Not fixed, awaiting a decision:** a grouped row lands in no quality tally — `grouped_duplicates`
counts it, but `healthy`/`needs_work` do not, so on the real install 19 of 138 skills are absent
from the counts the summary line reports. The suppression is right for the command
recommendations; whether it is right for the counts is a separate judgement.
