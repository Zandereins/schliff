# `--format skill` and `--format skill.md` score the same file differently

**Status:** fixed · **Branch:** `fix/format-alias-normalization` · **Found:** 2026-08-04, on `main` at 8cb3158

Closes the two items [2026-07-31](2026-07-31-format-alias-drops-security.md) left open. They are
not two semantics questions — they are the last two branch sites of the defect #168 fixed at the
first one.

## Symptom

Two spellings of the same `--format` value disagree:

```
schliff score AGENTS.md --format skill     → composite 39.3
schliff score AGENTS.md --format skill.md  → composite 34.5
```

Across the 29 tracked instruction files in this repo, **exactly the 8 that have no YAML
frontmatter** diverge, by **4.7 to 5.5 composite points**:

| File | `--format skill` | `--format skill.md` | Δ |
| --- | --- | --- | --- |
| `AGENTS.md` | 39.3 | 34.5 | 4.8 |
| `benchmarks/corpus/v1/phase0-snapshot/09-algorithms.SKILL.md` | 23.7 | 18.2 | 5.5 |
| `benchmarks/corpus/v1/phase0-snapshot/10-GAP-Design-System.SKILL.md` | 22.1 | 17.4 | 4.7 |
| `demo/sample-cursorrules/.cursorrules` | 29.7 | 25.0 | 4.7 |
| `demo/sync-conflict/.cursorrules` | 29.7 | 25.0 | 4.7 |
| `demo/sync-conflict/CLAUDE.md` | 29.7 | 25.0 | 4.7 |
| `skills/schliff/tests/fixtures/dangling-repo/AGENTS.md` | 29.6 | 24.8 | 4.8 |
| `skills/schliff/tests/proof/bad-skill.md` | 20.7 | 16.0 | 4.7 |

Two of those are real files in the project's own benchmark corpus, so this is not a synthetic
edge case. `skill`/`skill.md` is the **only** alias pair that diverges — `claude`/`claude.md`,
`cursor`/`cursorrules`, `agents`/`agents.md` and `system-prompt`/`system_prompt` are byte-identical
across all 29 files (measured, not reasoned: #168 closed the last of those).

A second, non-scoring symptom: a genuine SKILL.md **with** frontmatter, scored with `--format skill`,
prints

```
  Format: skill (normalized)
```

Both halves are false. `skill` is not the format's name, and nothing was normalized — for content
that already has frontmatter `normalize_content` returns it unchanged.

## Cause

Three raw string compares branch on a value that may be a public `--format` alias:

| Site | Compare | Consequence |
| --- | --- | --- |
| `shared.py:230` | `fmt != "skill.md"` | the alias enters the normalization branch its canonical twin skips |
| `formats.py:77` | `fmt == FORMAT_SKILL_MD` | the inner early return misses the alias too, so wrapping proceeds |
| `cli.py:288` | `detected_fmt != "skill.md"` | display name and the "(normalized)" claim |

For a file without frontmatter the normalization branch invents synthetic frontmatter
(`_extract_name` / `_extract_description` from the body) and scores the wrapped copy. The structure
dimension then sees a name and a description that the file does not have — worth the 4.7–5.5 points.
For a file that already has frontmatter the branch is a no-op on content, which is why only 8 of 29
files move.

`resolve_format()` was introduced by #168 and every *lookup* in `registry.py` uses it. These three
are *branches*, and the docstring of `resolve_format` already warns that branches must resolve
first. #168 fixed one of four; these are the remaining three.

## Decision: converge on NOT normalizing

The two spellings must agree — that is not a judgment call for a deterministic scorer. Which side
they agree on is, and it is the un-normalized one (the lower number):

- Normalization exists so formats that *legitimately* carry no frontmatter (CLAUDE.md, AGENTS.md,
  `.cursorrules`) are scorable at all. A SKILL.md is **defined** by its frontmatter.
- Inventing a name and description for a SKILL.md that lacks them hides exactly the structural
  defect the structure dimension exists to report. 39.3 is the flattered number; 34.5 is the
  measurement.
- Auto-detection is not the tie-breaker some might expect: a frontmatter-less `.txt` detects as
  `unknown`, not `skill.md`, so AUTO normalizes because of the *detected* format. Nothing about the
  detected path argues for laundering a stated `skill.md`.

So `--format skill` drops to its canonical twin's score. **This lowers scores** for the stated-format
path on files without frontmatter, which is why it ships as a minor, not a patch.

## Fix

Canonicalize once at the top of `build_scores`, then branch only on the canonical name — `fmt`
carries a canonical value from that line down, so both compares underneath are correct without
being touched individually. `normalize_content` receives the canonical name and its own early
return starts working. `detect_format` already returns canonical names, so the detected path — and
with it the playground, which only ever calls `detect_format` — is a strict no-op.

`cli.py` resolves `detected_fmt` for display and for the JSON `format` field, which fixes the name
and retires the false "(normalized)" line in one move: once `--format skill` resolves to `skill.md`,
the `!= "skill.md"` guard is correctly False and prints nothing.

The JSON `format` field now reports canonical names for every alias (`--format claude` reports
`claude.md`). No consumer breaks: the leaderboard validates against its own display vocabulary
(`VALID_FORMATS = {"SKILL.md", ".cursorrules", "CLAUDE.md", "AGENTS.md"}`), which never accepted
engine names in the first place, and the playground emits `detect_format()` output.

## Acceptance gate — two-sided

Same shape as #168's, widened from 60 cells to 348: **29 tracked instruction files × 12 format
values** (`None`, the 10 registry/alias choices, and `unknown` — mirroring `cli.py:1067`, which
appends it). Both the composite and every per-dimension score are compared.

| | Result |
| --- | --- |
| 348 cells, `main` at 8cb3158 vs fixed | **340/348 byte-identical** |
| The 8 that changed | all `--format skill` on a frontmatter-less file, each now **equal to its canonical `skill.md` twin** |
| Cells that raise | 0 before, 0 after |
| Unit tests | red before / green after |
| ruff 0.15.8 (CI pin) over `scripts/` | clean |

The 8 changed cells are exactly the set the symptom table accuses — no third cell moved. That is the
property #149 lacked and the reason this gate is two-sided rather than "the new case works".

## Reachability note

A stated format reaches the engine from exactly one place: `cmd_score`
(`getattr(args, "format")`, `cli.py:175`). `verify`, `badge`, `doctor`, `diff`, `compare`, `report`
and `suggest` all call `detect_format` and cannot receive an alias — so **no CI gate can change
verdict from this fix**, only an explicit `schliff score --format skill` on a file without
frontmatter. `evolve --format` is free-form but routes through `text_gradient`, which resolves.

## Left open

Nothing from #168's list remains. `_resolve_version()` — the third item raised on 2026-08-04 —
shipped separately in #172, since it shares no code with this.

One inaccuracy in #168's write-up, recorded rather than fixed: it states the four inline
`FORMAT_ALIASES.get(fmt, fmt)` copies were all replaced by `resolve_format()`. One survives, at
`text_gradient.py:594`. It resolves correctly, so it is not a defect and is deliberately left
untouched here — but it is the same duplication #168 named as the reason a caller could forget,
so it is worth collapsing the next time that file is opened for a real change.
