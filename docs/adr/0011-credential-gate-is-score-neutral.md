# ADR 0011: Credential detection is score-neutral and gate-effective

- Status: accepted
- Date: 2026-08-06

## Context

Adding credential detection to schliff raised an apparent binary: fold it into the security
dimension so it affects the composite and therefore CI gates, or keep it purely informational
so nothing breaks.

Both branches are bad. schliff has **no rubric-versioning mechanism** — no `RUBRIC_VERSION`,
nothing — so a score-affecting change has nothing to soften its landing. And the README
publicly recommends pinning an absolute threshold in two places (`--min-score 75` in the CI
recipe and the pre-commit hook), so a composite shift breaks advice schliff itself published.

The purely informational branch is worse in a different way: `schliff verify AGENTS.md
--min-score 75` would print the finding and **exit 0**. Detecting a credential and then
waving it through the gate is the exact state the work was meant to end.

## Decision

Credential detection changes no score and no threshold. The composite is bit-identical before
and after. `verify` exits non-zero when a credential is found, independently of `--min-score`.

**The operative constraint:** the detector must stay out of `scoring/security.py`'s
`_CATEGORIES`. A category there carries a penalty, and for `system_prompt` the security
dimension is always-on and weighted 0.15 in the composite (`shared.py:224-228` skips the
`include_security` gate for that format; `registry.py:29`). A `_CATEGORIES` entry would
therefore move the system-prompt composite and break this ADR silently, on the one format
where nobody would look for it.

No opt-out flag ships.

## Why

The false binary dissolved once "score-affecting" and "gate-effective" were separated. A leak
is not a quality deduction that belongs on the same scale as three missing trigger phrases —
it is a categorical failure. Modelling it as a hard fail rather than a penalty gives the full
protective effect at zero compatibility cost: badges, comparisons, the leaderboard shape and
every pinned threshold behave exactly as before, so no rubric versioning is needed.

The change is still breaking in behaviour — a green CI can turn red — but it fires only where
a structurally valid vendor token is actually present, which is the correct build failure.

## Rejected

**Score-affecting.** Shifts every composite, invalidates pinned thresholds, and needs a
versioning mechanism that does not exist. Buys nothing the hard fail does not already buy.

**Purely informational.** Leaves the credential passing the gate. Detecting and permitting is
worse than either extreme, because it produces the appearance of protection.

**An `--allow-secrets` opt-out.** An escape hatch on a security gate becomes the default
copy-paste line within a release or two. If a legitimate value trips the detector, that is a
pattern bug to fix in the pattern, not a switch to hand the user.
