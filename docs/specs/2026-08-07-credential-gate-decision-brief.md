# Decision brief: does the credential gate ship, and in what shape?

**Status:** open, awaiting decision · **Branch:** `docs/skillopt-import-adrs` at `0751e45`
**Written:** 2026-08-07, after the third code-review pass

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

## Not in scope

F1 (gradient target check + train/val split) and F4 (redaction patterns) ship regardless.
Two open F4 items from the third pass are ordinary bugs, not premise failures, and are worth
fixing whatever is decided here: short `PWD=` values are unredacted with no backstop
(`sanitize.py:36`), and the redaction set cannot match a modern `sk-proj-` key
(`sanitize.py:13`) — a miss that reaches a model provider.
