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
