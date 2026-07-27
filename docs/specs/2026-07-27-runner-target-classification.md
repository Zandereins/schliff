# Runner-target classification (#133) — retire the `consumed_run` build fallback

- Status: **spec — decisions settled 2026-07-27, implementation not started**
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

2. **Add `pylint` to `_TEST_INTRINSIC` — and nothing else.** Scope settled by
   reading the set rather than by judgement: `_TEST_INTRINSIC` already carries 16
   tools (`black`, `eslint`, `flake8`, `isort`, `jest`, `mocha`, `mypy`, `nextest`,
   `nox`, `pre-commit`, `prettier`, `pyright`, `pytest`, `ruff`, `tox`, `vitest`).
   `pylint` is the only gap the sweep exposes, and `lint` is already a `_TEST_TOKEN`
   so the tool that performs it belongs there too. The earlier worry that step 3
   would wrongly drop `uv run ruff` was unfounded — `ruff` is already covered.

3. **Then fall through to `None`, not `build`.** An unrecognised target is
   unmeasured, which is what "we could not determine this" has always meant
   everywhere else in this engine. `npm run wibble` credits nothing.

Boundary matching (`test-*`, `test_*`, `test:*`) is deliberately **not** proposed
for `_RUNNER` verbs in this round. It is defensible there — `npm run` cannot occur
in prose — but adding a second mechanism in the same change would confound the
golden re-derivation. Revisit once this lands and is measured.

## Impact and golden handling

This is a **golden-touching** change. `test_agents_md_profile.py` pins mean,
median, min and band counts over the 30-file corpus and must be re-derived from
the engine, never hand-tuned.

Each step simulated separately over the corpus:

| variant | mean | vs today |
| --- | --- | --- |
| today | 37.17 | — |
| step 1 alone (read-only guard) | 37.17 | +0.00 |
| steps 1+2 (read-only + `pylint`) | 37.17 | +0.00 |
| steps 1+2+3 (full) | 36.50 | **−0.67** |

median, min and max are unchanged in every variant, and exactly **one of 30 files**
moves: `markov-kernel__databricks-mcp` 65 → 45.

That isolation matters for how the change is read. Steps 1 and 2 are **not
standalone wins** — they are the guard that stops step 3 from discarding genuine
test tools. Proposing them as improvements in their own right would misdescribe
them.

The −20 on the one file is a correction, not a regression. It documents
`uv run pytest`, `uv run black .`, `uv run pylint …` and a `-- --help` invocation
— **no build command at all**. The fallback was manufacturing one, and the engine
was reporting "real build command resolved" on that basis.

This repo's own `AGENTS.md` is unaffected: its 4 runner-delegated commands are all
exact-vocabulary hits (measured, `opcov` 100 with every category credited). The
published badge should not move; that is a gate, not an assumption.

## Review surface

The current behaviour is pinned as literals in
`TestRunnerClassificationCharacterization` (`test_operational_coverage.py`), split
into correct-today / defect A / defect B. **The rows marked DEFECT B are what this
change flips**, so the test diff is the review surface — it should be read line by
line rather than skimmed, and any row that moves unexpectedly is a finding.

Those tests exist because analysing this issue produced three successive causal
explanations of the module, each derived by reading it, and all three were wrong.
The implementation must not assert a score movement it has not measured.

## Verification plan

- TDD per step, red → green, one test per corpus-named case
- full suite green; `ruff==0.15.8` clean
- golden re-derived from the engine with the delta documented in the test comment
- own badge re-checked: `95.8` in-repo == isolated, or the change is justified in writing
- re-run the 259-file sweep and confirm no new false credit appears

## Decisions (settled 2026-07-27)

1. **Defect A is won't-fix.** `make test-unit` stays invisible and the limit is
   documented instead. Buying 2 genuine commands would cost 14 non-commands, and
   the prose guard is the reason `check-commands` has never made a false claim.
   The README now states the tradeoff with the measurement rather than a
   mechanism (#137).
2. **An unknown project script is not a build command.** `npm run gateway` no
   longer credits `build`. The engine may not report "real build command
   resolved" about a target it never inspected — that is the same class of
   unsupported claim #134 set out to remove from this repo.
3. **Step 2 is `pylint` only.** Answered by reading `_TEST_INTRINSIC`, not by
   judgement: 16 tools are already covered, `pylint` is the single gap.
4. **This repo's own `AGENTS.md` is not reworded.** `make test-unit` stays
   uncredited. Measured cost: zero — `opcov` is already 100 with every category
   credited, carried by `make lint`, the `pytest` invocation and `python -m build`.
   Rewriting a file so the project's own scorer likes it better is the
   grading-your-own-homework move, and here it would not even buy a point.
5. **Sequencing.** README correction (#137) and the characterization baseline
   (#138) land before the engine change, so the implementation's effect is a
   checkable diff rather than an argument.
