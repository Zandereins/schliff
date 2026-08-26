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

**Why not `EXCLUDED_DIRS`.** Adding `cache` takes the count from **159 to 50**: the cache *is*
where plugins install, so the exclusion would delete the majority of real skills instead of the
duplicates. The set has already needed three extensions (`site-packages`, `.cache`, `.vercel`);
a path wordlist is complete only until the next package manager. This is the enumeration trap
recorded in the 2026-08-25 amendment to
`docs/specs/2026-08-13-structural-signal-detection.md`, in a different file.

**The rule instead.** `shared.skill_payload_digest` — sha256 over SKILL.md, `references/*.md`
and `eval-suite.json`, length-prefixed. It carries no vendor names and does not grow.

**The key covers what a row's SCORE and COST are derived from, and that was got wrong three
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

All three are pinned by mutation-verified tests in
`skills/schliff/tests/unit/test_doctor_collapses_duplicate_copies.py`.

**Known limit, deliberately not closed.** The `Issues` column can still differ between two
copies with the same digest: `structure`'s dangling-reference lint resolves declared paths such
as `scripts/run.py` against the skill directory and its plugin/git ancestors, which lie outside
the digest's domain. Measured over the 20 real groups: 0 divergences, and that lint does not
score. Widening the digest to every path a skill might declare is the enumeration trap again;
reporting the union of issues across a group is the fix if a field case ever appears.

**What is deliberately not decided.** Which copy of a genuine duplicate is *counted* is
arbitrary: after the digest they are identical in everything measured. The path is not
interchangeable to a reader — `/schliff:auto` writes `.schliff/` history beside the file, and a
plugin cache directory is overwritten on the next update — so the report prints every path in a
group and says the choice is arbitrary. Nothing is deleted (ADR 0019).

**Still open, unchanged by this:** `doctor --json` reports `mesh_issue_count: 0` under
`incremental=True` while a fresh analysis finds 49. Present on `main` before this change.
