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

**Precondition on opening it at all** *(amended 2026-08-20 — see [Amendments](#amendments))*: no
submission PR is opened at either marketplace until
`docs/experiments/plugin-channel/s2-baseline.md` is on `main`. The S2 void rule below is
conditional on D0, which means the loss it describes is triggered by an action the owner takes,
not by a date that shows up in a calendar — so the block belongs on the action. Captured
2026-08-20. Whether the precondition holds is not asserted here, it is checked against the
remote rather than a local ref, which is only as fresh as the last fetch:

```bash
gh api -X GET repos/Zandereins/schliff/contents/docs/experiments/plugin-channel/s2-baseline.md \
  -f ref=main --jq .path
```

`-X GET` is not optional: `gh` switches to POST as soon as any `-f` field is present, the
contents route has no POST handler, and the resulting 404 is indistinguishable from the file
being absent — a permanently red gate that reads as "the baseline was never committed".

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
.type` returns `User` (not `Bot`, and not an `app/` login). *(amended 2026-08-20 — a
mass-automation account can pass this check as written; if one is admitted it must be named in
the verdict with the reason it was or was not counted. See [Amendments](#amendments).)*

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
no discretionary judgment call available at verdict time beyond the three already made and
disclosed — the strength caveat on Gate 1 given an effective N of 1, the owner-attested
no-solicitation commitment in Gate 2's condition (3), and the mass-automation disclosure duty
added to condition (2) on 2026-08-20 (see [Amendments](#amendments)). Nothing about the passing or failing values
can be adjusted after the traffic or PR data comes in.

## Operating the collector

Every quantitative reading in this document — Gate 2's branch and Observation R — is taken from a
line in `docs/experiments/plugin-channel/traffic.jsonl`. That file only has lines in it because
the collector ran.

**The command, by hand:**

```bash
make collect-traffic     # or: bash scripts/collect-traffic.sh
```

**Or on a schedule, in CI.** `.github/workflows/collect-traffic.yml` runs it **daily at 20:17
UTC** *(amended 2026-08-20 — was weekly, Mondays 06:17 UTC; see [Amendments](#amendments))* so
the record does not depend on anyone remembering. Nothing is installed on any machine — no cron
job, no LaunchAgent.

**Where the scheduled observations land: the `experiment/traffic-data` branch, not `main`.**
`main` is protected with `enforce_admins: true` and six required status checks, so a workflow
push to it is rejected outright — measured on 2026-08-11 in run `31519738229`, where collection
succeeded and only the push failed with `GH006: Protected branch update failed`. Opening a pull
request for each daily line would trade that for a merge queue nobody asked for. The scheduled
job therefore appends to `docs/experiments/plugin-channel/traffic.jsonl` **on that branch**, and
`main` keeps only the seeded baseline until a reading is taken.

**Consequence for every reading in this document:** read the file from the data branch, not from
a working copy of `main`:

```bash
git fetch origin experiment/traffic-data
git show origin/experiment/traffic-data:docs/experiments/plugin-channel/traffic.jsonl
```

At each reading date the branch's state is merged into `main` in one pull request, so the record
ends up where this document says it is. A reading taken from `main` before that merge sees only
the baseline and would be wrong — that is the one operational mistake this arrangement makes
possible, and it is named here so it is not made.

That workflow needs one secret, and it cannot use the default workflow token. Measured on
2026-08-11 in run `31514201151`: `gh api repos/OWNER/REPO/traffic/views` with `GITHUB_TOKEN` and
`contents: write` returns **HTTP 403, "Resource not accessible by integration"**. The traffic
endpoints sit behind repository *Administration* permissions, which a workflow token cannot be
granted through the `permissions:` block at all.

So the workflow reads a `TRAFFIC_TOKEN` repository secret — a fine-grained personal access token
scoped to this repository with **Administration: Read** (and Contents: Read and write, so it can
commit the observation). Until that secret exists the job exits green with a notice and collects
nothing: a scheduled job that fails every day teaches its owner to ignore it, which is a worse
failure than a missing measurement. **A green run is therefore not evidence that an observation
was taken** — check that `traffic.jsonl` grew.

It needs an authenticated `gh` and nothing else, is idempotent per UTC day (a second run the same
day overwrites that day's line rather than appending a duplicate), and never touches the seeded
`"note":"baseline"` line.

<a id="the-cadence-rule"></a>

**THE CADENCE RULE — stated once, referenced everywhere else.** *(amended 2026-08-21 — the
previous figure and the reason it moved are in [Amendments](#amendments))*

> **Run the collector at least once every 12 days, and on each reading date.**

Twelve, and the two steps are separate. **The arithmetic gives thirteen:** the window's far end
drifts by a day depending on when in the UTC day the call lands, measured — a run answered at
T-1 covers `[N-14, N-1]`, one answered at T-2 covers `[N-15, N-2]`. If the run before a gap lands
at T-2 and the one after it at T-1, a spacing of 14 leaves day `N-1` in no snapshot at all, while
13 still closes flush. **Twelve is thirteen minus one day of reserve**, held back because the
T-1/T-2 drift rests on a handful of observations and a slower answer than any yet seen would
break a bound set exactly at the arithmetic. The reserve is a deliberate margin, not a
derivation.

Do not restate this number elsewhere. It appeared in eleven places before 2026-08-21, and each
correction had to land in all eleven or contradict itself somewhere; `test_cadence_rule_stated_once.py`
now fails if a second site quotes it.

The daily workflow satisfies this comfortably, and `TRAFFIC_TOKEN` is configured — the
2026-08-17T06:28 `schedule` run succeeded and produced commit `ca60a89` on
`experiment/traffic-data`. Were the secret ever removed, the manual command would again be the
only thing producing lines.

GitHub's traffic API returns a rolling 14-day window and serves nothing older. That is a hard
property of the API — the input to the rule above, not the rule itself.

**What happens if it is not run — the failure is silent and permanent.** Exceed
[the cadence rule](#the-cadence-rule) and the days that fell out of the window are gone; there is no backfill, no export, and no
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
[the cadence rule](#the-cadence-rule) still applies throughout, or the snapshot taken on the
reading date will be correct but the record around it will have holes.

## Amendments

Changes made to this document **after** it was pre-registered on 2026-08-11. Listed so a reader
can separate what was fixed in advance from what was added later. `distributors.md` sets the
precedent: showing the correction is the point, silently editing it would be worse than the
original error.

**No fixed date and no measurement window has been changed by any amendment below.** Gate 1 is
still "≥1 of N merges within D0+21", Gate 2's threshold is still ≥96 uniques, Observation R still
reads 2026-09-10 against baseline 32, and the abandonment deadline is still 2026-09-30.

**One gate criterion HAS been narrowed, on 2026-08-25, and this line exists so that no reader has
to find it buried:** Gate 2's quantitative branch (`uniques ≥ 96`) is **void** for a window in
which a submission or listing outside the plugin channel lands, leaving Gate 2 to be decided on
its qualitative branch alone. It was written before any such submission existed and before any
Gate 2 data existed, and it removes a route to GREEN rather than adding one — it makes the gate
**harder** to pass. The earlier wording of this paragraph ("no GATE criterion … has been
changed") was accurate when written and is corrected here rather than quietly deleted, per the
`distributors.md` precedent stated above. See
[the 2026-08-25 amendment](#2026-08-25--four-measurement-defects-named-dates-after-2026-09-30-fixed-and-one-gate-narrowed).

One *operating* threshold did change, and saying "no threshold changed" would have hidden it:
the collector's cadence floor went from 14 days to 12 on 2026-08-21. It governs how the
instrument is run, not what the instrument decides, and the correction makes it stricter — see
[the cadence rule](#the-cadence-rule).

### 2026-08-20 — collector moved from weekly to daily

*What changed:* `.github/workflows/collect-traffic.yml` ran `cron: '17 6 * * 1'` (Mondays). It now
runs `cron: '17 20 * * *'` — daily. Every prose description of **the workflow's own schedule** was
corrected to match: in this file, in the workflow header, and in `scripts/collect-traffic.sh`,
whose header still claimed nothing scheduled the collector at all. The separate floor on how
long data survives was untouched by THAT change and corrected the next day — see
[the cadence rule](#the-cadence-rule) for the number and the amendment below for why.

*Why:* 2026-09-10 — Observation R's reading date, fixed on 2026-08-11 — is a **Thursday**. The
Mondays available before it were 08-24, 08-31 and **09-07**. Under the reading rule, the
qualifying snapshot would have been the one from 09-07 — a 30-day observation read from a
counter whose window ends around 09-05, leaving its last five days outside the number that
decides it. *The dates that must be covered* already required 2026-09-10; the schedule could not
deliver it. This is not `UNMEASURED-COLLECTOR-GAP` — a line would have existed and the 14-day
chain was never broken. It is a snapshot on the wrong date, which the reading rule forbids
substituting away.

*Why daily rather than a dated one-off:* the same requirement names a second date, A0+30, which
cannot be wired in advance because A0 is the merge date of a submission not yet opened. A dated
cron would have fixed one instance of the defect and left the other.

*What the 20:17 UTC hour does and does not buy.* It does **not** put the reading date into the
counter: the traffic API never reports the day the call is made. Measured 2026-08-20, a call at
10:12 UTC returned a window ending 2026-08-19, and all three committed snapshots agree
(08-11T12:52 → ends 08-10; 08-17T06:28 → ends 08-15). What the hour buys is whether the window
ends at T-1 or T-2: the 06:28 run came back at T-2, while calls at 10:12, 12:52 and 17:57 all
came back at T-1. A late run therefore costs one day of lag instead of two — and **one day is the
floor this API allows, not zero.**

*Deferred here, corrected separately:* the cadence floor. See the 2026-08-21 entry below.

*Cost:* ~30 observations per month on `experiment/traffic-data` instead of ~4. That branch holds
data only.

### 2026-08-21 — cadence floor 14 → 12 days, and stated in one place

*What changed:* the floor moved from 14 days to 12, and every other site now links to
[the cadence rule](#the-cadence-rule) instead of restating it.

*Why the number:* the window's far end drifts by a day depending on when in the UTC day the call
lands — a run answered at T-1 covers `[N-14, N-1]`, one answered at T-2 covers `[N-15, N-2]`. If
the run before a gap lands at T-2 and the one after it at T-1, a spacing of 14 leaves day `N-1`
in no snapshot at all, while 13 closes flush. Twelve is thirteen minus a day of reserve, because
the drift rests on a handful of observations. A margin, named as one.

*Why one place is the actual fix:* the number was stated in eleven sites across three files, so
every correction had to land eleven times. Three consecutive review rounds each found a site that
had been missed — including one where the prose claimed the sweep was complete while two sites
still disagreed. `test_cadence_rule_stated_once.py` now fails when a second statement appears,
and its first version could itself be defeated by rewording, which is why it matches any stated
duration rather than a list of phrasings.

*Scope:* this is an operating threshold, not a gate. With the daily collector it bites only if
the workflow is disabled or `TRAFFIC_TOKEN` is unset.

### 2026-08-20 — S2 baseline captured, and made a precondition of D0

*What changed:* `docs/experiments/plugin-channel/s2-baseline.md` was created (48 repository/path
pairs, 22 repositories; the `schliff@schliff` query returned 0). A precondition was added to *The
clock*: no submission PR is opened until that file is on `main`.

*Why:* the file the spec required had never been written. The void rule is conditional on D0, so
nothing was lost yet — but the trigger is an action the owner controls rather than a date, which
is precisely why it stayed invisible for nine days. Binding it to the action removes the
dependency on anyone remembering. No criterion moved: the S2 branch, its dating procedure and its
conditions are unchanged.

### 2026-08-20 — Gate 2 condition (2): disclosure duty for mass-automation accounts

*What changed:* nothing in the condition. This amendment adds a **disclosure duty**, not a
threshold.

*Why:* condition (2) qualifies an author by `gh api users/<login> --jq .type` returning `User`.
Measured 2026-08-20, the account `webbrain-one` — which forked this repository and opened PR #188
— returns `type=User` and `is_bot=false` while holding 20,816 public repositories on an account
created 2026-06-21. It passes condition (2) as written. In this instance condition (3) excludes it
anyway, because its interaction with this repository pre-dates D0, so no live gate is affected.

*The duty:* if a signal is admitted whose author's public profile indicates mass automation, the
account is **named in the verdict, with the profile facts that prompted the note — and it still
counts.** This adds disclosure only. It grants no discretion to exclude such an author: condition
(2) as pre-registered decides that, and inventing an exclusion now, with `webbrain-one` already in
view, is exactly what pre-registration forbids. A reader must be able to see which signals came
from such accounts and judge the verdict themselves; that is the whole of the duty. No number
is invented after the fact — inventing a repository-count threshold now, with the case already in
view, is the exact pattern pre-registration exists to prevent. This mirrors the owner-attested
mechanism already carried by condition (3): the check that cannot be fully mechanised is written
down in advance and disclosed when used.

### 2026-08-20 — release timing recorded as an operational constraint

*What changed:* nothing in any gate. Recorded here because it was previously an undocumented
verbal constraint, which a reader had no way to check.

*The constraint:* version 8.12.0 is not released while a measurement window is open. Its
`[Unreleased]` block has been ready since 2026-08-14 and is deliberately held.

*Honest about the evidence:* the confound is **not demonstrated** on the metric that matters.
Release day 2026-08-10 carries the highest single-day `count` in the baseline window
(2026-07-28 … 2026-08-10) at 26, but only 6 `uniques` — while that window's `uniques` peak, 7 on
2026-07-29, has no release near it. The highest `uniques` day recorded anywhere so far, 8 on
2026-08-13, sits in the 08-17 snapshot's window and likewise has no release near it. A
release plausibly moves views; on uniques it is unproven. The constraint is kept on asymmetry
rather than evidence: a wrongly confounded reading cannot be recovered, a delayed release can.

*The scheduled placement*, given that Gate 2's window opens at A0 and the median open→merged
latency for external PRs at `jeremylongshore/claude-code-plugins-plus-skills` was measured at
**1.17 days** (61 external merges, full result set: 876 returned against a limit of 3000): the
release goes out after Observation R's snapshot and a full week before the submission PR. Note
what does and does not follow: with release 09-11, D0 09-18 and A0 ≈ 09-19, the 14-day counter at
A0 still contains release day, so the week of separation does **not** clear the tail out of the
window. What protects the gate is that the quantitative branch reads a single snapshot at A0+30,
by which point release day has long fallen out of a 14-day window entirely. The separation buys
margin on the qualitative branch and on any reading taken earlier, not on the arithmetic.

### 2026-08-25 — four measurement defects named, dates after 2026-09-30 fixed, and one gate narrowed

*Deadline this was written against:* the last snapshot on `experiment/traffic-data` at the time
of this commit is `collected_at: 2026-08-24T20:28:05Z`, and its daily array ends **2026-08-23** —
so no snapshot in hand contains a single day of Observation R's window. The next run to carry one
lands 2026-08-28. **Everything from 2026-08-25 onward is blind at the time of writing**, which is
the property that makes the entries below pre-registration rather than post-hoc commentary. The
chain in hand is gapless — `2026-07-28 .. 2026-08-23`, `missing: []` — verifiable with the
coverage check in [Operating the collector](#operating-the-collector).

**E-1 — Observation R cannot see the intervention's onset.** R reads the snapshot at 2026-09-10,
whose 14-day T-1 window is **2026-08-27 … 2026-09-09**. The intervention (README change
`97beb01`) shipped 2026-08-11, sixteen days before that window opens. Whatever the README did in
its first two weeks — including the highest `uniques` day recorded anywhere so far, 8 on
2026-08-13 — is arithmetically outside the number that gets written down. R measures a *tail*,
not an onset. This is a limit on what R can conclude, and it is recorded rather than fixed:
moving the reading date would be changing a pre-registered date after watching data accumulate,
which is precisely what this document forbids. **The reading date stays 2026-09-10.**

*Explicitly NOT a defect, so that nobody "fixes" it later:* the window-type incompatibility
first suspected here is **refuted**. The baseline line (`collected_at 2026-08-11T12:52:19Z`)
carries a 14-day array ending 2026-08-10 — a T-1 window — and R's reading rule produces the same
14-day T-1 shape. Baseline and R are the same estimator on the same instrument. They are
comparable; only the *placement* of R's window is the problem.

**E-2 — the baseline window was noisy in a way the R window is not, and the direction is not
assumed.** The baseline window (2026-07-28 … 2026-08-10) contained **8 releases** — `v8.8.0`,
`v8.8.1`, `v8.8.2`, `v8.9.0`, `v8.10.0`, `v8.10.1`, `v8.11.0`, `v8.11.1` — and 40 commits on
`main`. Observation R's window falls inside the visible-surface freeze, so it will contain zero
releases. The two windows therefore differ in repository activity, not only in the intervention.

*Stated in both directions, because only one direction is convenient and that is the reason to
write both down:*

- **Baseline inflated** → the comparison flatters the README, and a delta at R is partly the
  absence of release noise being read as intervention effect. Convenient direction.
- **Baseline is the honest reference** → this repository's normal state includes shipping, the
  freeze makes the R window *abnormally quiet*, and R therefore **understates** what the README
  does under ordinary operation. Inconvenient direction.

Which one holds is not decidable from the data available, and this document does not pick. What
it forbids is picking on 2026-09-10, once the number is known. Note also that the 2026-08-20
amendment already records the honest state of the evidence: on `uniques` — the metric R actually
reads — a release effect is **unproven**, and both recorded `uniques` peaks sit away from any
release. E-2 is a named uncertainty, not a demonstrated bias.

**E-3 — `fpaul.dev` is a self-created referrer, and R has no channel attribution.** From the
2026-08-21 snapshot onward, `fpaul.dev` appears in `referrers` (1–2 uniques; 2 as of the
2026-08-24 snapshot). R reads `views.uniques` for the repository page as a single scalar: it
cannot separate a visitor who arrived because the README changed from one the owner's own site
sent. Any R reading above baseline is therefore **partly self-supplied, by an amount R cannot
report**. Recorded, not corrected — subtracting a referrer count from a de-duplicated `uniques`
field is not arithmetically valid (a visitor can appear in both), and inventing a correction
after the fact is worse than naming the limit. When R is written down on 2026-09-10, the
`referrers` array of the same snapshot line is recorded beside it, so a reader can see the size
of this term instead of being told it is small.

**E-4 — Gate 1's base rate is 35 %, and the 1.17-day median is the wrong statistic.** The
2026-08-20 amendment cites a median open→merged latency of **1.17 days** at
`jeremylongshore/claude-code-plugins-plus-skills`. That figure is computed over *merged PRs only*
and is therefore survivorship-biased: it answers "given a merge, how fast", not "given a
submission, how likely". Measured 2026-08-25 over the complete result set (1137 PRs returned
against a limit of 3000, so not truncated), counting external non-owner non-bot PRs whose full
21-day window has already elapsed:

| Cohort (external PRs opened in…) | Merged within 21 days |
| --- | --- |
| the last 90 days | **14/40 = 35.0 %** |
| the last 180 days | 43/87 = 49.4 % |
| the last 365 days | 59/107 = 55.1 % |

**The base rate is strongly window-sensitive, and that is disclosed rather than resolved.** The
90-day figure is the reference because 90 days is the window `distributors.md` already qualifies
channels on — not because it is the most favourable; it is in fact the least favourable of the
three. What all three say jointly: **Gate 1 failing is a common outcome at a healthy channel**,
not evidence of rejection. A `RED-DISTRIBUTION` verdict must be read against this number, and
this table is what it is read against.

*Censoring, pre-registered:* an external PR still open when its 21 days elapse is a **censored
observation** — 16 external PRs at that repository are open right now, several older than 21
days. Applied to Gate 1: if schliff's submission PR is still open at 23:59 UTC on D0+21, Gate 1
resolves `RED-DISTRIBUTION` as pre-registered — **the criterion does not change** — but the
verdict records it as **censored (open, not rejected)** in the same sentence, because "not merged
within 21 days" and "declined" are different findings, and the base rate above shows the first is
the ordinary case.

**Dates after 2026-09-30, which existed nowhere until this commit.** These are derived from rules
already in this document; nothing is chosen freshly here:

| Event | Date | Derived from |
| --- | --- | --- |
| D0 (planned) | 2026-09-18 | operational plan; still the event that fixes the clock |
| Gate 1 resolves | **23:59 UTC 2026-10-09** | D0+21, per *The clock* |
| Gate 2 opens | A0, 00:00 UTC | A0 = `mergedAt` of the first merged submission PR |
| Gate 2 resolves | 23:59 UTC on A0+30 | single snapshot, per Gate 2's quantitative branch |

**The outcome with no A0 is named here, in advance:** if Gate 1 resolves without a merge, A0
never exists, Gate 2 is **never opened and never read**, and the demand question stays untested by
this branch. That is reported as `RED-DISTRIBUTION` with Gate 2 recorded as `NOT-REACHED` — not as
`RED-DEMAND`, and not as a pending item that quietly stays open forever. If D0 itself never
happens by 23:59 UTC 2026-09-30, `ABANDONED-UNSUBMITTED` governs and every date in the table
above is void.

**Collector operating commitment.** `.github/workflows/collect-traffic.yml` runs daily until at
least **A0+31**, or — if Gate 1 resolves without a merge — until Gate 1's resolution date. Issue
#198 stays open until then and is the place where a collector outage is recorded. The instrument
is not switched off at the first verdict, because Gate 2 reads a snapshot 30 days after a merge
that may not yet have happened when Gate 1 resolves.

**Secondary quantity, pre-registered as NON-CONFIRMATORY.** Alongside R's scalar, this will be
computed on 2026-09-10: the per-day union of `views.views[]` across all snapshots, and from it
the mean `uniques`/day for **2026-07-28 … 2026-08-10** (pre) against **2026-08-11 … 2026-09-09**
(post). The pre value is already fixed and is stated now: 42 unique-days over 14 days =
**3.00/day**. The post value is deliberately **not** computed here.

*The estimator discrepancy is disclosed up front:* summing the daily array is **not** the same
statistic as the window field. On the baseline line the daily array sums to **42** while
`views.uniques` reports **32** — a visitor returning on several days is counted once by the
window field and once per day by the sum. The two measure different things; neither is wrong, and
the 10-visitor gap is the size of the effect.

**Hard limits on this quantity, so it cannot be used to rescue a result:** it may not move the
96-uniques threshold, may not overturn or soften a RED verdict, and may not be reported as the
headline. It exists because the daily array is finer-grained data the experiment already collects
and currently discards, and pre-registering it now is the only way it can ever be reported
without being a post-hoc fishing expedition.

**One gate criterion IS narrowed by this amendment — Gate 2's quantitative branch can be
voided.** This is the first amendment to touch a gate:

> If a submission or listing **outside the plugin channel** (for example the pending
> `awesome-claude-code` #1620, or a `travisvn` directory submission) lands or is merged during
> Gate 2's window, the quantitative branch (`uniques ≥ 96`) is **void** for that window, and
> Gate 2 is decided **on its qualitative branch alone**.

*Why, and why now:* Gate 2's branches are an OR, so the weaker branch decides the gate. A listing
in a 38.9k-star or 14.8k-star index could push `uniques` past 96 through a channel that is not
the one under test, and Gate 2 would read GREEN for the wrong reason. The qualitative branch
already requires attribution to the plugin path, so it is immune to this by construction.

*The direction of the change is the point:* this makes Gate 2 **harder** to pass, never easier —
it removes a route to GREEN and keeps only the branch carrying the attribution duty. It is
written now, **before any such submission exists and before any Gate 2 data exists**, by someone
who wants those listings to happen. That is the disclosure: this amendment runs against the
author's own interest in the outcome, which is what makes it admissible at all. An amendment
*adding* a route to GREEN, written at this point, would not be.

*Unchanged by all of the above:* D0 stays 2026-09-18. Gate 1 stays "≥1 of N merges within D0+21".
Gate 2's threshold stays 96 uniques and its qualitative branch is untouched. Observation R still
reads 2026-09-10 against baseline 32. The abandonment deadline stays 2026-09-30.
