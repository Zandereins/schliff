# Spec: plugin-channel experiment — pre-registered

**Status:** pre-registered 2026-08-11 — no measurement below has been taken yet
**Branch:** `feat/plugin-channel-experiment`
**Written:** 2026-08-11, before Task 3 (README) or any submission

> This document is the falsification criteria, written down before the measure is taken. That
> ordering is the entire point: after the fact, any threshold can be rationalized to fit
> whatever happened. Before the fact, it can only be met or missed.

## Hypothesis and falsification

**Hypothesis:** making schliff's existing Claude Code plugin install path visible — first in
the README, then in third-party plugin marketplaces — produces measurable demand (a stranger's
signal or a traffic increase) that the current, invisible path does not.

**Falsified by:** the plugin path becomes visible in both places and, within the windows set by
Gate 1 and Gate 2 below, no signal above baseline appears. A negative result here is not
"marketing failed" — it is evidence that the 2026-08-04 bet's RED verdict, cashed while the
measuring instrument was off, generalizes: the constraint on schliff's growth is not
discoverability.

## Baseline

Collected 2026-08-11T12:52:19Z, `docs/experiments/plugin-channel/traffic.jsonl` line 1
(`"note":"baseline"`), GitHub's rolling 14-day window (2026-07-28 to 2026-08-10):

| Metric | Value |
| --- | --- |
| Views | 111 |
| Unique visitors | **32** |
| Clones | 1579 |
| Unique cloners | 330 (CI noise — the test matrix clones five times per run) |
| Stars | 13 |
| Forks | 1 (`webbrain-one`, a 13,728-repo account created 2026-06-21 — a mass-fork bot, not a user) |
| Referrers | `github.com` 9 uniques, Google 2, DuckDuckGo 1 — three humans arrived via search |

No referrer traffic from `awesome-claude-code`, although schliff is listed there twice.

Every number above is quoted from the file, not recomputed. `views.uniques` in the JSONL is
`32`; that is the baseline this spec's thresholds are built from.

## Gate 1 — distribution

**At least one of N = 2 qualified marketplaces merges a submission within 21 days of
submission.**

N and the qualified list come from `docs/experiments/plugin-channel/distributors.md`, measured
2026-08-11 against 14 candidates using the criterion "at least two distinct external (non-owner,
non-bot) authors merged PRs in the trailing 90 days":

| Repo | External authors in window | Fit to schliff |
| --- | --- | --- |
| `jeremylongshore/claude-code-plugins-plus-skills` | 3 | General plugins-and-skills marketplace |
| `Piebald-AI/claude-code-lsps` | 6 | LSP-server marketplace — schliff is a skill linter, not an LSP |

**Failure verdict:** `RED-DISTRIBUTION` — a finding about the channel, not about demand.

### The N = 2 finding, and why it is not softened

The plan expected three qualified distributors. Fourteen candidates were surveyed — the three
pre-measured ones, the official Anthropic directory, and eleven more found by search — and
**twelve failed to qualify**, most for reasons that only appear once the 90-day window and the
non-owner criterion are actually applied rather than read off star counts: `trailofbits`'s 20 of
22 merges are the repo's own CEO; `anthropics/claude-plugins-official`, at 33,394 stars, shows
zero external human merges in 90 days behind an automated bump pipeline; `hashicorp/agent-skills`
states outright in its own `CONTRIBUTING.md` that external contributions are not accepted, despite
five non-owner usernames appearing in the merge log. This is a pre-experiment finding about the
distribution channel itself: most repositories that look like plugin marketplaces by name, star
count, or push frequency are not currently distributing outside work at all. It is recorded here
as what it is, not smoothed into "N = 3, approximately."

### Judgement call: what N = 2 can and cannot carry

Gate 1 is kept exactly as originally framed — "≥1 of N merges within 21 days" — rather than
quietly redefined to compensate for N being smaller than planned. But N = 2 changes what a
result on either side of the gate is allowed to mean, and that has to be stated rather than left
implicit:

- **A GREEN result (a merge happens) is a mechanism test, not a channel-generalization test.**
  With N = 2, a merge shows "at least one gatekeeper will let schliff through," not "plugin
  marketplaces merge skill linters" as a class. That distinction matters more than usual here
  because one of the two qualifiers, `Piebald-AI/claude-code-lsps`, is a marketplace for LSP
  servers — thematically distant from a skill linter. A merge there is weaker evidence of
  channel *fit* than a merge at `jeremylongshore/claude-code-plugins-plus-skills`, whose scope
  is general plugins and skills. Gate 1 treats a merge at either repo as an equivalent pass; that
  equivalence is a known simplification of the gate, not a fact about the two channels.
- **A RED result (neither merges within 21 days) is equally thin in the other direction.** With
  N = 2, two non-merges could be idiosyncratic to two maintainers' review backlogs rather than
  evidence that "plugin marketplaces won't distribute schliff." A RED-DISTRIBUTION verdict from
  this gate supports "the two channels surveyed and reachable today did not merge it in 21 days"
  — it does not support the stronger claim "no viable distribution channel exists."
- **What would make the verdict strong enough to publish without this caveat:** a larger
  qualified pool. That pool does not currently exist per `distributors.md`; inventing one by
  loosening the qualification criterion (e.g., counting `hashicorp/agent-skills`'s five
  non-owner usernames despite its own stated policy) would repeat exactly the design flaw that
  made the 2026-08-04 bet uninformative — measuring against a channel that cannot produce a
  merge is not a measurement.

Net: Gate 1's verdict, whichever direction it lands, is reported alongside this caveat rather
than as a bare RED or GREEN. The gate is not abandoned or resized — it is exactly as thin as N =
2 makes it, and that thinness is disclosed rather than absorbed into the headline result.

## Gate 2 — demand

Within 30 days of the first acceptance under Gate 1:

**At least one qualitative signal from a stranger** (an issue, a question, a PR, or a mention
that is not a bot) **or** unique visitors ≥ 3× baseline (**≥ 96** per 14-day window, against the
32-unique baseline above).

**Failure verdict:** `RED-DEMAND` — and that one is final, because it is measured. There is no
retry: if the channel opens (Gate 1 passes) and no signal follows within the window, the
conclusion is that visibility was not the constraint.

Gate 2 only runs if Gate 1 passes. If Gate 1 fails, the experiment stops at
`RED-DISTRIBUTION` and Gate 2 is never reached — see below for why that separation matters.

## Why the two verdicts are separated

The 2026-08-04 bet died at the gatekeeper and never reached the demand question, which is what
made its verdict unusable: a RED result that could mean either "nobody wants this" or "nobody
could find this" is not a result. Splitting `RED-DISTRIBUTION` from `RED-DEMAND` means a failure
at Gate 1 is reported as a channel finding — the two currently-reachable marketplaces didn't
merge it — and is never conflated with a statement about whether anyone wants schliff. Only a
Gate 2 failure, reached after distribution actually happened, is allowed to say anything about
demand.

## What is deliberately not done

No announcement round. No second Show HN. The 2026-07-13 finding stands: a post from a cold
account has no reach, and content was never the problem (`feedback_cold_account_distribution`).
This experiment tests whether an existing, already-installable path becomes visible in places a
prospective user already looks — the README and marketplace listings — not whether a fresh
promotional push generates traffic. Adding an announcement round would reintroduce the
confound the 2026-08-04 bet already failed on: a positive result could then be attributed to the
announcement rather than to distribution visibility, and a negative result could be blamed on
weak promotion rather than measured as a channel or demand finding.

## How it will be judged, and by whom

The repository owner judges both gates by running the same commands anyone else could run
against the same artifacts, on the stated dates:

- Gate 1: `gh pr view <submission-PR-URL>` against each of the two qualified repos, checked for
  a merge commit dated within 21 days of the submission's opening. No other repo counts toward
  N, regardless of how promising it looks once visited — the qualified list is fixed by
  `distributors.md` and is not expanded after Gate 1 opens.
- Gate 2: `scripts/collect-traffic.sh`'s output in `traffic.jsonl` for the `uniques` field
  across the 30-day window, compared against the fixed baseline of 32 recorded above; and a scan
  of GitHub issues/PRs/mentions opened by accounts other than the repository owner and not
  flagged as bots.

Both thresholds are numbers fixed in this document before either measurement is taken. There is
no discretionary judgment call available at verdict time beyond the one already made and
disclosed above — the strength caveat on Gate 1 given N = 2. Nothing about the passing or
failing values can be adjusted after the traffic or PR data comes in.
