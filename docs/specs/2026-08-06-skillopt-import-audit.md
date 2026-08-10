# What schliff should take from microsoft/SkillOpt — and what it must not

**Status:** resolved by grilling, 2026-08-06 · **Branch:** — · **Audited:** 2026-08-06, `main` at `1893358`
**Source:** `microsoft/SkillOpt` @ `9639719` (MIT, Microsoft Corp. 2026), full read of the tree

> **Superseded in several places**, by a grilling session and two adversarial review passes on
> 2026-08-06. Refuted: the F1 fix (neither a split nor a read-only policy — the defect is that
> `generate_patches` never checks `target`, ADR 0015), the F3 placement (*"reusing the existing
> machinery"* would build a blind detector — ADR 0012, ADR 0016), the F3 open decision
> (non-scoring first was the wrong frame — ADR 0011), and two thirds of the F4 gap inventory
> (`AIza`, `gho_` and `Password=` were already shipped — ADR 0010). The corrections are inline
> below. Decisions of record: **ADR 0010–0017**. Vocabulary: `docs/specs/glossary.md`.
> Final scope: **F3 → F1 → F4, F2 rejected**, shipping as 8.11.0.
>
> Both review passes ended at the round cap rather than converging, with roughly 25 unverified
> candidates each. These documents are more correct than they were; they are not proven correct.

Second-pass audit. The first pass looked at the training loop; this one covers security,
robustness, and the two places SkillOpt touches schliff's own domain. Every candidate was
checked against schliff's actual code before it was kept.

## Refuted — do not import these

Three obvious-looking imports are already covered, better, in schliff. Recorded so they
are not proposed again.

| SkillOpt offers | schliff already has | Verdict |
| --- | --- | --- |
| `skillopt_sleep/skill_resolver.py` — resolve skill name, states `found/missing/ambiguous/rejected` | `scoring/command_resolution.py` — three-state with **"anything unprovable is `unknown`, never `dangling`"** (`:11-13`), symlink containment `_contained` (`:76-88`), unresolved-include tracking | schliff is **stricter**. It refuses to claim absence without proof; SkillOpt has no such rule. |
| `optimizer/skill.py:apply_patch_with_report` — per-edit applied/unmatched status (2 dedicated test files) | `text_gradient.py:845 apply_patches` returns `applied/skipped/errors`; `auto-improve.py:435` explicitly skips when `applied == 0` | Already covered. No latent "unmatched edit counted as applied" bug. |
| `skillopt_sleep/staging.py:_SECRET_PATTERNS` — redaction before writing artifacts | `evolve/sanitize.py:12-26` — 7 patterns incl. `sk-ant-` (which SkillOpt **lacks**) | Not a gap. See F4 for the narrow real delta. |

## F1 — `auto-improve.py` gates on the rubric that produced the edit

The loop accepts a change when schliff's **own composite** rises (`auto-improve.py:1-20`,
`:427-471`). That composite is the same rubric `text_gradient.py` inverted to generate the
change. There is no held-out set, so a reported "+3.5 composite" can be the rubric agreeing
with itself.

schliff already knows this: `runtime-evaluator.py:5-7` says *"scoring measures file patterns,
not runtime behavior. The runtime evaluator bridges that gap."* The evaluator exists but is
not wired to the keep/revert decision.

**CORRECTED TWICE — the split is not the fix, and neither is a read-only policy.** An earlier
correction claimed the loop rewrites the exam it is measured against; the code does not support
that, since no writer in the loop touches `eval-suite.json` (the only one anywhere is
`init-skill.py:898`, driven by `/schliff:init`). The real defect is that **`generate_patches`
filters on confidence and effort and never on `target`**, while eleven gradients target
`eval-suite.json` and `apply_patches` only ever writes `skill_path`. Two of those eleven
(`:480`, `:491`) already pass the filter and are inert only because no handler exists for their
issue strings.

**Fix (per ADR 0015):** a target check in `generate_patches` — a gradient is applied only to the
file its `target` names. The split is a separate, still-valid measurement decision.

- `eval-suite.json` gains a per-case `split` field (`train` | `val` | `test`); gradients come
  from `train`, the gate reads `val`.
- Where the case count cannot carry a split, the report **says so**. Real suites hold 44
  `triggers` (22/22 meaningful) and 14 `edge_cases` (7/7 workable) but only 4 `test_cases`
  (2/2 is not).
- Reference: `skillopt_sleep/consolidate.py:54-90` (`_split` returns `holdout_leaked`) and the
  pure decision function in `skillopt_sleep/gate.py`. Deterministic, netzfrei, zero new deps.

## F2 — the runtime evaluator tests a fragment, not the substrate

`runtime-evaluator.py:54-69` embeds the skill as **untrusted text inside a prompt**, wrapped
in a nonce tag. It never installs the skill or loads it through an activation path — there is
no `--plugin-dir` and no skills-dir install anywhere in `skills/schliff/scripts/`.

That measures "does the model answer well when handed this text". It cannot measure "does
this skill get selected and behave" — the skill is force-fed, so selection never happens.
This is the failure recorded in `feedback_probe_against_original_substrate` and the CLAUDE.md
rule *"Modell-/Agent-Inputs mit dem ECHTEN Agent testen"*.

**Import:** the harness shape from `skillopt_sleep/adapters/superpowers.py:1-18` — clone a
host at a **pinned SHA** into a temp workspace, overlay the candidate skill, load it through
the **normal plugin bootstrap** so the real activation path runs, and score with **rule-based
judges over harness-collected evidence, no LLM self-grading**. That last clause is schliff's
own philosophy; SkillOpt states it explicitly in its docstring.

Carry their scope warning verbatim: the evaluated agent gets Bash as the same OS user, so
evidence is tamper-**evident**, not tamper-proof. Trusted local candidates only.

This stays on the existing opt-in runtime path — the deterministic core keeps its
"no model in the loop" promise untouched.

## F3 — the security dimension detects no credentials

`scoring/security.py:171 score_security` has negation-awareness (`_preceded_by_negation`),
code-block awareness (`_find_code_block_ranges`), and domain detection (`_is_security_domain`)
— but **zero credential patterns**. Confirmed: no `sk-`/`AKIA`/`ghp_`/`eyJ` anywhere under
`scoring/`. The patterns exist only in `evolve/sanitize.py`, which is the opt-in LLM path.

So schliff scores an `AGENTS.md` with a live API key in it without a word. Committed
instruction files are a real leak surface, and detecting it is purely deterministic — exactly
schliff's wheelhouse.

The existing `_in_code_block` and `_preceded_by_negation` machinery is what makes this
feasible without wrecking legitimate content: a doc showing `export OPENAI_API_KEY=sk-...`
as an example must not be flagged as a leak. See `feedback_overcorrection_pattern` and
`feedback_syntax_collision_detectors`.

**RESOLVED — the open decision was a false binary.** "Score-affecting" and "gate-effective" are
separable. The gate is **score-neutral and gate-effective** (ADR 0011): the composite is
bit-identical, `verify` and the Action exit non-zero on a finding, no `--allow-secrets`.

**CORRECTED — do not reuse the existing machinery as written above.** `_in_code_block`
(`security.py:215`) and `_preceded_by_negation` (`:220`) both **suppress**. Inheriting them
would blind the detector exactly where keys live — `export ANTHROPIC_API_KEY=sk-ant-…` inside a
fence, or *"never commit your `sk-ant-…` key"*. Credentials are exempt from both, as
`obfuscation` already is; the discriminator is the **value**, not the location (ADR 0012).

**CORRECTED — it cannot live in `score_security`.** That dimension is opt-in
(`shared.py:250`) and would never run in the plain `schliff score --json` the Action calls. It
is an always-on check over the **raw bytes** of the real file, before `normalize_content` and
the temp-file swap at `shared.py:241` (ADR 0016).

Surfaces: `verify` + the Action gate; `score --json` carries the finding as data; `doctor`,
`compare`, `report` display it and never change their exit code (ADR 0014).

`feedback_field_test_over_fixtures` still applies — measure the false-positive rate against the
tracked corpus, not synthetic fixtures.

## F4 — two narrow pattern gaps in `evolve/sanitize.py`

**This set stays separate from F3's** (ADR 0013). Redaction and detection have opposite error
costs: a false positive here is harmless, a false negative leaks to the provider — so this set
may be aggressive, while F3's must be precise. `Password=`/`Pwd=` therefore belong here **only**.

**CORRECTED — two thirds of this gap did not exist.** `sanitize.py:25` already carries
`AIza[a-zA-Z0-9_-]{35}` and `:20` already carries `gho_[a-zA-Z0-9]{36}`, both inside the very
range cited above. The verified residual delta, from the side-by-side with `staging.py:105-204`:

- The GitHub patterns are bounded at **exactly 36** characters and cover only `ghp_` (`:19`)
  and `gho_` (`:20`). SkillOpt uses `gh[pousr]_[A-Za-z0-9]{20,}` — the missing part is the
  `ghu_`/`ghs_`/`ghr_` prefixes and the variable length bound.
- No ODBC `Pwd=`. **`Password=` is NOT a gap** — the generic assignment catcher at
  `sanitize.py:41` lists `password`/`passwd` and already redacts it; running the shipped
  `redact_secrets` on a connection string confirms it.
- SkillOpt distinguishes ODBC `Pwd=` from the conventional all-caps `PWD` working-directory
  variable (`staging.py:144-150`). Worth copying if `Pwd` is adopted.

**CORRECTED — not via `validate_regex_complexity`** (ADR 0013). That validator's only
production call sites are `runtime-evaluator.py:123` and `scoring/runtime.py:164`, both on
eval-suite-supplied regexes; it guards *untrusted* patterns, not first-party ones. Run over the
16 live `_SECRET_PATTERNS` it fails one that already ships — `sanitize.py:24` trips the
nested-quantifier heuristic on `\s+(RSA\s+)?`. First-party patterns are instead guarded by a
**ReDoS timing test**: pathological input of defined length, wall-clock bound. See
`feedback_redos_untrusted_regex` and the existing `test_scoring_redos.py`.

## Explicitly out of scope

- **The LLM optimizer path** (`gradient/reflect.py`, `gradient/aggregate.py`, `optimizer/clip.py`,
  `optimizer/lr_autonomous.py`). Every stage is a `chat_optimizer` call. Adopting it means
  `openai` + `azure-identity` as dependencies, an API budget, and non-determinism — it deletes
  the positioning that differentiates schliff from agnix.
- **The harvest layer** (`skillopt_sleep/harvest*.py`, ~9k LOC over 5 agents). Documented data
  boundary: *"Outbound prompts are not currently guaranteed to be secret-free"*
  (`docs/sleep/README.md:29-33`). Reopens the question ADR 0008/0009 just closed.
- **The five plugin integrations.** The opposite of Route B.

## Sequencing — CORRECTED

**F3 → F1 → F4. F2 is rejected** (ADR 0010).

F1 moved behind F3: `auto-improve` is not a subcommand of the shipped CLI (no hit in
`cli.py`) and `/schliff:auto` is barred from unattended use, so the lying gate sits on a path
nobody currently runs unsupervised. F3 sits on the surfaces actually in use.

Three PRs, one minor **8.11.0** (ADR 0017), with the CHANGELOG entry under **BREAKING
BEHAVIOUR**, a **CLI test** proving the red path (`verify` exits non-zero on a credential
fixture), and the **three version constants** moved in lockstep — `pyproject.toml:7`,
`.claude-plugin/plugin.json:3`, `skills/schliff/__init__.py:3` — plus the separate cosmetic
README/docs occurrences.

The matching `action-selftest.yml` fixture is a **post-release follow-up**, not part of this
release: `action.yml:63` installs the engine from PyPI and all five self-test jobs enter via
`uses: ./`, so a fixture added now would exercise 8.10.1 and pass for the wrong reason
(ADR 0014, ADR 0017).

## Open questions

None blocking. The F2 host-pinning question is moot while F2 is rejected; if it is ever
revived, a purpose-built fixture beats schliff's own skill —
`feedback_suite_extracted_from_artifact` (a suite derived from the artifact grades it 100% by
construction).
