# `--format system-prompt` silently drops the security dimension

**Status:** fixed · **Branch:** `fix/format-alias-drops-security` · **Found:** 2026-07-31, on shipped v8.9.0

## Symptom

The same file scores differently depending on whether its format is *detected* or *stated*:

```
schliff score fp.txt --json                         → composite 49.4 · 7 dims · security 100
schliff score fp.txt --format system-prompt --json  → composite 36.8 · 6 dims · security absent
```

Measured spread across five files: **5.9 to 15.0 composite points**. The user who pins the
format explicitly — the more careful thing to do in CI — gets the wrong number.

## Cause

`--format` accepts aliases (`registry.FORMAT_ALIASES`), including `system-prompt` → `system_prompt`.
Every *lookup* in `registry.py` resolved them; the *branch* in `shared.build_scores` did not:

```python
if fmt == "system_prompt":      # raw compare — False for "system-prompt"
```

For the alias the compare fails, the dedicated early return is skipped, and the file falls through
to the instruction-file branch — where `if dim == "security" and not include_security: continue`
removes the dimension. For `system_prompt`, `security` is a **core headline dimension**
(weight 0.15, `registry.HEADLINE_EXCLUDED` excludes only `runtime`), so the composite moves.

`system-prompt` is the only affected alias, because `system_prompt` is the only format with a
dedicated branch. `skill`/`claude`/`cursor`/`agents` all reach the generic branch, where
`get_scorers()` resolves them correctly — verified, not assumed (60-cell matrix below).

## Fix

`registry.resolve_format()` becomes the single canonicalizer (the four inline
`FORMAT_ALIASES.get(fmt, fmt)` copies now call it — that duplication is what let one caller forget).
`shared.build_scores` dispatches on the resolved name:

```python
if resolve_format(fmt) == "system_prompt":
```

**Deliberately NOT canonicalizing `fmt` itself.** The second compare four lines down
(`if fmt != "skill.md"`) drives normalization, and resolving `fmt` globally would flip it too:
`--format skill` would stop being laundered through a `.md` temp file and its score would move
(**measured: 30.8 → 26.1** on a `.txt`). That is a real inconsistency, but it is a different
defect with different semantics, and it was not what the measurement accused. It is recorded
below rather than smuggled into this fix.

## Acceptance gate — two-sided

Not "the new case works" alone; also "no already-correct score moved" (the one-sided gate is what
let #149 through).

| | Result |
| --- | --- |
| 5 files × 12 format values (incl. `None` and every alias), shipped 8.9.0 vs fixed | **55/60 byte-identical** |
| The 5 that changed | all `--format system-prompt`, each now **equal to its canonical `system_prompt` twin** (71.9 = 71.9, 67.8 = 67.8) |
| Unit tests | 3 new, red before / green after; **1930 passed** |
| ruff 0.15.8 (CI pin) over `scripts/` | clean |

The first run of this gate **caught the over-broad first draft** of the fix (the `--format skill`
regression above) before it reached a commit. That is the gate doing its job, and the reason it is
two-sided.

## Left open — separate decisions, not fixed here

1. **`--format skill` normalizes a file that needs no normalization**, routing it through a `.md`
   temp file and shifting its score by ~4.7 points versus the un-normalized path. Which of the two
   is *correct* is a semantics question, not a bug fix.
2. **The reported format echoes the alias**, not its canonical name: `"format": "skill"` in JSON,
   and `cli.py:288` prints `Format: skill (normalized)` for a plain SKILL.md — a false statement,
   since nothing was normalized. Cosmetic; no score impact (measured).

## Reachability note

This lands on the path F3 identified in the 2026-07-30 audit: `security` is dead for the skill.md
family and **live and load-bearing for `system_prompt`**. The deletion-list entry for `security.py`
must stay split — fix candidate here, deletion candidate there.
