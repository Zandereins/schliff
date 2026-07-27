# Runner-target classification (#133) — retire the `consumed_run` build fallback

- Status: **spec — awaiting decision, not implemented**
- Issue: [#133](https://github.com/Zandereins/schliff/issues/133)
- Branch: `spec/133-runner-target-classification`

## Goal

Stop `operational_coverage` from crediting a `build` command it never looked at.
When a runner delegates to a target the vocabulary does not know, the family must
follow from what the target *is*, not from whether the word `run` happened to
precede it.

Explicit non-goal: widening the `_GUARDED` prose defence. Measurement below shows
that would trade a 2-occurrence problem for a false-positive class.

## Context

`_runner_family()` (`scoring/operational_coverage.py:274`) ends with:

```python
return "build" if consumed_run else None
```

Everything downstream of the vocabulary miss hinges on that one flag:

| | `test` | `test-unit` | `lint-fix` | `wibble` |
|---|---|---|---|---|
| `make`, `just`, `cargo`, `yarn <script>` | test | — | — | — |
| `npm run`, `pnpm run`, `yarn run`, `uv run` | test | **build** | **build** | **build** |

(— = dropped.) `yarn test-unit` drops; `yarn run test-unit` scores build. Same
tool, same script.

`operational_coverage` carries weight **0.4** on the `agents.md` headline profile,
so a wrong family here is a wrong public score.

## What the measurement changed

Three hypotheses died against real data. Recorded because each one would have
produced a worse fix.

**1 — "make uses exact matching, npm uses prefix matching."** False. `make` is not
in `_RUNNER` at all and never reaches `_runner_family`; it is handled by the
`_GUARDED` branch (`:415-428`). `_script_family`'s prefix matching is on an
unrelated path. The real split is `consumed_run`.

**2 — "so make the guarded branch match prefixes too."** Refuted by incidence.
Across **259 real files** (30-file AGENTS.md corpus + 228 installed SKILL.md +
this repo's own), guarded verbs with an unknown target inside a bash fence occur
**30 times**, and the composition is hostile:

| what it is | count | examples |
|---|---|---|
| agent-tool syntax / prose | 14 | `Task reviewer:`, `Task {`, `Task 1:`, `task =`, **`Make sure`** |
| script-path invocations | 13 | `python3 scripts/onboard.py`, `node …/analyze-sessions.mjs` |
| the motivating case | **2** | `make test-unit`, `make test-all` |
| other | 1 | `go mod` |

`Make sure` appears **inside a fence**, which refutes the assumption that fence
context is a safe licence to relax. The motivating case occurs twice in 259 files
— both in this repo's own `AGENTS.md`. Loosening the guard to catch 2 real
commands would newly credit 14 non-commands. The guard's comment already states
the intent (`make tests pass` is English, not a command); the data backs it.

→ **Defect A (the drop) is closed as won't-fix.** `check-commands` staying silent
rather than guessing is the documented, and now measured, correct behaviour.

**3 — "so unknown run-targets should return `None`."** Too blunt. Simulated over
the corpus, opcov mean moves 37.17 → 36.50 and exactly **1 of 30 files** changes:
`markov-kernel__databricks-mcp` 65 → 45. Inspecting it shows the fallback is
masking two *opposite* errors in adjacent lines:

```
uv run pylint databricks_mcp tests    -> build    # pylint is a linter -> test
uv run databricks-mcp -- --help       -> build    # --help is inspection junk -> nothing
```

Returning `None` fixes the second and breaks the first. The blanket fallback is
not one bug; it is a missing classification step that happens to be wrong in both
directions.

## Proposal

Replace the flag-driven fallback with three ordered checks on the delegated
target. Only the last line changes behaviour; the earlier ones already exist and
simply were never reached.

1. **Honour the existing read-only guard.** `_is_readonly` already recognises
   `--help` / `--version` as inspection junk. Apply it to the delegated target so
   `uv run databricks-mcp -- --help` credits nothing. Today the fallback bypasses it.

2. **Extend the intrinsic tool sets with what the field actually uses.** `pylint`
   belongs in `_TEST_INTRINSIC` — `lint` is already a `_TEST_TOKEN`, the tool that
   performs it should be too. Candidates are to be derived from the same 259-file
   sweep, not invented, and each added token gets a corpus-named test.

3. **Then fall through to `None`, not `build`.** An unrecognised target is
   unmeasured, which is what "we could not determine this" has always meant
   everywhere else in this engine. `npm run wibble` credits nothing.

Boundary matching (`test-*`, `test_*`, `test:*`) is deliberately **not** proposed
for `_RUNNER` verbs in this round. It is defensible there — `npm run` cannot occur
in prose — but the corpus shows the wins come from steps 1 and 2, and adding a
second mechanism in the same change would confound the golden re-derivation.
Revisit once this lands and is measured.

## Impact and golden handling

This is a **golden-touching** change. `test_agents_md_profile.py` pins mean,
median, min and band counts over the 30-file corpus and must be re-derived from
the engine, never hand-tuned.

Simulated for step 3 alone: mean 37.17 → 36.50, median/min/max unchanged, 1 file
moves. Steps 1 and 2 move it back up where the target is a real test tool, so the
net is expected to be smaller — **to be measured, not predicted**, and written
into the test's comment the way #10's re-baseline was.

This repo's own `AGENTS.md` is unaffected: its 4 runner-delegated commands are all
exact-vocabulary hits (measured). The published badge should not move; that is a
gate, not an assumption.

## Verification plan

- TDD per step, red → green, one test per corpus-named case
- full suite green; `ruff==0.15.8` clean
- golden re-derived from the engine with the delta documented in the test comment
- own badge re-checked: `95.8` in-repo == isolated, or the change is justified in writing
- re-run the 259-file sweep and confirm no new false credit appears

## Open decisions

1. **Won't-fix on defect A** — accept that `make test-unit` stays invisible and
   document it, or keep it open? Recommendation: accept. The alternative buys 2
   commands for 14 false positives, and the README already states the limit.
2. **Scope of step 2** — how aggressively to extend the intrinsic sets. Every
   addition is a permanent widening. Recommendation: only tools observed in the
   sweep, each with a named test.
3. **This repo's own `AGENTS.md`** — leave `make test-unit` / `make test-all`
   uncredited, or reword to vocabulary terms? Recommendation: leave it. Rewording
   the file to please the scorer is the "grading your own homework" move, and the
   file is honest as written.
