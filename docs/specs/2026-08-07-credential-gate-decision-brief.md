# Decision brief: does the credential gate ship, and in what shape?

**Status:** decided 2026-08-10 — **(a) report, do not gate**, implemented in ADR 0019 and
ADR 0020 · **Branch:** `docs/skillopt-import-adrs`
**Written:** 2026-08-07, after the third code-review pass

> The decision this brief was written to force has been taken, so the document below is the
> record of the question and not a live proposal. What was settled, beyond the headline: no
> opt-in flag; the Action annotates with a warning and never fails; the vendor patterns widen
> (the repeated-run heuristic is gone, hyphens are allowed behind a known OpenAI prefix, JWTs
> stay out); the CHANGELOG's BREAKING section is withdrawn; `verify`'s fail-closed exit 2 on an
> unreadable file is withdrawn with it, while `credentials: null` survives as the third state;
> the `action-selftest.yml` follow-up becomes a **green**-path fixture (post-release, since the
> Action installs from PyPI); and ADR 0016 is untouched.
>
> One measurement was added after the fact and is not in the analysis below: across 128 real
> instruction files the detector finds nothing, and across ~600 documentation files every
> finding it produces is documentation *about* credentials. See ADR 0020.

Input for a grilling session. Everything here was measured on the branch, not inferred.
The decision is F3's alone; **F1 and F4 are unaffected and healthy.**

## The measurement that forces the decision

Run against `scoring/credentials.py` as it stands on `0751e45`:

| Input | What it is | Gate |
| --- | --- | --- |
| `sk-proj-Ab3d-Kf9LmQ2xR7tYu1VwZ0nBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789abcdef` | **real** OpenAI project key | **silent** |
| `AKIA0000TUVWXY3BCDEF` | **real** AWS key | **silent** |
| `AKIA1234567890ABCDEF` | documentation placeholder | **fires** |
| `ghp_abcdefghijklmnopqrstuvwxyz012345` | documentation placeholder | **fires** |

It misses real keys and fires on invented ones. Same input set, opposite of the intent.

## The claim that turned out to be false

ADR 0012, `## Why`, first paragraph:

> Location carries no information about whether a token is real; shape carries all of it.

`AKIA1234567890ABCDEF` and `AKIAJ7QRTUVWXY3BCDEF` are structurally identical and both
satisfy every rule the ADR specifies. One belongs in a README, the other is a credential.
Shape does not separate them.

The placeholder heuristic (`_PLACEHOLDER_MARKERS` plus a four-identical-character run) was
the patch for that gap. It both over- and under-fires: it eats a real key containing `0000`,
and it passes any dummy that avoids its marker words.

**Every narrowing produces a false negative on a security gate. Every widening breaks a third
party's CI.** That is not a tuning problem; it is what an undecidable classification looks
like from the inside.

## Why more iteration is not the answer

| Pass | Findings | Of which were regressions from the previous pass's fixes |
| --- | --- | --- |
| 1 | 10 | — |
| 2 | 10 | 6 |
| 3 | 10 | 4 (plus one I found myself before the run) |

Thirty confirmed findings. The defect count per pass is flat while the subsystem churns —
the errors move rather than disappear. Every pass was verified by execution, so this is not
reviewer noise.

Real secret scanners solve this with entropy scoring, live verification against the vendor
API, allowlists and baseline files. That is precisely the machinery ADR 0010 declined when it
rejected SkillOpt's heavier apparatus, and it is a different product from a deterministic
rubric linter.

## What makes it dangerous rather than merely wrong

ADR 0011 decided **no opt-out ships** — no `--allow-secrets`, no threshold, no suppression.
That decision was sound *given* the assumption that precision was achievable. With the
assumption gone, it is the thing that converts a false positive into an unfixable red build
for someone who does not control schliff's release cycle. `action.yml` also defaults
`schliff-version` to latest, so Action users receive the behaviour without acting.

## The options

**(a) Report, do not gate.** The finding appears in `score`, `doctor` and `verify` output;
no exit code changes. Supersedes ADR 0011's gate-effectiveness. Keeps the whole benefit that
survives the refutation — you see the finding — and removes the property that makes an
undecidable classification harmful. Cost: a leak no longer fails CI, so the feature stops
being a gate and becomes a report.

**(b) Keep the gate, add a baseline/allowlist file.** Matches how real scanners handle
exactly this. Cost: accepts the machinery ADR 0010 rejected, adds a file format, a
resolution path and a staleness problem, and reopens the "no opt-out" decision anyway — an
allowlist *is* an opt-out with extra steps.

**(c) Drop F3.** Ship F1 and F4, point the README at gitleaks. Cost: the audit's most
user-visible item disappears; the honest gain is that schliff stops claiming a capability it
cannot deliver deterministically.

**Recommendation: (a).** It is the only option that neither invents machinery the project
declined nor abandons the finding. It also inverts cleanly: if a precise discriminator is
ever found, promoting a report back to a gate is a minor release, whereas retracting a gate
that broke builds is not.

## Standing pressure for the grilling

Route B — maintained-but-parked, 12 stars, demand bet cashed RED 2026-08-04. F3 was justified
in ADR 0010 on the grounds that *"a committed credential damages the one person who has it,
immediately and irreversibly"* — a harm that does not scale with adoption. That argument
survives the refutation and argues for (a) over (c). The counter-argument is that a detector
which misses real keys offers false assurance, which can be worse than none.

## Questions the grilling has to settle

- Does the gate become a report (a), gain an allowlist (b), or go away (c)?
- If (a): does `verify` keep a non-zero exit behind an explicit opt-**in** flag, or none at all?
- Do the vendor patterns stay as they are, get widened for recall now that a false positive
  is cheap, or get narrowed to the classes with no plausible documentation form?
- What happens to the CHANGELOG entry, which is currently filed under BREAKING BEHAVIOUR for
  a behaviour that may not ship?
- ADR 0011, 0012, 0014 and 0016 all rest on the refuted premise to some degree. Which are
  superseded, and which merely need their reasoning corrected?

## Not in scope — but still open

F1 (gradient target check + train/val split) and F4 (redaction patterns) ship regardless of
this decision. **Four findings from the third pass were ordinary bugs rather than premise
failures. All four are closed in `846e171`; they needed no decision:**

- `evolve/sanitize.py:36` — short `PWD=` values went unredacted and no other pattern covers
  the ODBC spelling, so the generic assignment catcher did not backstop it. Was:
  `redact_secrets('conn: Server=x;PWD=abc123;DB=y')` returned the string unchanged. Fixed by
  dropping the invented eight-character floor; `$PWD` and lowercase `pwd=` still survive.
- `evolve/sanitize.py:13` — the redaction set could not match a modern `sk-proj-` OpenAI key
  (alnum-only body stops at the hyphen). A miss here reaches a model provider, which is the
  expensive direction for redaction (ADR 0013). Fixed by allowing hyphens **behind a known
  key prefix only**: a bare `sk-` with hyphens would have eaten kebab-case prose such as
  `sk-add-credential-scanning-to-verify`, and over-redaction destroys the prompt it protects.
- `auto-improve.py:321` — the empty-val guard fired only when **all three** populations were
  empty, so holding out only triggers left `quality` and `edges` at the unmeasured sentinel
  on the gate and destructive patches reached the user's SKILL.md. Fixed per population:
  each population with no val cases falls back to the full suite and `gate_suite` names it,
  while populations that do hold out keep their holdout. Measured on schliff's own 44/4/14
  suite — the gate saw `quality -1, edges -1`, and now sees `90, 100`.
- `auto-improve.py:404` — `_should_stop` received the val-basis score, so the documented
  "composite reaches 98+" stop was evaluated against a number no other schliff surface
  produces: a run printed `Baseline: 95.3` (gate basis) while the summary reported `99 → 99`.
  The basis sweep of `a335ff9` was incomplete. Fixed: the stop check runs on the reported
  basis, re-measured after each keep, and the verbose baseline line prints the reported
  figure with the gate's number labelled beside it.

Nothing in the four touches `scoring/credentials.py`, so the decision below is unchanged by
them. The branch now has exactly one open question.

## The rest of the backlog

- **Version bump to 8.11.0** — its own `chore(release):` commit touching `pyproject.toml:7`,
  `.claude-plugin/plugin.json:3`, `skills/schliff/__init__.py:3` (the three constants
  `test_version_consistency.py` asserts), plus `README.md`, `docs/README.md` and the badge
  cache-bust. A release step, not a feature step (ADR 0017).
- **The CHANGELOG entry** currently sits under BREAKING BEHAVIOUR for a behaviour that may
  not ship. It follows the decision.
- **Push and PR** — nothing has left the local tree. The branch is ten commits.
- **The `action-selftest.yml` fixture** remains a post-release follow-up, now proving the
  **green** path: a file with a vendor token must leave the job green and produce the warning
  annotation. The timing constraint is unchanged — the composite action installs from PyPI, so
  no self-test can exercise a scan that is not published yet (ADR 0014, ADR 0019).
