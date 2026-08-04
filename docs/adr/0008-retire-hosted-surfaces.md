# ADR 0008: Retire the hosted playground, leaderboard and badge endpoint

- Status: accepted
- Date: 2026-08-04

## Context

schliff shipped three publicly reachable surfaces alongside the CLI: a playground
(`POST /api/score`), a leaderboard (`POST /api/submit`, `GET /api/query`) and a badge
endpoint (`GET /api/badge?repo=`). All three ran as Vercel serverless functions in region
`iad1`, and the leaderboard's rate limiter stored visitor-IP-derived keys in an Upstash
Redis instance.

The trigger was an operator constraint: the maintainer is a private individual in Germany
and will not publish a home address, which the provider-identification duty for publicly
provided telemedia requires. But a council review found that framing was the weaker half
of the problem. The **data-protection information duty** does not attach to how an operator
presents themselves — it attaches to **processing**. Visitor IPs used as rate-limit keys
are processing, and no service address, no lawyer's opinion and no wording change removes
that duty. It is a permanent operating obligation for as long as the surfaces run.

Against that stood the measured value of the surfaces:

- **Web Analytics was never enabled** on either project (`404 Web Analytics not found`),
  so no usage data exists and none can be recovered retroactively.
- A GitHub code search for `schliff-playground.vercel.app` and
  `schliff-leaderboard.vercel.app` returned references in **three repositories, all owned
  by the maintainer** — zero third-party consumers. The search is not exhaustive, so the
  honest claim is *no demonstrable demand*, not *zero demand*.
- A pre-registered demand bet on badge adoption had a baseline of **0 badges in the wild**.

## Decision

Take all three surfaces offline. Both Vercel projects are **kept and emptied**, not
deleted: every function and environment variable is removed and each project serves a
static retirement notice. The playground additionally serves a static shields-endpoint
JSON at `/api/badge` reporting `retired` in grey, so any badge already embedded in a
README degrades to an honest label instead of a broken image.

The Upstash `rl:*` keys are deleted explicitly over the REST API and the result recorded
before the integration is removed, rather than trusting the integration teardown to erase
them.

The application code and its 95 tests stay in the repository. Exactly one file is removed:
`.github/workflows/playground-pin-drift.yml`, which asserted that the live deployed engine
matched the committed pin and would otherwise fail daily against a service that no longer
exists.

## Why

Retirement is the only option that discharges every obligation at once. A service address
(~10–20 €/month, the alternative four of six advisors reached for) would settle the
*disputed* provider-identification question and leave the *established* processing duty and
the third-country transfer untouched. Buying a permanent operating obligation for surfaces
with no demonstrable demand is the worse trade regardless of who is right about the
provider-identification threshold — which is why this decision does not depend on
resolving it.

**The projects are kept rather than deleted** because releasing a `*.vercel.app` subdomain
makes it re-registrable, and the playground URL was already written into third-party pull
requests by the action's comment footer. Emptying removes the processing just as
completely; deleting additionally hands a schliff-branded address to whoever claims it
next.

**The code is kept** because deleting it discharges no obligation that taking the surfaces
offline does not already discharge. It was the only irreversible step in the original plan
and the only one with no stated benefit, and it would have forced the deletion of four test
files carrying 95 collected tests. The drift risk it was meant to remove — stale entries in
the release checklist — costs one paragraph in `RELEASING.md`.

## Rejected

- **Publish a service address and keep operating.** Settles the disputed duty only. Leaves
  the processing duty and the `iad1` transfer, i.e. a permanent obligation, in exchange for
  surfaces with no measured users.
- **Rebuild the playground as a static client-side page (Pyodide/WASM).** Technically
  attractive — the scoring core is deterministic and dependency-free — but a static page is
  just as much a publicly provided telemedium, so it does not answer the address question.
  It was advanced and then withdrawn by its own proposer as "a data-protection improvement
  in provider-identification costume".
- **Gate the surfaces behind authentication.** Same practical effect as retirement for any
  outside user, while keeping the projects, the processing and the obligations alive.
- **Wait until the demand bet's 2026-09-29 deadline.** The bet's instrument was never
  instrumented — analytics did not exist — so waiting produces no new evidence. Enabling
  analytics now and waiting 30–60 days *would* produce some, and that option is recorded in
  the kill criteria below rather than pretended away.
- **Delete the Vercel projects.** See above: subdomain re-registration, no compensating
  benefit.

## What would reverse this

1. The Vercel usage dashboard shows more than roughly 200 requests per month to either
   project after retirement, with the maintainer's own checks subtracted. That would mean
   demand existed and was merely never measured; an EU region plus a published privacy
   notice would then beat retirement.
2. A third-party repository turns up embedding the badge. Code search is not exhaustive; a
   real consumer makes the static retirement JSON a duty rather than a courtesy and means
   the subdomains must be held indefinitely.

## Note on scope

This ADR records an engineering and operating decision and the reasoning behind it. It is
**not legal advice and not a legal assessment** — no lawyer was consulted, the
provider-identification threshold for a non-monetised open-source demo is genuinely
disputed, and the processing analysis above is a considered reading rather than a finding.
It is written down so the decision is not re-litigated from memory, not so it can be cited
as authority.

## Correction, 2026-08-04 (same day, after acceptance)

The Context section above states the trigger as "the maintainer … will not publish a home
address". **That was too broad and is corrected here rather than rewritten** — an accepted
ADR records what was decided and on what basis, including where the basis turned out to be
stated wrongly.

The accurate position: publishing provider-identification data was never the blocker it was
written up as, and the maintainer does publish it where it is owed. What a published address
cannot do is discharge the **data-protection information duty**, because that duty attaches
to processing rather than to how an operator presents themselves — which is exactly the
reasoning already given under *Why*, and which the retirement was actually built on.

**The decision is unchanged and the load-bearing argument is untouched.** The two reasons that
carry it — a permanent processing obligation, and no demonstrable demand for the surfaces
paying for it — were independent of the trigger from the start. Only the framing of the
trigger was wrong, and a public record that says something inaccurate about its own author is
worth correcting even when the outcome does not move.

See `docs/adr/0009-ai-act-assessment.md` for the regulatory assessment that was deliberately
left out of this ADR at the time.
