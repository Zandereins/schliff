# ADR 0019: Credential detection reports; it does not gate

- Status: supersedes ADR 0011, ADR 0014
- Date: 2026-08-10

## Context

ADR 0011 made credential detection gate-effective with no opt-out, and ADR 0014 named the two
surfaces that would carry the hard fail: `verify` and the GitHub Action. Both decisions were
sound *given* ADR 0012's premise that a token's shape separates a real credential from a
documentation placeholder. That premise is refuted; ADR 0020 records the measurement.

What remains is a classification the detector cannot make. Every narrowing produces a false
negative on a security gate, and every widening turns a third party's green build red. Three
review passes produced ten confirmed findings each, and the majority of each pass were
regressions from the previous pass's fixes — the errors move rather than disappear. That is
what an undecidable classification looks like from the inside, not a tuning problem.

Two facts decide how much that costs. `action.yml:22-25` defaults `schliff-version` to latest,
so Action users receive the behaviour on their next run without acting. And a false positive is
unfixable by the person it hits: they do not control schliff's release cycle and, under ADR
0011, have no flag, threshold or suppression to reach for.

A field measurement over this machine's real files makes it concrete. Across 128 instruction
files — the detector's actual target population — the scan produces **no findings at all**.
Across 601 documentation files it produces **11, every one of them documentation about
credentials**: a plan document listing secret-masking test fixtures, and schliff's own decision
brief. Zero real keys. A gate would have fired only where it was wrong.

## Decision

**No credential finding changes any exit code.** `verify` and the Action report it; neither
gates on it.

The Action keeps its step, downgraded to `::warning::` with the `exit 1` removed. Its `MISSING`
branch stays: a pinned pre-8.11 engine still says that no scan was performed rather than
implying a clean result.

**No opt-in flag ships.** A caller who wants enforcement reads the `credentials` field from
`score --json`, which is already the Action's own data source.

The fail-closed path in `verify` — exit 2 on a file that could not be read — is removed. It was
a gate stance: refusing to pass what could not be checked only makes sense while checking gates
something. Without it, failing a build because the tool could not look, while passing a file
that contains a real key, is incoherent. `credentials: null` survives as the third state, so
"could not look" is still never rendered as "clean"; `doctor` already holds that contract.

**What stays in force from ADR 0011:** score-neutrality, and its operative constraint. The
detector must never enter `scoring.security._CATEGORIES` — for `system_prompt` that dimension
is always-on and weighted 0.15, so an entry there would move a published composite silently.

**What stays in force from ADR 0014:** the finding payload rule — vendor and line number, the
matched value never in the data structure — and the rule that reporting surfaces do not change
exit codes, which is now simply universal. The gate-surface list is empty.

The post-release proof in `action-selftest.yml` becomes a **green**-path fixture: a file with a
vendor token must leave the job green and produce the warning annotation. It still cannot run
before release, for the reason ADR 0014 gave — `action.yml:63` installs the engine from PyPI.

## Why

The benefit that survives the refutation is the finding itself, and a report keeps all of it.
What a gate adds on top is the one property an undecidable classification must not have: the
power to break work that is not wrong.

The inversion is asymmetric, and that settles the direction of travel. Promoting a report back
to a gate is a minor release (ADR 0017) the day a precise discriminator exists. Retracting a
gate that has already turned other people's builds red is not — it costs the trust that made
anyone install a linter that grades their files in the first place.

ADR 0010 justified F3 on the grounds that *"a committed credential damages the one person who
has it, immediately and irreversibly"* — a harm that does not scale with adoption. That
argument survives the refutation intact, and it argues for reporting rather than for dropping
the feature: the person who needs to see the finding is the author, who is looking at the
output either way.

The counter-argument is real and is recorded here rather than answered away: a detector that
misses real keys offers false assurance, and false assurance can be worse than none. Two things
bound it. The finding is never presented as a clearance — schliff says what it found, never
that a file is clean — and ADR 0020 documents the miss classes in the CHANGELOG rather than in
a comment nobody reads.

Route B — maintained-but-parked, 12 stars, the demand bet cashed RED on 2026-08-04 — decides
the remaining margin. Every option that keeps the gate needs machinery (a baseline file, a
resolution path, a staleness story) that ADR 0010 declined on a project with more users than
this one has.

## Rejected

**Keep the gate, add a baseline or allowlist file.** How real scanners handle exactly this, and
it accepts precisely the apparatus ADR 0010 rejected. It also reopens ADR 0011's "no opt-out"
decision under another name: an allowlist is an opt-out with a file format attached.

**Drop F3 entirely.** Honest — schliff would stop claiming a capability it cannot deliver
deterministically — but it throws away a finding that is correct whenever it fires on a real
key, and ADR 0010's harm argument is unaffected by the refutation.

**An opt-in `--fail-on-credentials` flag.** Structurally different from the opt-out ADR 0011
declined, since its default is safe. Still rejected: nobody asked for it, it is a permanent
promise on a parked project, and the caller who wants it already has three lines of `jq`
against `score --json`.

**Keep the gate and keep tuning the patterns.** This is what the three review passes already
were. A defect count that does not fall across rounds is a statement about the design, not an
invitation to a fourth round.
