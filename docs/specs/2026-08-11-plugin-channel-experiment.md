# Spec: plugin-channel experiment — pre-registered

**Status:** pre-registered 2026-08-11 — no *outcome* measurement below has been taken yet. The
baseline and distributor tables were measured that day; every threshold they feed is fixed before
the intervention, and no gate has been evaluated.
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

## The clock — when the windows start and stop

Written before submission, because "21 days from submission" fixes nothing while the submission
date is open-ended. Without this section the experiment can sit indefinitely in neither GREEN nor
RED, which is the same non-result the 2026-08-04 bet produced.

**D0 (Gate 1 start).** The UTC date on which the **first** submission PR is opened at either
qualified marketplace. Whichever repo is submitted to first sets D0; a later submission to the
second repo does not restart or extend the clock. When that PR is opened, its URL and opening
date are recorded in the table below, in this file, in the same commit that does nothing else.
The clock is not "when Franz decides to start" — it is an event with a public timestamp
(`gh pr view <URL> --json createdAt`) that neither side can move afterwards.

| Field | Value |
| --- | --- |
| D0 (first submission PR opened, UTC) | *not yet submitted — record here when it happens* |
| First submission PR URL | *not yet submitted* |
| Second submission PR URL (if any) | *not yet submitted* |

**Abandonment deadline.** If no submission PR has been opened at either qualified marketplace by
**23:59 UTC on 2026-09-30**, the experiment is over. It is recorded in this file as
`ABANDONED-UNSUBMITTED`, and that is a real, reportable outcome, not a pause: it says the
intervention was never delivered, so neither the distribution question nor the demand question
was tested by this branch. It is explicitly **not** reported as RED-DISTRIBUTION — nothing was
put in front of a gatekeeper, so nothing was learned about gatekeepers. The one thing this
deadline forbids is letting the experiment stay open forever by never starting it. The date may
not be extended once passed; a later attempt is a new experiment with a new pre-registration.

**Day boundaries.** All windows are counted in whole UTC days, with D0 itself counted as day 0
(the day the PR opens is not day 1). Both windows are **inclusive of their final day**:

| Window | Opens | Resolves |
| --- | --- | --- |
| Gate 1 (21 days) | D0, 00:00 UTC | **23:59 UTC on D0+21** |
| Gate 2 (30 days) | A0, 00:00 UTC | **23:59 UTC on A0+30** |
| README-only observation (see below) | 2026-08-11 | **23:59 UTC on 2026-09-10** |

where **A0** is the UTC date of the first merge under Gate 1 (`mergedAt` of the merged submission
PR). A merge committed at 23:55 UTC on D0+21 passes Gate 1; one at 00:05 UTC on D0+22 does not.
The comparison is made against the timestamps GitHub reports, in UTC, not against local time.

## Gate 1 — distribution

**At least one of N = 2 qualified marketplaces merges a submission on or before 23:59 UTC on
D0+21**, where D0 is defined above.

N and the qualified list come from `docs/experiments/plugin-channel/distributors.md`, measured
2026-08-11 against 14 candidates using the criterion "at least two distinct external (non-owner,
non-bot) authors merged PRs in the trailing 90 days":

| Repo | External authors in window | Fit to schliff |
| --- | --- | --- |
| `jeremylongshore/claude-code-plugins-plus-skills` | 15 | General plugins-and-skills marketplace |
| `Piebald-AI/claude-code-lsps` | 6 | LSP-server marketplace — schliff is a skill linter, not an LSP |

The first figure was corrected from 3 to 15 on 2026-08-11 (a default `gh pr list` limit had
truncated the original count); see the `Corrections` section of `distributors.md`. The correction
does not change N — both figures clear the bar of 2 — but it does change which of the two
channels carries Gate 1, as the caveat below records.

**Failure verdict:** `RED-DISTRIBUTION` — a finding about the channel, not about demand.

### The N = 2 finding, and why it is not softened

The plan expected three qualified distributors. Fourteen candidates were surveyed — the three
pre-measured ones, the official Anthropic directory, and eleven more found by search — and
**twelve failed to qualify**, most for reasons that only appear once the 90-day window and the
non-owner criterion are actually applied rather than read off star counts: `trailofbits`'s 17 of
20 merges are the repo's own CEO; `anthropics/claude-plugins-official`, at 33,394 stars, shows
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
- **A RED result (neither merges within 21 days) is equally thin in the other direction, and for
  the same reason — effective N is 1, not 2.** The asymmetry disclosed above about a GREEN
  applies with full force to a RED, and it must be stated here too rather than left for the
  reader to carry over: **a non-merge at `Piebald-AI/claude-code-lsps` is uninformative by
  construction.** That repo distributes LSP servers. schliff is a skill linter and not an LSP
  server, so a submission there is outside the marketplace's stated scope, and a maintainer
  declining an out-of-scope submission is the correct behaviour of a healthy channel — it is not
  evidence about whether marketplaces will distribute skill linters. Nothing is learned from that
  half of N in the RED direction. A RED-DISTRIBUTION verdict therefore rests, in substance, on a
  single observation: `jeremylongshore/claude-code-plugins-plus-skills` not merging by 23:59 UTC
  on D0+21. One non-merge at one general marketplace can be idiosyncratic to one maintainer's
  review backlog. So RED-DISTRIBUTION supports at most "the one in-scope channel reachable today
  did not merge it inside the window, and one out-of-scope channel also did not" — it does not support "plugin
  marketplaces won't distribute schliff," and it does not support "no viable distribution channel
  exists."
- **Both verdicts are reported with the same denominator.** The temptation this bullet exists to
  block is reporting a GREEN as "1 of 2 merged" while reporting a RED as "0 of 2 merged" — the
  first quietly discounting Piebald as a weak pass, the second quietly counting it as a full
  failure. Whichever way Gate 1 lands, the result is written as **1 in-scope channel plus 1
  out-of-scope channel**, with the per-repo outcome named, never as a bare fraction of 2.
- **What would make the verdict strong enough to publish without this caveat:** a larger
  qualified pool. That pool does not currently exist per `distributors.md`; inventing one by
  loosening the qualification criterion (e.g., counting `hashicorp/agent-skills`'s five
  non-owner usernames despite its own stated policy) would repeat exactly the design flaw that
  made the 2026-08-04 bet uninformative — measuring against a channel that cannot produce a
  merge is not a measurement.

Net: Gate 1's verdict, whichever direction it lands, is reported alongside this caveat rather
than as a bare RED or GREEN. The gate is not abandoned or resized — it is exactly as thin as a
nominal N of 2 and an effective N of 1 make it, and that thinness is disclosed rather than
absorbed into the headline result. This is also why Observation R exists: with Gate 1 resting on
a single in-scope channel, the probability that this experiment ends at `RED-DISTRIBUTION`
without ever reaching the demand question is high enough that the README arm needs its own
unconditional reading.

## Gate 2 — demand

From A0 (the UTC date of the first merge under Gate 1) to 23:59 UTC on A0+30, Gate 2 passes if
**either** branch below is satisfied. They are an OR, so the weaker branch decides the gate — which
is why the qualitative branch is specified at length rather than left to judgement.

**Quantitative branch:** unique visitors ≥ 3× baseline (**≥ 96**, GitHub's 14-day rolling window,
against the 32-unique baseline above).

**Qualitative branch:** at least one signal meeting **all four** of the conditions below. Any
signal failing even one of them does not count, however encouraging it looks.

The earlier phrasing of this branch — "a qualitative signal from a stranger (an issue, a
question, a PR, or a mention that is not a bot)" — is replaced, because it could not fail. It
named no surface, no search, and no link to the plugin channel, and it operationalised "stranger"
as merely "not the owner and not a bot" — a bar a friend, a colleague, or someone the owner
directly asked would clear. A gate that a solicited signal can satisfy is not a gate.

**(1) Surface — it must occur on one of these three, and nowhere else counts:**

| # | Surface | How it is found |
| --- | --- | --- |
| S1 | An issue, pull request, or discussion opened on `Zandereins/schliff` | `gh issue list --repo Zandereins/schliff --state all --limit 200 --json number,author,createdAt`, same for `gh pr list`, and `gh api graphql` for discussions; filter to `createdAt` inside the window |
| S2 | A file committed to a **public GitHub repository outside the owner's account** that references schliff's plugin install path | `gh api -X GET search/code -f q='"Zandereins/schliff" -user:Zandereins'` and `gh api -X GET search/code -f q='"schliff@schliff" -user:Zandereins'` |
| S3 | A comment by a third party (not the owner, not a maintainer of that marketplace) on either submission PR | `gh pr view <URL> --json comments` |

Anything not reachable by one of those commands is out of scope: no private messages, no Discord,
no "someone told me they saw it." If a signal cannot be produced by a command another person can
re-run against public data, it does not exist for this gate.

**(1b) Dating — a hit must be shown to post-date D0, or it does not count.**

Surfacing a hit is not the same as showing it happened *after* the intervention. S1 carries a
`createdAt` and is filtered on it, but `search/code` returns **no date at all**, and an
undated S2 hit would let a file that already existed before any submission — a marketplace config
that happens to list schliff, written by a genuine stranger months ago — satisfy every other
condition and be counted as demand produced by an intervention that had not happened yet. That
would not be a weak signal; it would be evidence from the wrong side of the experiment. The rules
below are mechanical on purpose: a reviewer who is not the author, months from now, must reach the
same verdict without judgement.

| Surface | Dating rule |
| --- | --- |
| S1 | `createdAt` of the issue/PR/discussion must fall inside the window. Already filtered by the command above. |
| S3 | `createdAt` of the comment must fall inside the window — `gh pr view <URL> --json comments` returns it per comment. |
| S2 | Not directly dated by the search API. Use the two-step procedure below. |

**The pre-D0 S2 baseline (do this before submitting anything).** Both S2 queries are run once
*before* D0 and their full result set — repository, path, and the date of capture — is committed
to `docs/experiments/plugin-channel/s2-baseline.md`. Every repository/path pair in that snapshot
is pre-existing by definition and is **permanently excluded** from S2, with no dating work
required. This must be captured before the first submission PR is opened; **if D0 arrives with no
committed baseline, the S2 branch is void** and only S1 and S3 remain available. A control taken
after the intervention is not a control.

**Dating a hit that is not in the baseline.** Given a hit at `OWNER/REPO` path `P`:

1. Find the last commit touching `P` before D0:

   ```bash
   gh api "repos/OWNER/REPO/commits?path=P&until=<D0>T00:00:00Z&per_page=1" --jq '.[0].sha'
   ```

2. **Empty result** — the path did not exist before D0. The hit post-dates the intervention.
   **Counts.**
3. **A sha comes back** — fetch the file as it stood at that commit and look for the reference:

   ```bash
   gh api "repos/OWNER/REPO/contents/P?ref=<sha>" --jq '.content' | base64 --decode
   ```

   If the schliff plugin reference is already present in that content, the reference pre-dates D0
   and the hit is **excluded**. If it is absent, the reference was added after D0 and the hit
   **counts**.

Dates are committer dates in UTC, matching the window boundaries fixed in *The clock*.

**When a hit cannot be dated.** If either call fails to resolve — the repository has since gone
private or was deleted, the path was renamed so its history does not reach back past D0, or the
API returns an error — the hit is recorded as **undatable** and **does not satisfy this branch on
its own**. An undatable S2 hit counts only if corroborated by a qualifying S1 signal from the same
author inside the window, which is dated by construction. There is no third option and no
tie-break by inspection: an undatable hit with no S1 corroboration is written down as
examined-and-excluded, with "undatable" as the recorded reason. Narrowing the criterion is the
correct trade here — a branch that silently admits pre-intervention evidence is worse than one
that turns away a real signal it cannot date, because only the first kind of error can manufacture
a false GREEN.

**(2) Not the owner, not a bot.** Author login ≠ `Zandereins`, and `gh api users/<login> --jq
.type` returns `User` (not `Bot`, and not an `app/` login).

**(3) Unsolicited — the condition that does the real work.** The signal does not count if the
author is anyone the owner contacted, asked, told, or is otherwise connected to. Checkable filters,
all of which must hold:

- `gh api users/Zandereins/following --paginate --jq '.[].login'` does not contain the author, and
  `gh api users/<login>/following --paginate --jq '.[].login'` does not contain `Zandereins`.
- The author has no interaction with any repository under `Zandereins` dated **before D0** — no
  issue, PR, comment, star, or fork. Checked with
  `gh api -X GET search/issues -f q='involves:<login> user:Zandereins'` and
  `gh api repos/Zandereins/schliff/stargazers -H "Accept: application/vnd.github.star+json"
  --paginate`.
- **Pre-registered commitment, binding from today:** the owner will not solicit this signal —
  will not ask, DM, prompt, or hint to any person that they open an issue, file a PR, or mention
  schliff, for the duration of the Gate 2 window. If any signal that would otherwise qualify came
  from a person the owner had contact with about schliff during the window, it is disclosed in
  the verdict and **excluded**, even if the automated filters above would have passed it. This
  last part is owner-attested and cannot be verified from outside; it is written down in advance
  precisely because that is the only thing that gives an attestation any force.

**(4) Attributable to the plugin channel.** The signal must carry evidence that the person
arrived through the intervention this experiment shipped, not through some unrelated path. At
least one of:

- Its text references the plugin install path — `/plugin marketplace add`, `/plugin install`,
  `schliff@schliff`, `marketplace.json`, or the marketplace repo by name.
- It originates on a marketplace surface (S3), which is the plugin channel by construction.
- For S2, the committed file is a Claude Code plugin/marketplace configuration rather than a
  `pip`/`uvx` dependency pin — a `requirements.txt` mentioning schliff is a packaging signal, not
  a plugin-channel signal, and does not count.

A signal that is unattributable — a bare "nice project" issue with nothing tying it to the plugin
path — does **not** satisfy this branch. That is deliberate: the hypothesis is specifically that
*plugin-channel visibility* produces demand, and a signal that could equally have come from PyPI
or a search engine cannot test it.

The 30 days and the 14 days measure different things and are not interchangeable: 30 days is
the period Gate 2 has to resolve in; 14 days is the width of the window GitHub's API reports on
any single call. The quantitative branch resolves against **one fixed snapshot**: the last
`traffic.jsonl` line whose `collected_at` falls at or before 23:59 UTC on A0+30. That
line's own `views.uniques` field — itself already a trailing-14-day count as of that
`collected_at` — is compared against 96. No other line in the file counts, even if an
intermediate snapshot happened to clear 96 and a later one did not: picking whichever of several
overlapping 14-day readings clears the bar is a multiple-comparisons problem, and fixing the
evaluation point to a single pre-specified snapshot is what keeps the threshold from being found
by search after the fact.

**Failure verdict:** `RED-DEMAND` — and that one is final, because it is measured. There is no
retry: if the channel opens (Gate 1 passes) and no signal follows within the window, the
conclusion is that visibility was not the constraint.

Gate 2 only runs if Gate 1 passes. If Gate 1 fails, the experiment stops at
`RED-DISTRIBUTION` and Gate 2 is never reached — see below for why that separation matters. That
is what makes the next section necessary.

## Observation R — the README-only arm

**Not a gate. A pre-registered observation with a fixed reading date, which runs regardless of
what Gate 1 does.**

Why it exists: the README change (commit `97beb01`, plugin install path moved to the top) is the
only intervention this branch actually delivers to the public today. Submission has not happened
and may not happen. But Gate 2 is conditional on Gate 1, so as the spec stood, a
`RED-DISTRIBUTION` verdict would end the experiment with the shipped intervention **never
measured** — the demand question unanswered for exactly the second time, in exactly the way this
document exists to prevent. A clean baseline exists (2026-08-11, 32 unique visitors) and the
intervention is already live against it; not reading the result would be a choice to discard
data already being generated.

**Window:** 2026-08-11 (baseline, `traffic.jsonl` line 1) through **23:59 UTC on 2026-09-10** —
30 days. It does not wait for D0, is not extended by a late submission, and is not cancelled by
`RED-DISTRIBUTION` or by `ABANDONED-UNSUBMITTED`.

**Reading date: 2026-09-10.** The measurement is the same fixed-snapshot rule Gate 2's
quantitative branch uses, so the two are directly comparable: the last `traffic.jsonl` line whose
`collected_at` is at or before 23:59 UTC on 2026-09-10, and that line's own `views.uniques`
field. One line, chosen by date, not the maximum over the window.

**Confound, stated up front:** if D0 falls before 2026-09-10, this window overlaps the Gate 1
period and a reading here cannot be attributed to the README alone. In that case the number is
still recorded, and recorded as **confounded**, with D0 named. It is a clean README-only reading
only when no submission PR was opened before the reading date.

**What gets written down on 2026-09-10**, in this file, regardless of outcome:

| Field | Value |
| --- | --- |
| Reading date | 2026-09-10 |
| Snapshot line `collected_at` | *to be recorded* |
| `views.uniques` at reading | *to be recorded* |
| Baseline `views.uniques` | 32 |
| Delta vs. baseline | *to be recorded* |
| Confounded by a submission before the reading date? | *to be recorded (yes + D0, or no)* |

**Interpretation, pre-registered so it is not chosen afterwards:**

- **≥ 96 uniques (3× baseline)** — the same threshold Gate 2 uses. A README change alone clearing
  it would be a genuinely surprising result and is recorded as such.
- **Between 33 and 95** — movement, but within the range a 14-day rolling counter drifts through
  on its own. Recorded as *not distinguishable from noise*, explicitly not as encouragement. The
  baseline itself is a single reading, so there is no variance estimate available to say more
  than that, and inventing one after the fact is the thing this document exists to prevent.
- **≤ 32** — the README intervention produced no traffic increase. Combined with a
  `RED-DISTRIBUTION` or `ABANDONED-UNSUBMITTED` verdict, this is the branch's most likely honest
  outcome and it is a real finding: the one change that shipped, changed nothing measurable.

This observation carries no GREEN/RED verdict on its own — a single traffic reading against a
single baseline reading cannot support one, and pretending otherwise would be the same
over-claiming the gates above are built to avoid. What it guarantees is that the intervention
this branch shipped produces a written-down number either way, instead of nothing.

## Why the two verdicts are separated

The 2026-08-04 bet died at the gatekeeper and never reached the demand question, which is what
made its verdict unusable: a RED result that could mean either "nobody wants this" or "nobody
could find this" is not a result. Splitting `RED-DISTRIBUTION` from `RED-DEMAND` means a failure
at Gate 1 is reported as a channel finding — the two currently-reachable marketplaces didn't
merge it — and is never conflated with a statement about whether anyone wants schliff. Only a
Gate 2 failure, reached after distribution actually happened, is allowed to say anything about
demand.

## What is deliberately not done

No announcement round. No second Show HN. The 2026-07-13 finding stands, as recorded in the
parent plan (`docs/superpowers/plans/2026-08-11-plugin-channel-experiment.md`): a post from a
cold account has no reach, and content was never the problem. This experiment tests whether an existing, already-installable path becomes visible in places a
prospective user already looks — the README and marketplace listings — not whether a fresh
promotional push generates traffic. Adding an announcement round would reintroduce the
confound the 2026-08-04 bet already failed on: a positive result could then be attributed to the
announcement rather than to distribution visibility, and a negative result could be blamed on
weak promotion rather than measured as a channel or demand finding.

## How it will be judged, and by whom

The repository owner judges both gates by running the same commands anyone else could run
against the same artifacts, on the stated dates:

- Gate 1: `gh pr view <submission-PR-URL> --json createdAt,mergedAt,state` against each of the two
  qualified repos, checking `mergedAt` against 23:59 UTC on D0+21 as fixed in *The clock* above.
  No other repo counts toward N, regardless of how promising it looks once visited — the qualified
  list is fixed by `distributors.md` and is not expanded after Gate 1 opens. The verdict names the
  per-repo outcome and the in-scope/out-of-scope split, never a bare fraction of 2.
- Gate 2, quantitative branch: from `traffic.jsonl`, the last line with `collected_at` at or
  before 23:59 UTC on A0+30; its `views.uniques` field compared against 96 (3× the
  32-unique baseline recorded above). `scripts/collect-traffic.sh` must have been run at least
  once at or near that boundary for the line to exist — see *Operating the collector* below, so a
  missing snapshot at day 30 is an operational failure to fix, not a reason to substitute a
  different line.
- Gate 2, qualitative branch: the S1/S2/S3 commands listed in the Gate 2 section, run over the
  window; every hit is first **dated** per condition (1b) — S1/S3 on `createdAt`, S2 against the
  pre-D0 baseline and then the commit-history procedure — and every survivor is then checked
  against conditions (2), (3), and (4): not a bot, unsolicited, attributable to the plugin
  channel. A candidate that fails any one of the four is recorded as examined-and-excluded, with
  the failing condition named (including "undatable" where that is the reason), so the verdict
  shows what was looked at and not only what passed.
- Observation R: as specified in its own section — read 2026-09-10, recorded whatever it says.

Both thresholds are numbers fixed in this document before either measurement is taken. There is
no discretionary judgment call available at verdict time beyond the two already made and
disclosed above — the strength caveat on Gate 1 given an effective N of 1, and the owner-attested
no-solicitation commitment in Gate 2's condition (3). Nothing about the passing or failing values
can be adjusted after the traffic or PR data comes in.

## Operating the collector

Every quantitative reading in this document — Gate 2's branch and Observation R — is taken from a
line in `docs/experiments/plugin-channel/traffic.jsonl`. That file only has lines in it because
the collector ran.

**The command, by hand:**

```bash
make collect-traffic     # or: bash scripts/collect-traffic.sh
```

**Or on a schedule, in CI.** `.github/workflows/collect-traffic.yml` runs it weekly (Mondays
06:17 UTC) so the record does not depend on anyone remembering. Nothing is installed on any
machine — no cron job, no LaunchAgent.

That workflow needs one secret, and it cannot use the default workflow token. Measured on
2026-08-11 in run `31514201151`: `gh api repos/OWNER/REPO/traffic/views` with `GITHUB_TOKEN` and
`contents: write` returns **HTTP 403, "Resource not accessible by integration"**. The traffic
endpoints sit behind repository *Administration* permissions, which a workflow token cannot be
granted through the `permissions:` block at all.

So the workflow reads a `TRAFFIC_TOKEN` repository secret — a fine-grained personal access token
scoped to this repository with **Administration: Read** (and Contents: Read and write, so it can
commit the observation). Until that secret exists the job exits green with a notice and collects
nothing: a scheduled job that fails every week teaches its owner to ignore it, which is a worse
failure than a missing measurement. **A green run is therefore not evidence that an observation
was taken** — check that `traffic.jsonl` grew.

It needs an authenticated `gh` and nothing else, is idempotent per UTC day (a second run the same
day overwrites that day's line rather than appending a duplicate), and never touches the seeded
`"note":"baseline"` line.

**The required cadence: at least once every 14 days, and on each reading date.** The weekly
workflow satisfies this with a full missed run of slack — but only once `TRAFFIC_TOKEN` is set.
Until then the manual command is the only thing producing lines. GitHub's traffic
API returns a rolling 14-day window and serves nothing older. That is a hard property of the API,
not a default that can be raised.

**What happens if it is not run — the failure is silent and permanent.** Go 15 days without a
run and the days that fell out of the window are gone; there is no backfill, no export, and no
support request that recovers them. A gap does not produce an error, a warning, or a missing
file — `traffic.jsonl` simply has no line covering that stretch, and the absence is only
noticeable later, when a reading date arrives and the nearest qualifying snapshot is weeks stale
or does not exist. Concretely: if no snapshot exists at or before a reading boundary, that
reading cannot be taken at all. Per the rule above, a different line may **not** be substituted —
so the outcome is not a wrong number but no number, and the branch that depended on it is
recorded as `UNMEASURED-COLLECTOR-GAP` with the gap's dates. That is a worse outcome than any
RED, because a RED is a finding and a gap is only a mistake.

**The dates that must be covered**, given the windows fixed above: 2026-09-10 (Observation R),
and A0+30 whenever Gate 1 passes. Running it on those two dates is not sufficient on its own —
the 14-day rule still applies throughout, or the snapshot taken on the reading date will be
correct but the record around it will have holes.
